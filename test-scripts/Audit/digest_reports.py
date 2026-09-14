#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

def parse_trivy(file_path):
    findings = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            results = data.get("Results") or []
            for res in results:
                target = res.get("Target", "Unknown Target")
                vulns = res.get("Vulnerabilities") or []
                for v in vulns:
                    severity = str(v.get("Severity", "")).upper()
                    if severity in ["CRITICAL", "HIGH"]:
                        findings.append({
                            "tool": "Trivy",
                            "severity": severity,
                            "target": target,
                            "id": v.get("VulnerabilityID", "N/A"),
                            "package": v.get("PkgName", "Unknown"),
                            "installed": v.get("InstalledVersion", "Unknown"),
                            "fixed": v.get("FixedVersion", "N/A"),
                            "title": v.get("Title", "No description")
                        })
    except Exception as e:
        print(f"[!] Warning: Failed parsing Trivy report ({file_path.name}): {e}", file=sys.stderr)
    return findings

def parse_testssl(file_path):
    findings = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                data = data.get("scanResult", [])
            for item in data:
                if not isinstance(item, dict):
                    continue
                severity = str(item.get("severity", "")).upper()
                if severity in ["CRITICAL", "HIGH"]:
                    findings.append({
                        "tool": "testssl.sh",
                        "severity": severity,
                        "target": item.get("id", "TLS Check"),
                        "finding": item.get("finding", "Issue detected")
                    })
    except Exception as e:
        print(f"[!] Warning: Failed parsing testssl report ({file_path.name}): {e}", file=sys.stderr)
    return findings

def parse_zap(file_path):
    findings = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            sites = data.get("site") or []
            if isinstance(sites, dict):
                sites = [sites]
            for site in sites:
                site_name = site.get("@name", "Web Target")
                alerts = site.get("alerts") or []
                for alert in alerts:
                    risk_code = str(alert.get("riskcode", ""))
                    # Risk code 3 = High, 2 = Medium
                    if risk_code in ["3", "2"]:
                        solution = alert.get("solution") or "N/A"
                        findings.append({
                            "tool": "OWASP ZAP",
                            "severity": "HIGH" if risk_code == "3" else "MEDIUM",
                            "target": site_name,
                            "alert": alert.get("name", "Unnamed Alert"),
                            "url": alert.get("url", "Unknown URL"),
                            "solution": solution[:150] + ("..." if len(solution) > 150 else "")
                        })
    except Exception as e:
        print(f"[!] Warning: Failed parsing ZAP report ({file_path.name}): {e}", file=sys.stderr)
    return findings

def parse_trufflehog(file_path):
    findings = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    detector = entry.get("DetectorName") or entry.get("DetectorType", "Secret")
                    raw = entry.get("Raw", "")
                    masked = raw[:6] + "..." if len(raw) > 6 else "Found"
                    findings.append({
                        "tool": "TruffleHog",
                        "severity": "CRITICAL",
                        "finding": f"Detector: {detector} | File: {entry.get('SourceName', 'Unknown')} | Value: {masked}"
                    })
                except json.JSONDecodeError:
                    if "Found unverified result" in line or "Found verified result" in line:
                        findings.append({
                            "tool": "TruffleHog",
                            "severity": "CRITICAL",
                            "finding": line
                        })
    except Exception as e:
        print(f"[!] Warning: Failed parsing TruffleHog report ({file_path.name}): {e}", file=sys.stderr)
    return findings

def parse_lynis(file_path):
    findings = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith("warning[]=") or line.startswith("suggestion[]="):
                    parts = line.split("=", 1)
                    findings.append({
                        "tool": "Lynis",
                        "severity": "HIGH" if "warning" in parts[0] else "MEDIUM",
                        "finding": parts[1] if len(parts) > 1 else line
                    })
    except Exception as e:
        print(f"[!] Warning: Failed parsing Lynis report ({file_path.name}): {e}", file=sys.stderr)
    return findings

def parse_nmap(file_path):
    findings = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if "/tcp" in line or "/udp" in line:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "open":
                        findings.append({
                            "tool": "Nmap",
                            "severity": "INFO",
                            "target": parts[0],
                            "finding": f"Open port: {line}"
                        })
    except Exception as e:
        print(f"[!] Warning: Failed parsing Nmap report ({file_path.name}): {e}", file=sys.stderr)
    return findings

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 digest_reports.py <path_to_report_directory>")
        sys.exit(1)

    report_dir = Path(sys.argv[1])
    if not report_dir.exists():
        print(f"Error: Directory {report_dir} does not exist.")
        sys.exit(1)

    all_findings = []
    output_filename = "CRITICAL_VULNERABILITIES_SUMMARY.txt"

    for file_path in report_dir.rglob("*"):
        if not file_path.is_file() or file_path.name == output_filename:
            continue

        fname = str(file_path).lower()
        if "trivy" in fname and file_path.suffix == ".json":
            all_findings.extend(parse_trivy(file_path))
        elif "ssl" in fname and file_path.suffix == ".json":
            all_findings.extend(parse_testssl(file_path))
        elif "zap" in fname and file_path.suffix == ".json":
            all_findings.extend(parse_zap(file_path))
        elif "trufflehog" in fname:
            all_findings.extend(parse_trufflehog(file_path))
        elif "lynis" in fname and file_path.suffix in [".dat", ".txt", ".log"]:
            all_findings.extend(parse_lynis(file_path))
        elif "nmap" in fname and file_path.suffix in [".txt", ".nmap"]:
            all_findings.extend(parse_nmap(file_path))

    # Output formatted log
    output_log = report_dir / output_filename
    with open(output_log, "w", encoding='utf-8') as log_file:
        header = (
            f"=== SECURITY AUDIT DIGEST REPORT ===\n"
            f"Generated for: {report_dir.resolve().name}\n"
            f"Total Findings Processed: {len(all_findings)}\n"
            f"====================================\n\n"
        )
        print(header)
        log_file.write(header)

        if not all_findings:
            msg = "No critical, high, or open service findings detected across parsed reports.\n"
            print(msg)
            log_file.write(msg)
            return

        for idx, f in enumerate(all_findings, 1):
            tool = f.get("tool")
            sev = f.get("severity")
            
            entry = f"[{idx}] [{sev}] Tool: {tool}\n"
            if tool == "Trivy":
                entry += (
                    f"    Target:  {f['target']}\n"
                    f"    CVE:     {f['id']} | Package: {f['package']} ({f['installed']}) -> Fixed in: {f['fixed']}\n"
                    f"    Title:   {f['title']}\n"
                )
            elif tool == "testssl.sh":
                entry += f"    Check:   {f['target']}\n    Finding: {f['finding']}\n"
            elif tool == "OWASP ZAP":
                entry += f"    Site:    {f['target']}\n    Alert:   {f['alert']}\n    URL:     {f['url']}\n    Sol:     {f['solution']}\n"
            elif tool == "Nmap":
                entry += f"    Port:    {f['target']}\n    Details: {f['finding']}\n"
            elif tool in ["TruffleHog", "Lynis"]:
                entry += f"    Details: {f['finding']}\n"
            
            entry += "-" * 60 + "\n"
            print(entry)
            log_file.write(entry)

    print(f"\nSummary successfully exported to: {output_log}")

if __name__ == "__main__":
    main()