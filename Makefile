.PHONY: install fmt lint typecheck test all build_lambda_scan_ebs test_lambda_scan_ebs

install:
	pip install -e ".[dev]"

fmt:
	ruff format src/ tests/

lint:
	ruff check src/ tests/

typecheck:
	mypy src/ tests/

test:
	pytest tests/

test_lambda_scan_ebs:
	pytest tests/ -k ec2_unattached -v

build_lambda_scan_ebs:
	mkdir -p build
	cp -r src/saverbot build/
	cp -r src/lambdas build/
	cd build && zip -r ../lambda-scan-ebs.zip saverbot lambdas
	rm -rf build
	@echo "Lambda package created: lambda-scan-ebs.zip"

all: fmt lint typecheck test

