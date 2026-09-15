.PHONY: setup key test-batch run export

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	@echo "Setup complete. Run 'source .venv/bin/activate' (or '.venv\\Scripts\\activate' on Windows) to activate the environment."

key:
	bash scripts/get_opensea_key.sh

test-batch:
	python -m src.cli batch wallets.txt --out data/results.csv --limit 5

run:
	python -m src.cli batch wallets.txt --out data/results.csv

export:
	python -m src.cli export --out data/results.csv
