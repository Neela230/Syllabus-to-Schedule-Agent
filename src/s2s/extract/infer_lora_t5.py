from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from peft import PeftModel
import dateparser

from s2s.schemas import AssignmentRecord
from s2s.extract.validate import normalize_assignment
from s2s.utils import log_interaction


SCHEMA_PROMPT = (
    '{'
    '"course": Optional[str], '
    '"assignment_title": str, '
    '"due_datetime_iso": str, '
    '"deliverables": List[str], '
    '"points_or_weight": Optional[str], '
    '"source_doc": str, '
    '"evidence_spans": List[str], '
    '"confidence": float'
    '}'
)


class AssignmentExtractor:
    """Wrapper that loads a LoRA-adapted t5-small or falls back to heuristics."""

    def __init__(
        self,
        base_model: str = "t5-small",
        adapter_dir: Path = Path("models/s2s_lora_t5"),
        force_rule_based: bool = False,
        device: Optional[str] = None,
    ) -> None:
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.base_model_name = base_model
        self.adapter_dir = Path(adapter_dir)
        self.force_rule_based = force_rule_based
        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)
        self.model = None

        if not self.force_rule_based:
            try:
                base = AutoModelForSeq2SeqLM.from_pretrained(self.base_model_name)
                if (self.adapter_dir / "adapter_config.json").exists():
                    self.model = PeftModel.from_pretrained(base, str(self.adapter_dir))
                else:
                    self.model = base
                self.model.to(self.device)
                self.model.eval()
            except Exception as exc:  # pragma: no cover
                self.force_rule_based = True
                log_interaction(
                    tag="extractor_init_fallback",
                    prompt="load_model",
                    response=str(exc),
                    metadata={"adapter_dir": str(self.adapter_dir)},
                )

    def extract(self, text: str, source_doc: str) -> AssignmentRecord:
        """Generate a primary AssignmentRecord from raw text."""
        records = self.extract_many(text, source_doc)
        if records:
            return records[0]
        raw = self._rule_based_single(text)
        record, _ = normalize_assignment(raw, source_doc)
        return record

    def extract_many(self, text: str, source_doc: str) -> List[AssignmentRecord]:
        """Return one or more AssignmentRecords extracted from the document."""
        if self.force_rule_based or self.model is None:
            records = self._rule_based_many(text, source_doc)
            if records:
                return records
            raw = self._rule_based_single(text)
            record, _ = normalize_assignment(raw, source_doc)
            return [record]

        prompt = (
            "Extract JSON with schema: "
            f"{SCHEMA_PROMPT}. "
            "Only output valid JSON. "
            "Input:\n"
            f"{text.strip()}"
        )
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=768).to(self.device)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=512,
                num_beams=4,
                early_stopping=True,
            )
        decoded = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        log_interaction("assignment_prompt", prompt, decoded)
        data = self._repair_json(decoded)
        parsed_items = data if isinstance(data, list) else [data]
        records: List[AssignmentRecord] = []
        for item in parsed_items:
            try:
                record, _ = normalize_assignment(item, source_doc)
                records.append(record)
            except Exception:
                continue
        if records:
            return records
        return self._rule_based_many(text, source_doc)

    def _repair_json(self, candidate: str) -> Dict[str, Any]:
        candidate = candidate.strip()
        if not candidate.startswith("{"):
            start = candidate.find("{")
            end = candidate.rfind("}")
            candidate = candidate[start : end + 1] if start != -1 and end != -1 else "{}"
        candidate = re.sub(r",\s*}", "}", candidate)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            parsed = {}
        return self._normalize_parsed(parsed)

    def _normalize_parsed(self, parsed: Any) -> Any:
        if isinstance(parsed, list):
            return [self._normalize_parsed(item) for item in parsed]
        if not isinstance(parsed, dict):
            parsed = {}
        if "due_datetime_iso" in parsed:
            parsed["due_datetime_iso"] = self._coerce_date(parsed["due_datetime_iso"])
        if "deliverables" in parsed and isinstance(parsed["deliverables"], str):
            parsed["deliverables"] = [parsed["deliverables"]]
        parsed.setdefault("deliverables", [])
        parsed.setdefault("evidence_spans", [])
        parsed.setdefault("assignment_title", "Untitled Assignment")
        parsed.setdefault("confidence", 0.55)
        parsed.setdefault("due_datetime_iso", self._coerce_date("next friday at 11:59 pm"))
        return parsed

    def _coerce_date(self, text: str) -> str:
        if not text:
            return "1970-01-01T00:00:00"
        cleaned = text.strip()
        cleaned = cleaned.lstrip("•-–—* ").strip()
        match = re.search(r"due[^:]*:\s*(.+)", cleaned, flags=re.IGNORECASE)
        if match:
            cleaned = match.group(1)
        cleaned = re.sub(r"^[A-Za-z\s]*[:\-]\s*", "", cleaned, flags=re.IGNORECASE)
        parsed = dateparser.parse(cleaned)
        if not parsed:
            return "1970-01-01T00:00:00"
        return parsed.replace(microsecond=0).isoformat()

    def _rule_based_single(self, text: str) -> Dict[str, Any]:
        records = self._rule_based_many(text, "")
        if records:
            data = records[0].dict_for_storage()
            data["source_doc"] = ""
            return data
        return {
            "course": None,
            "assignment_title": "Untitled Assignment",
            "due_datetime_iso": self._coerce_date("next friday at 11:59 pm"),
            "deliverables": ["Submission per instructions"],
            "points_or_weight": None,
            "source_doc": "",
            "evidence_spans": [],
            "confidence": 0.35,
        }

    def _rule_based_many(self, text: str, source_doc: str) -> List[AssignmentRecord]:
        default_due = "1970-01-01T00:00:00"
        lines: List[Dict[str, str]] = []
        for raw in text.splitlines():
            clean = re.sub(r"\s+", " ", raw.strip().lstrip("•*-–— ")).strip()
            lines.append({"raw": raw, "clean": clean, "lower": clean.lower()})

        course = None
        for info in lines:
            clean = info["clean"]
            lower = info["lower"]
            if not clean:
                continue
            if "course:" in lower:
                course = clean.split(":", 1)[-1].strip()
                break
        if course is None:
            for info in lines:
                if info["clean"]:
                    course = info["clean"]
                    break

        header_keywords = {
            "assignment",
            "milestone",
            "project",
            "homework",
            "lab",
            "quiz",
            "peer",
            "final",
            "midterm",
            "design",
            "reflection",
            "task",
            "deliverable",
            "report",
            "proposal",
            "presentation",
            "brief",
            "showcase",
        }
        header_suffixes = (
            "assignment",
            "project",
            "homework",
            "report",
            "proposal",
            "presentation",
            "forms",
            "packet",
            "guide",
            "brief",
            "critique",
            "journal",
            "deliverables",
            "reflection",
        )
        due_keywords = {
            "due",
            "deadline",
            "submission",
            "submit",
            "report",
            "presentation",
            "demo",
            "meeting",
            "session",
            "exam",
            "quiz",
            "review",
            "showcase",
        }
        forbid_due = {"assigned", "release", "opens"}
        deliverable_keywords = {"deliverable", "deliverables", "submission", "submit"}
        weight_keywords = {"weight", "worth", "points", "percent", "%", "counts"}

        def is_header(clean: str, lower: str) -> bool:
            if not clean:
                return False
            if re.match(r"^\d+[\).]\s*", clean):
                return True
            if ":" in clean:
                prefix = clean.split(":", 1)[0].lower()
                base = prefix.split()[0]
                if prefix in header_keywords or base in header_keywords:
                    return True
            if clean.isupper() and len(clean) <= 40:
                return True
            return False

        def strip_title(title: str) -> str:
            cleaned = re.sub(r"^\d+[\).]\s*", "", title).strip(":-• ")
            parts = cleaned.split(":", 1)
            if len(parts) == 2 and parts[0].lower() in header_keywords:
                cleaned = parts[1].strip()
            return cleaned or title.strip()

        assignments: List[AssignmentRecord] = []
        seen: Dict[tuple, int] = {}
        current_title: Optional[str] = None

        for idx, info in enumerate(lines):
            clean = info["clean"]
            lower = info["lower"]
            if not clean:
                continue

            due_iso = self._coerce_date(clean)
            if (
                due_iso != default_due
                and not any(forbidden in lower for forbidden in forbid_due)
                and (
                    any(keyword in lower for keyword in due_keywords)
                    or re.search(r"\b(at|by)\b", lower)
                )
            ):
                if "draft" in lower and "final" not in lower:
                    continue
                if "session" in lower and "due" not in lower and "submission" not in lower:
                    continue
                if "demo date" in lower and "submission" not in lower:
                    continue

                title = strip_title(current_title or clean)

                deliverables: List[str] = []
                points: Optional[str] = None

                for j in range(idx + 1, min(len(lines), idx + 6)):
                    nxt = lines[j]
                    nxt_clean = nxt["clean"]
                    nxt_lower = nxt["lower"]
                    if not nxt_clean:
                        break
                    if is_header(nxt_clean, nxt_lower):
                        break
                    if self._coerce_date(nxt_clean) != default_due and any(
                        keyword in nxt_lower for keyword in due_keywords
                    ):
                        break
                    if any(keyword in nxt_lower for keyword in deliverable_keywords):
                        value = re.sub(
                            r"^[A-Za-z\s]+:\s*",
                            "",
                            nxt_clean,
                            flags=re.IGNORECASE,
                        ).strip()
                        if value:
                            deliverables.append(value)
                    if points is None and any(keyword in nxt_lower for keyword in weight_keywords):
                        points = nxt_clean

                if points is None:
                    for j in range(idx - 1, idx - 4, -1):
                        if j < 0:
                            break
                        prev_clean = lines[j]["clean"]
                        prev_lower = lines[j]["lower"]
                        if any(keyword in prev_lower for keyword in weight_keywords):
                            points = prev_clean
                            break

                if not deliverables:
                    deliverables = ["Submission per instructions"]

                key = (title.lower(), due_iso)
                if key in seen:
                    idx_existing = seen[key]
                    existing = assignments[idx_existing]
                    updates: Dict[str, Any] = {}
                    if existing.points_or_weight is None and points:
                        updates["points_or_weight"] = points
                    if (
                        existing.deliverables == ["Submission per instructions"]
                        and deliverables != ["Submission per instructions"]
                    ):
                        updates["deliverables"] = deliverables
                    if updates:
                        assignments[idx_existing] = existing.copy(update=updates)
                    continue

                raw = {
                    "course": course,
                    "assignment_title": title,
                    "due_datetime_iso": due_iso,
                    "deliverables": deliverables,
                    "points_or_weight": points,
                    "source_doc": source_doc,
                    "evidence_spans": [clean],
                    "confidence": 0.35,
                }
                record, _ = normalize_assignment(raw, source_doc or "rule_based")
                assignments.append(record)
                seen[key] = len(assignments) - 1

                continue

            if is_header(clean, lower):
                current_title = strip_title(clean)
                continue

            if clean and any(clean.lower().endswith(suffix) for suffix in header_suffixes):
                current_title = strip_title(clean)
                continue

            elif (
                current_title is None
                and clean
                and clean[0].isalpha()
                and clean[0].isupper()
                and ":" not in clean
                and len(clean.split()) <= 8
                and not lower.startswith(("course", "instructor", "notes", "semester", "policies"))
            ):
                current_title = strip_title(clean)

        log_interaction(
            "rule_based_extract_many",
            text[:1200],
            json.dumps([record.dict_for_storage() for record in assignments]),
        )
        return assignments
