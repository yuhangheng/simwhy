"""Command-line entry point: python -m simwhy run examples/pressurized_jump.json
or: python -m simwhy audit <directory> [--format text|json]
"""
import argparse
import csv
import json
import sys
from pathlib import Path
from dataclasses import asdict
from .core import Config, simulate, step_refinement
from .viz import render_svg
from .audit import audit_directory, format_report_text, format_report_json
from .coupling_gate import assess_evidence


def main():
    parser=argparse.ArgumentParser(description="Run low-cost physics hypotheses with explicit limitations.")
    sub=parser.add_subparsers(dest="command", required=True)
    run=sub.add_parser("run", help="Run one ideal-gas pulse model")
    run.add_argument("configuration", type=Path)
    run.add_argument("--out", type=Path, default=Path("results/demo"))
    audit=sub.add_parser("audit", help="Audit a coupled-simulation directory for failure patterns")
    audit.add_argument("directory", type=Path, help="Directory to audit")
    audit.add_argument("--format", choices=["text", "json"], default="text")
    gate=sub.add_parser("coupling-audit", help="Screen fixed-geometry CFD and pressure-feedback ablation evidence")
    gate.add_argument("evidence", type=Path, help="JSON of derived CFD pairs and synchronized signal traces")
    gate.add_argument("--format", choices=["text", "json"], default="text")
    args=parser.parse_args()

    if args.command == "audit":
        if not args.directory.exists() or not args.directory.is_dir():
            print(f"error: directory not found: {args.directory}", file=sys.stderr)
            sys.exit(2)
        report = audit_directory(args.directory)
        if args.format == "json":
            print(format_report_json(report))
        else:
            print(format_report_text(report))
        # Exit code: 1 if any critical failure
        sys.exit(1 if report.fail_count > 0 else 0)

    if args.command == "coupling-audit":
        try:
            evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
            result = assess_evidence(evidence)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            print(f"coupling evidence error: {exc}", file=sys.stderr)
            sys.exit(2)
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print(f"Coupling audit: {result['verdict']}")
            print(f"Fixed-geometry CFD: {result['cfd']['status']}")
            print(f"Pressure-feedback ablation: {result['pressure_ablation']['status']}")
            print("Result is only an evidence screen, not physical validation.")
        sys.exit(0 if result['verdict'] == "NUMERICALLY_SUPPORTED_REQUIRES_PHYSICAL_VALIDATION" else 1)

    c=Config.from_dict(json.loads(args.configuration.read_text(encoding="utf-8")))
    rows, report=simulate(c)
    report["step_refinement"]=step_refinement(c)
    report["input_configuration"]=asdict(c)
    report["source_configuration"]=str(args.configuration)
    out=args.out
    out.mkdir(parents=True, exist_ok=True)
    with (out/"trajectory.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (out/"summary.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (out/"trajectory.svg").write_text(render_svg(rows,report),encoding="utf-8")
    print(f"Peak altitude: {report['peak_altitude_m']:.4f} m")
    print(f"Initial thrust/weight: {report['initial_thrust_to_weight']:.2f}")
    print(f"Gas used: {report['gas_consumed_kg']:.2f} kg")
    print(f"Time-step peak difference: {report['step_refinement']['peak_difference_relative']:.3%}")
    print(f"Model credibility: {report['status']}")
    print(f"Artifacts: {out.resolve()}")


if __name__=="__main__":
    main()
