#!/bin/bash
#
# Compile contracts for our integration tests.
#
# Usage: cd src/tests/integration/contract_sources && ./compile.sh
#
[ ! -d contract_data ] && mkdir -v contract_data
python _compile_contracts.py -f contract.sol -v '0.8.19'
