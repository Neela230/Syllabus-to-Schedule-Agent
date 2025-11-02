#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from datasets import DatasetDict, concatenate_datasets, load_dataset


def build_dataset(seed_path: Path, synth_path: Path) -> DatasetDict:
    seed = load_dataset("json", data_files=str(seed_path))["train"]
    synth = load_dataset("json", data_files=str(synth_path))["train"]
    train = concatenate_datasets([seed, synth])
    valid = train.train_test_split(test_size=0.1, seed=42)
    return DatasetDict(
        train=valid["train"],
        validation=valid["test"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="training/data/seed.jsonl")
    parser.add_argument("--synth", default="training/data/synth.jsonl")
    parser.add_argument("--out_dir", default="training/data/dataset")
    args = parser.parse_args()

    dataset = build_dataset(Path(args.seed), Path(args.synth))
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    dataset.save_to_disk(args.out_dir)
    print(f"Saved dataset to {args.out_dir}")


if __name__ == "__main__":
    main()
