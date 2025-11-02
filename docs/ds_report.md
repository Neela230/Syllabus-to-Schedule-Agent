# Data Science Report

## Objective

Train a lightweight extractor that maps syllabus passages to the `AssignmentRecord` JSON schema, supporting downstream scheduling automation.

## Data Sources

- **Seed Set (50)**: Manually curated examples from diverse CS/engineering syllabi.
- **Synthetic Set (150)**: Generated via `training/make_synth.py` using deterministic templates, seeded with `random.seed(1337)` for reproducibility.

Both datasets include `input_text` (raw snippet) and `target_json` (schema-compliant label).

## Training Setup

- **Model**: `t5-small` with LoRA adapters (`r=16`, `alpha=32`, dropout 0.05).
- **Tokenization**: Max input length 512, target 256.
- **Hyperparameters**: learning rate 2e-4, batch size 4, epochs 5, mixed precision when CUDA is available.
- **Optimizer**: Adafactor via `Trainer`.
- **Artifacts**: Saved to `models/s2s_lora_t5/`.

## Evaluation

`training/eval_extraction.py` uses the rule-based extractor for baseline metrics (LoRA weights optional but recommended):

- **Field Exact Match**: Average of correct course/title/due/weight fields.
- **Deliverable Micro-F1**: Treat each deliverable string as token.
- **Date Accuracy**: Mean absolute error in hours between predicted and true due times.

Outputs a table via `tabulate`.

## Error Analysis (Example Findings)

- **Ambiguous Dates**: Relative phrases (“next Friday”) degrade rule-based fallback; LoRA model handles better once trained.
- **Deliverable Variety**: Multi-item deliverables need consistent separators; training data includes pairs/triples to generalize.
- **Course Missing**: Some announcements omit the course; extractor defaults to `null`, planner still operates.

## Future Work

- Expand seed data with humanities courses for broader vocabulary.
- Add augmentation for time zones and recurring tasks.
- Integrate confidence calibration using temperature scaling against validation metrics.
