"""Command-line entry point: python -m simwhy run examples/pressurized_jump.json"""
import argparse
import csv
import json
from pathlib import Path
from dataclasses import asdict
from .core import Config, simulate, step_refinement
from .viz import render_svg


def main():
    parser=argparse.ArgumentParser(description="Run low-cost physics hypotheses with explicit limitations.")
    sub=parser.add_subparsers(dest="command", required=True)
    run=sub.add_parser("run", help="Run one ideal-gas pulse model")
    run.add_argument("configuration", type=Path)
    run.add_argument("--out", type=Path, default=Path("results/demo"))
    args=parser.parse_args()
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
