from __future__ import annotations

import argparse
import sys

from .data_loading import load_examples, load_item, load_microcategories
from .evaluation import calibrate_thresholds, evaluate_examples
from .pipeline import AvitoSplitterPipeline, PipelineConfig
from .utils import dump_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="avito-splitter")
    subparsers = parser.add_subparsers(dest="command", required=True)

    predict = subparsers.add_parser("predict", help="Predict split drafts for one item.")
    predict.add_argument("--item", required=True)
    predict.add_argument("--dict", required=True, dest="dictionary")
    predict.add_argument("--debug", action="store_true")
    predict.add_argument("--disable-qwen", action="store_true")

    evaluate = subparsers.add_parser("evaluate", help="Evaluate the pipeline on labeled examples.")
    evaluate.add_argument("--examples", required=True)
    evaluate.add_argument("--dict", required=True, dest="dictionary")
    evaluate.add_argument("--disable-qwen", action="store_true")

    calibrate = subparsers.add_parser("calibrate", help="Run a lightweight calibration report.")
    calibrate.add_argument("--examples", required=True)
    calibrate.add_argument("--dict", required=True, dest="dictionary")
    calibrate.add_argument("--disable-qwen", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    microcategories = load_microcategories(args.dictionary)
    pipeline = AvitoSplitterPipeline(
        microcategories,
        config=PipelineConfig(enable_qwen=not getattr(args, "disable_qwen", False)),
    )

    if args.command == "predict":
        result = pipeline.predict(load_item(args.item), include_debug=args.debug)
        print(dump_json(result.to_public_dict(include_debug=args.debug)))
        return 0
    if args.command == "evaluate":
        print(dump_json(evaluate_examples(pipeline, load_examples(args.examples))))
        return 0
    if args.command == "calibrate":
        print(dump_json(calibrate_thresholds(pipeline, load_examples(args.examples))))
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
