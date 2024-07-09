#!/bin/bash
set -e
python -m ruff format src
python -m ruff check --fix src/eip712_structs
python -m mypy src/eip712_structs
