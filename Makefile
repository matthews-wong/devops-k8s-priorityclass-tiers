.PHONY: validate schema priorities test lint

validate: schema priorities test lint ## Run every local check

schema:
	kubeconform -strict -summary manifests/*.yaml

priorities:
	scripts/check_priority.py

test:
	python3 -m unittest discover -s scripts -p 'test_*.py'

lint:
	actionlint
