"""Command-line entrypoint for the separate blind forecast ledger."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forecast_evaluation import (
    SAMPLE_CLASSES,
    evaluate_records,
    load_forecasts,
    load_results,
    lock_forecast_csv,
    lock_result_csv,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="鎖定並評估與排卦分離的足球盲測預測。")
    commands = parser.add_subparsers(dest="command", required=True)

    lock = commands.add_parser("lock", help="驗證預測草稿並產生不可竄改指紋。")
    lock.add_argument("--input", required=True)
    lock.add_argument("--output", required=True)

    lock_results = commands.add_parser("lock-results", help="驗證賽果草稿並產生獨立指紋。")
    lock_results.add_argument("--input", required=True)
    lock_results.add_argument("--output", required=True)

    evaluate = commands.add_parser("evaluate", help="按 event_at 順序計算準確率與機率品質。")
    evaluate.add_argument("--forecasts", required=True)
    evaluate.add_argument("--results", required=True)
    evaluate.add_argument("--sample-class", choices=SAMPLE_CLASSES, default="CLEAN_BLIND")
    evaluate.add_argument("--minimum-samples", type=int, default=100)
    evaluate.add_argument("--output")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "lock":
        records = lock_forecast_csv(args.input, args.output)
        print(f"locked_forecasts={len(records)} output={args.output}")
        return 0
    if args.command == "lock-results":
        records = lock_result_csv(args.input, args.output)
        print(f"locked_results={len(records)} output={args.output}")
        return 0
    if args.minimum_samples < 1:
        raise ValueError("minimum-samples 必須大於 0。")
    report = evaluate_records(
        load_forecasts(args.forecasts),
        load_results(args.results),
        sample_class=args.sample_class,
        minimum_samples=args.minimum_samples,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
