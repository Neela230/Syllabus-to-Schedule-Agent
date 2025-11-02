#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import torch
from datasets import load_from_disk
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Trainer,
    TrainingArguments,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="training/data/dataset")
    parser.add_argument("--output", default="models/s2s_lora_t5")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch_size", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = load_from_disk(args.dataset)
    tokenizer = AutoTokenizer.from_pretrained("t5-small")
    model = AutoModelForSeq2SeqLM.from_pretrained("t5-small")

    def preprocess(batch):
        inputs = tokenizer(
            batch["input_text"],
            padding="max_length",
            truncation=True,
            max_length=512,
        )
        labels = tokenizer(
            batch["target_json"],
            padding="max_length",
            truncation=True,
            max_length=256,
        )
        inputs["labels"] = labels["input_ids"]
        return inputs

    tokenized = dataset.map(preprocess, batched=True)

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q", "v"],
        lora_dropout=0.05,
        bias="none",
        task_type="SEQ_2_SEQ_LM",
    )
    peft_model = get_peft_model(model, lora_config)
    collator = DataCollatorForSeq2Seq(tokenizer, model=peft_model)

    training_args = TrainingArguments(
        output_dir=args.output,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=10,
        fp16=torch.cuda.is_available(),
    )

    trainer = Trainer(
        model=peft_model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        data_collator=collator,
        tokenizer=tokenizer,
    )
    trainer.args.predict_with_generate = True

    trainer.train()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    peft_model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print(f"Saved LoRA adapter to {args.output}")


if __name__ == "__main__":
    main()
