from web3 import EthereumTesterProvider, Web3

import pytest

from tests.integration.contract_sources.contract_data.contract import TEST_CONTRACT_ABI, TEST_CONTRACT_DATA


@pytest.fixture(scope="session")
def w3() -> Web3:
    """Provide a Web3 client to interact with a local chain."""
    provider = EthereumTesterProvider()
    return Web3(provider)


@pytest.fixture(scope="session")
def contract(w3: Web3) -> str:
    """Deploys the test contract to the local chain, and returns a Web3.py Contract to interact with it."""
    contract = w3.eth.contract(**TEST_CONTRACT_DATA)
    func = contract.constructor()
    receipt = w3.eth.wait_for_transaction_receipt(func.transact())
    return w3.eth.contract(abi=TEST_CONTRACT_ABI, address=receipt["contractAddress"])
