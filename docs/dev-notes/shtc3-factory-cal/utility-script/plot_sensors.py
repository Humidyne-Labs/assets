#!/usr/bin/env python3
import os
import sys
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def load_sensor_csv(filepath: str) -> pd.DataFrame:
    """Reads sensor CSV, corrects midnight rollover, and drops empty trailing columns."""
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.", file=sys.stderr)
        sys.exit(1)
        
    df = pd.read_csv(filepath, index_col=False)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    if 'Time' not in df.columns:
        print(f"Error: 'Time' column missing from {filepath}.", file=sys.stderr)
        sys.exit(1)
        
    raw_time = pd.to_datetime(df['Time'].astype(str).str.strip(), format='%H:%M:%S')
    
    # Increment day count on midnight rollover (23:59:59 -> 00:00:00)
    day_rollovers = (raw_time.diff().dt.total_seconds() < 0).cumsum()
    df['Time'] = raw_time + pd.to_timedelta(day_rollovers, unit='D')
    return df

def get_base_model(column_name: str) -> str:
    """Extracts sensor model name, stripping pandas duplicate counters like '.1'."""
    if '.' in column_name and column_name.rsplit('.', 1)[-1].isdigit():
        return column_name.rsplit('.', 1)[0]
    return column_name

def parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Unified Sensor Plotter with baseline comparison and sensor isolation.",
        add_help=False
    )
    parser.add_argument('--help', action='help', help="Show this help message and exit.")
    
    # Unit / File flags
    parser.add_argument('-c', '--celsius', nargs='?', const=True, default=None,
                        help="Plot in Celsius (°C). Optionally specify file: -c temp.csv")
    parser.add_argument('-h', '--humidity', nargs='?', const=True, default=None,
                        help="Plot in Humidity (%%). Optionally specify file: -h hum.csv")
    parser.add_argument('files', nargs='*', help="One or two CSV file paths.")
    
    # Sensor isolation & baseline switches
    parser.add_argument('-s', '--sensors', nargs='+', default=None,
                        help="Isolate specific sensor model(s) (e.g. -s SHTC3 SHT85).")
    parser.add_argument('-b', '--baseline', default=None,
                        help="Sensor model to use as reference standard (e.g. -b SHT85).")
    parser.add_argument('--diff', action='store_true',
                        help="Plot deviation / delta relative to baseline (Δ = Sensor - Baseline).")
    
    # Formatting
    parser.add_argument('--aggregate', action='store_true',
                        help="Plot model averages instead of all individual channels.")
    parser.add_argument('-o', '--output', default=None,
                        help="Save figure to file path instead of opening interactive GUI.")
    
    return parser.parse_args()

def resolve_tasks(args):
    tasks = []
    if isinstance(args.celsius, str):
        tasks.append((args.celsius, 'c'))
    if isinstance(args.humidity, str):
        tasks.append((args.humidity, 'h'))
        
    if args.files:
        if len(args.files) == 1:
            unit = 'h' if args.humidity is True else 'c'
            tasks.append((args.files[0], unit))
        elif len(args.files) >= 2:
            tasks.append((args.files[0], 'c'))
            tasks.append((args.files[1], 'h'))
            
    if not tasks:
        print("Usage error: Please provide at least one CSV file.", file=sys.stderr)
        sys.exit(1)
    return tasks

