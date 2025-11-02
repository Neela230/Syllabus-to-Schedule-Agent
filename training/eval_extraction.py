#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
from datasets import load_from_disk
from tabulate import tabulate

from s2s.extract import AssignmentExtractor


def compute_metrics(golds: List[Dict], preds: List[Dict]) -> Dict[str, float]:
    fields = ["course", "assignment_title", "due_datetime_iso", "points_or_weight"]
    exact = []
    for gold, pred in zip(golds, preds):
        exact.append(int(all(pred.get(f) == gold.get(f) for f in fields)))

    def list_to_set(items):
        return set(items)

    micro_tp = 0
    micro_fn = 0
    micro_fp = 0
    for gold, pred in zip(golds, preds):
        gold_set = list_to_set(gold.get("deliverables", []))
        pred_set = list_to_set(pred.get("deliverables", []))
        micro_tp += len(gold_set & pred_set)
        micro_fp += len(pred_set - gold_set)
        micro_fn += len(gold_set - pred_set)

    denom = micro_tp + 0.5 * (micro_fp + micro_fn)
    f1 = micro_tp / denom if denom else 1.0

    def parse_date(value: str) -> np.datetime64:
        return np.datetime64(value.replace("Z", "+00:00"))

    date_diffs = []
    for gold, pred in zip(golds, preds):
        try:
            diff = abs(
                (parse_date(gold["due_datetime_iso"]) - parse_date(pred["due_datetime_iso"]))
                .astype("timedelta64[m]")
                .astype(float)
            )
            date_diffs.append(diff / 60.0)
        except Exception:
            date_diffs.append(np.inf)

    return {
        "field_exact_match": float(np.mean(exact)),
        "deliverable_micro_f1": f1,
        "date_accuracy_hours": float(np.mean(date_diffs)),
    }


def main() -> None:
    dataset_dir = Path("training/data/dataset")
    if not dataset_dir.exists():
        raise SystemExit("Dataset missing. Run training/collate.py first.")
    dataset = load_from_disk(str(dataset_dir))
    extractor = AssignmentExtractor(force_rule_based=True)
    golds: List[Dict] = []
    preds: List[Dict] = []
    for sample in dataset["validation"]:
        gold = json.loads(sample["target_json"])
        record = extractor.extract(sample["input_text"], "eval")
        golds.append(gold)
        preds.append(record.dict_for_storage())
    metrics = compute_metrics(golds, preds)
    table = tabulate(metrics.items(), headers=["Metric", "Value"])
    print(table)


if __name__ == "__main__":
    main()
