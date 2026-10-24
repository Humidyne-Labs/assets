#!/usr/bin/env python3
"""
science_mcp.py - Embedded Science, Symbolic Math, and Formal Verification MCP Server.
Provides SymPy fixed-point approximation, Z3 SMT constraint verification, and SciPy thermal fitting.
"""

import sys
import math
import json
from typing import Dict, List, Optional, Any
from mcp.server.fastmcp import FastMCP
import sympy as sp
import numpy as np
from scipy.optimize import curve_fit
import z3

mcp = FastMCP("science-math-prover")

@mcp.tool()
def derive_fixed_point_polynomial(
    formula: str,
    var: str = "T",
    min_val: float = -20.0,
    max_val: float = 80.0,
    degree: int = 3,
    q_format: int = 16,
    num_samples: int = 200
) -> str:
    """
    Fit a polynomial approximation to a mathematical expression over [min_val, max_val]
    and convert it to Q-format integer arithmetic for FPU-less ULP RISC-V or integer cores.
    
    Returns C code, integer coefficients, and maximum quantization error metrics.
    """
    sym = sp.Symbol(var)
    parsed_expr = sp.sympify(formula)
    f_lambdified = sp.lambdify(sym, parsed_expr, modules=["math", "numpy"])

    x_vals = np.linspace(min_val, max_val, num_samples)
    y_vals = np.array([float(f_lambdified(x)) for x in x_vals])

    # Fit polynomial of specified degree: P(x) = c0 + c1*x + c2*x^2 + ...
    poly_coeffs = np.polyfit(x_vals, y_vals, degree)
    # polyfit returns highest degree first: [c_deg, ..., c1, c0]
    coeffs_ascending = list(reversed(poly_coeffs))

    scale = 1 << q_format
    int_coeffs = [int(round(c * scale)) for c in coeffs_ascending]

    # Evaluate integer approximation vs true floating-point values
    approx_y = np.zeros_like(x_vals)
    for i, c_int in enumerate(int_coeffs):
        approx_y += (c_int * (x_vals ** i)) / scale

    errors = np.abs(y_vals - approx_y)
    max_abs_err = float(np.max(errors))
    rel_errors = np.where(np.abs(y_vals) > 1e-9, errors / np.abs(y_vals), 0.0)
    max_rel_err_pct = float(np.max(rel_errors)) * 100.0

    # Build C code snippet
    c_lines = [
        f"// Q{q_format}.{q_format} Polynomial Approximation for: {formula}",
        f"// Domain: [{min_val}, {max_val}], Max Abs Error: {max_abs_err:.6f}, Max Rel Error: {max_rel_err_pct:.3f}%",
        f"static inline int32_t approx_q{q_format}(int32_t {var}_fixed) {{",
        f"    // Input {var}_fixed in Q{q_format}.{q_format}",
    ]

    for i, c_int in enumerate(int_coeffs):
        c_lines.append(f"    const int32_t C{i} = {c_int}; // {coeffs_ascending[i]:.8f} * 2^{q_format}")

    # Horner's method for efficient integer evaluation
    c_lines.append("    // Horner evaluation:")
    horner_expr = f"C{len(int_coeffs)-1}"
    for i in range(len(int_coeffs) - 2, -1, -1):
        horner_expr = f"((({horner_expr} * {var}_fixed) >> {q_format}) + C{i})"
    c_lines.append(f"    return {horner_expr};")
    c_lines.append("}")

    result = {
        "formula": formula,
        "degree": degree,
        "q_format": f"Q{32 - q_format}.{q_format}",
        "float_coeffs_ascending": [float(c) for c in coeffs_ascending],
        "q_coeffs_int": int_coeffs,
        "max_absolute_error": max_abs_err,
        "max_relative_error_pct": max_rel_err_pct,
        "c_code": "\n".join(c_lines)
    }
    return json.dumps(result, indent=2)