def main():
    args = parse_cli_args()
    tasks = resolve_tasks(args)
    
    meta_map = {
        'c': {'unit_label': 'Temperature (°C)', 'title': 'Temperature', 'symbol': '°C'},
        'h': {'unit_label': 'Relative Humidity (%)', 'title': 'Relative Humidity', 'symbol': '%'}
    }
    
    # Ensure baseline is included in plotted targets if filter is active
    target_sensors = set(args.sensors) if args.sensors else None
    if args.baseline and target_sensors:
        target_sensors.add(args.baseline)
        
    loaded_data = []
    all_models = set()
    
    for filepath, unit in tasks:
        df = load_sensor_csv(filepath)
        sensor_cols = [c for c in df.columns if c != 'Time']
        
        # Filter down to isolated sensors if -s or -b was supplied
        if target_sensors:
            filtered_cols = [c for c in sensor_cols if get_base_model(c) in target_sensors]
            if not filtered_cols:
                print(f"Warning: None of {target_sensors} found in {filepath}.", file=sys.stderr)
            df = df[['Time'] + filtered_cols]
            sensor_cols = filtered_cols
            
        for col in sensor_cols:
            all_models.add(get_base_model(col))
        loaded_data.append((df, unit, filepath))
        
    if not all_models:
        print("Error: No matching sensor data to plot.", file=sys.stderr)
        sys.exit(1)
        
    sorted_models = sorted(list(all_models))
    palette = [c for c in plt.cm.tab10.colors if c != (0, 0, 0)]
    color_map = {}
    c_idx = 0
    for m in sorted_models:
        if m == args.baseline:
            color_map[m] = 'black'
        else:
            color_map[m] = palette[c_idx % len(palette)]
            c_idx += 1
            
    num_tasks = len(tasks)
    show_diff = args.diff and (args.baseline is not None)
    
    # Allocate subplots (2 rows per file if delta/diff is requested)
    if show_diff:
        fig, axes = plt.subplots(num_tasks * 2, 1, figsize=(14, 4.5 * num_tasks * 2), sharex=True)
        if not isinstance(axes, np.ndarray):
            axes = np.array([axes])
        axes = axes.flatten()
    else:
        fig, axes = plt.subplots(num_tasks, 1, figsize=(14, 5 * num_tasks), sharex=True, squeeze=False)
        axes = axes.flatten()
        
    for i, (df, unit, filepath) in enumerate(loaded_data):
        meta = meta_map.get(unit, {'unit_label': f'Value ({unit})', 'title': 'Sensor Readings', 'symbol': unit})
        sensor_cols = [c for c in df.columns if c != 'Time']
        
        # Calculate baseline reference curve
        baseline_series = None
        if args.baseline:
            b_cols = [c for c in sensor_cols if get_base_model(c) == args.baseline]
            if b_cols:
                baseline_series = df[b_cols].mean(axis=1)
            else:
                print(f"Warning: Baseline '{args.baseline}' not in {filepath}.", file=sys.stderr)
                
        grouped = {}
        for col in sensor_cols:
            grouped.setdefault(get_base_model(col), []).append(col)
            
        ax_main = axes[i * 2] if show_diff else axes[i]
        ax_diff = axes[i * 2 + 1] if show_diff else None
        
        # 1. Plot Baseline first
        if args.baseline and args.baseline in grouped:
            cols = grouped[args.baseline]
            label = f"BASELINE: {args.baseline}" + (f" (mean of {len(cols)})" if len(cols) > 1 else "")
            ax_main.plot(df['Time'], baseline_series, label=label, color='black', lw=2.2, linestyle='--', zorder=5)
            
        # 2. Plot Target Sensors
        for model_name, cols in grouped.items():
            if model_name == args.baseline:
                continue
            color = color_map[model_name]
            
            if args.aggregate:
                mean_s = df[cols].mean(axis=1)
                label = f"{model_name}" + (f" (avg of {len(cols)})" if len(cols) > 1 else "")
                ax_main.plot(df['Time'], mean_s, label=label, color=color, lw=1.8)
                if ax_diff is not None and baseline_series is not None:
                    diff = mean_s - baseline_series
                    ax_diff.plot(df['Time'], diff, label=f"Δ {model_name} - {args.baseline}", color=color, lw=1.6)
            else:
                for j, col in enumerate(cols):
                    label = f"{model_name} #{j+1}" if len(cols) > 1 else model_name
                    ax_main.plot(df['Time'], df[col], label=label, color=color, alpha=0.7, lw=1.2)
                    if ax_diff is not None and baseline_series is not None:
                        diff = df[col] - baseline_series
                        ax_diff.plot(df['Time'], diff, label=f"Δ {label} - {args.baseline}", color=color, alpha=0.7, lw=1.2)
                        
        ax_main.set_title(f"{meta['title']} — {os.path.basename(filepath)}", fontsize=12, fontweight='bold')
        ax_main.set_ylabel(meta['unit_label'], fontsize=10)
        ax_main.grid(True, linestyle='--', alpha=0.5)
        ax_main.legend(loc='best', fontsize=8)
        
        if ax_diff is not None:
            ax_diff.axhline(0, color='black', linestyle=':', lw=1.5, alpha=0.8)
            ax_diff.set_title(f"Deviation from Baseline (Δ = Sensor - {args.baseline})", fontsize=11, fontweight='bold')
            ax_diff.set_ylabel(f"Difference ({meta['symbol']})", fontsize=10)
            ax_diff.grid(True, linestyle='--', alpha=0.5)
            ax_diff.legend(loc='best', fontsize=8)
            
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    axes[-1].set_xlabel('Time (HH:MM:SS)', fontsize=10)
    fig.autofmt_xdate(rotation=30)
    
    plt.tight_layout()
    if args.output:
        plt.savefig(args.output, bbox_inches='tight', dpi=150)
        print(f"Plot saved to: {args.output}")
    else:
        plt.show()

if __name__ == '__main__':
    main()