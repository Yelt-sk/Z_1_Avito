from __future__ import annotations

from collections import Counter
from typing import Any

from .models import Item
from .pipeline import AvitoSplitterPipeline


def evaluate_examples(pipeline: AvitoSplitterPipeline, examples: list[dict[str, Any]]) -> dict[str, Any]:
    should_split_correct = 0
    tp = fp = fn = 0
    error_rows: list[dict[str, Any]] = []
    error_types: Counter[str] = Counter()

    for example in examples:
        item = Item.from_dict(example)
        expected_mc_ids = {int(value) for value in example.get("expectedDraftMcIds", [])}
        expected_should_split = bool(example.get("shouldSplit", expected_mc_ids))

        prediction = pipeline.predict(item, include_debug=True)
        predicted_mc_ids = {draft.mc_id for draft in prediction.drafts}

        if prediction.should_split == expected_should_split:
            should_split_correct += 1

        local_tp = len(predicted_mc_ids & expected_mc_ids)
        local_fp = len(predicted_mc_ids - expected_mc_ids)
        local_fn = len(expected_mc_ids - predicted_mc_ids)
        tp += local_tp
        fp += local_fp
        fn += local_fn

        if local_fp or local_fn or prediction.should_split != expected_should_split:
            if local_fp:
                error_types["false_positive"] += local_fp
            if local_fn:
                error_types["false_negative"] += local_fn
            if prediction.should_split != expected_should_split:
                error_types["should_split_mismatch"] += 1
            error_rows.append(
                {
                    "itemId": item.item_id,
                    "expectedShouldSplit": expected_should_split,
                    "predictedShouldSplit": prediction.should_split,
                    "expectedDraftMcIds": sorted(expected_mc_ids),
                    "predictedDraftMcIds": sorted(predicted_mc_ids),
                    "debug": prediction.debug,
                }
            )

    total = max(1, len(examples))
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 2 * precision * recall / max(1e-9, precision + recall)
    return {
        "count": len(examples),
        "shouldSplitAccuracy": should_split_correct / total,
        "microcategoryPrecision": precision,
        "microcategoryRecall": recall,
        "microcategoryF1": f1,
        "truePositives": tp,
        "falsePositives": fp,
        "falseNegatives": fn,
        "errorTypes": dict(error_types),
        "errors": error_rows,
    }


def calibrate_thresholds(pipeline: AvitoSplitterPipeline, examples: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = evaluate_examples(pipeline, examples)
    recommendation = (
        "Increase bundled penalties or tighten shortlist if false positives dominate."
        if metrics["falsePositives"] > metrics["falseNegatives"]
        else "Improve phrase coverage or relax shortlist if false negatives dominate."
    )
    return {
        "currentMetrics": metrics,
        "recommendedAction": recommendation,
        "defaultPolicy": "precision_first",
    }
