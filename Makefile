PYTHON ?= python

.PHONY: setup ingest index extract plan run train eval ui test clean

setup:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -e .

ingest:
	$(PYTHON) -m s2s.cli ingest data/raw --project default

index:
	$(PYTHON) -m s2s.cli index --project default

extract:
	$(PYTHON) -m s2s.cli extract --project default

plan:
	$(PYTHON) -m s2s.cli plan --project default

run:
	$(PYTHON) -m s2s.cli run --project default

train:
	$(PYTHON) training/train_lora_t5.py

eval:
	$(PYTHON) training/eval_extraction.py

ui:
	streamlit run ui/app.py

test:
	pytest

clean:
	rm -f out/*.ics out/*.csv
	rm -f models/s2s_lora_t5/*.bin
	find logs -type f -name "*.log" -delete