@mcp.tool()
def solve_z3_assertions(assertions: List[str], declarations: Optional[Dict[str, str]] = None) -> str:
    """
    Solve formal boolean/integer constraints using the Z3 SMT Theorem Prover.
    Pass declarations like {"state": "Int", "rtc_wake": "Bool", "hold_pin": "Bool"}
    and assertions like ["Or(state == 0, state == 1)", "Implies(rtc_wake, state == 1)"].
    
    Returns SAT with satisfying assignment (e.g. counterexample) or UNSAT (proved invariant).
    """
    solver = z3.Solver()
    env: Dict[str, Any] = {}

    if declarations:
        for name, typ in declarations.items():
            if typ.lower() in ("bool", "boolean"):
                env[name] = z3.Bool(name)
            elif typ.lower() in ("int", "integer"):
                env[name] = z3.Int(name)
            elif typ.lower() in ("real", "float"):
                env[name] = z3.Real(name)
            elif typ.lower().startswith("bitvec") or typ.lower().startswith("bv"):
                bits = int("".join(filter(str.isdigit, typ)) or 32)
                env[name] = z3.BitVec(name, bits)

    # Expose common Z3 functions in eval environment
    env.update({
        "And": z3.And, "Or": z3.Or, "Not": z3.Not, "Implies": z3.Implies,
        "Xor": z3.Xor, "If": z3.If, "Distinct": z3.Distinct,
        "ULT": z3.ULT, "UGT": z3.UGT, "ULE": z3.ULE, "UGE": z3.UGE,
        "Extract": z3.Extract, "Concat": z3.Concat
    })

    for a_str in assertions:
        try:
            expr = eval(a_str, {"__builtins__": {}}, env)
            solver.add(expr)
        except Exception as e:
            return json.dumps({"status": "ERROR", "message": f"Failed to parse assertion '{a_str}': {e}"})

    check_res = solver.check()
    if check_res == z3.sat:
        model = solver.model()
        model_dict = {str(d): str(model[d]) for d in model.decls()}
        return json.dumps({"status": "SAT", "message": "Constraint set is satisfiable.", "model": model_dict}, indent=2)
    elif check_res == z3.unsat:
        return json.dumps({"status": "UNSAT", "message": "Constraint set is unsatisfiable (proved impossible / invariant holds)."}, indent=2)
    else:
        return json.dumps({"status": "UNKNOWN", "message": "Solver timed out or undetermined."})

@mcp.tool()
def fit_thermal_rc(time_points_sec: List[float], temp_points_c: List[float]) -> str:
    """
    Fit an empirical Newton cooling / thermal RC decay curve:
        T(t) = T_inf + (T_0 - T_inf) * exp(-t / tau)
    
    Returns initial temperature T_0, asymptotic ambient T_inf, and time constant tau (sec).
    """
    t_arr = np.array(time_points_sec, dtype=float)
    T_arr = np.array(temp_points_c, dtype=float)

    def model_func(t, T0, T_inf, tau):
        return T_inf + (T0 - T_inf) * np.exp(-t / np.maximum(tau, 1e-6))

    p0 = [T_arr[0], T_arr[-1], max(1.0, (t_arr[-1] - t_arr[0]) / 3.0)]
    try:
        popt, _ = curve_fit(model_func, t_arr, T_arr, p0=p0, maxfev=10000)
        T0_fit, T_inf_fit, tau_fit = popt

        # Evaluate R^2
        residuals = T_arr - model_func(t_arr, *popt)
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((T_arr - np.mean(T_arr))**2)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0

        return json.dumps({
            "status": "SUCCESS",
            "T_initial_degC": float(T0_fit),
            "T_ambient_inf_degC": float(T_inf_fit),
            "tau_time_constant_seconds": float(tau_fit),
            "r_squared": float(r_squared),
            "summary": f"Decay tau = {tau_fit:.2f}s | T0 = {T0_fit:.2f}C -> T_inf = {T_inf_fit:.2f}C (R2 = {r_squared:.4f})"
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "message": str(e)})

@mcp.tool()
def eval_symbolic_math(expression: str, substitutions: Optional[Dict[str, float]] = None) -> str:
    """
    Simplify, factor, expand, or numerically evaluate a symbolic math expression via SymPy.
    """
    try:
        expr = sp.sympify(expression)
        simplified = sp.simplify(expr)
        result = {
            "input": expression,
            "simplified": str(simplified),
            "latex": sp.latex(simplified)
        }
        if substitutions:
            subs_syms = {sp.Symbol(k): v for k, v in substitutions.items()}
            evaluated = simplified.subs(subs_syms).evalf()
            result["evaluated"] = float(evaluated) if evaluated.is_number else str(evaluated)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "message": str(e)})

if __name__ == "__main__":
    mcp.run()
