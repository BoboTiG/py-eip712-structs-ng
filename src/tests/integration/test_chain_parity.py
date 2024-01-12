import os

from eip712_structs import Address, Array, Boolean, Bytes, EIP712Struct, Int, String, Uint
from web3 import Web3


# These structs must match the struct in tests/integration/contract_sources/contract.sol
class Bar(EIP712Struct):
    bar_uint = Uint(256)


# TODO Add Array type (w/ appropriate test updates) to this struct.
class Foo(EIP712Struct):
    s = String()
    u_i = Uint(256)
    s_i = Int(8)
    a = Address()
    b = Boolean()
    bytes_30 = Bytes(30)
    dyn_bytes = Bytes()
    bar = Bar
    arr = Array(Bytes(1))


def get_chain_hash(contract, s, u_i, s_i, a, b, bytes_30, dyn_bytes, bar_uint, arr) -> bytes:
    """Uses the contract to create and hash a Foo struct with the given parameters."""
    return contract.functions.hashFooStructFromParams(
        s,
        u_i,
        s_i,
        a,
        b,
        bytes_30,
        dyn_bytes,
        bar_uint,
        arr,
    ).call()


def test_encoded_types(contract):
    """Checks that the encoded types (and the respective hashes) of our structs match."""
    local_bar_sig = Bar.encode_type()
    remote_bar_sig = contract.functions.BarSig().call()
    assert local_bar_sig == remote_bar_sig

    local_foo_sig = Foo.encode_type()
    remote_foo_sig = contract.functions.FooSig().call()
    assert local_foo_sig == remote_foo_sig

    local_bar_hash = Bar.type_hash()
    remote_bar_hash = contract.functions.Bar_TYPEHASH().call()
    assert local_bar_hash == remote_bar_hash

    local_foo_hash = Foo.type_hash()
    remote_foo_hash = contract.functions.Foo_TYPEHASH().call()
    assert local_foo_hash == remote_foo_hash

    array_type = Array(Bytes(1))
    bytes_array = [os.urandom(1) for _ in range(5)]
    local_encoded_array = array_type.encode_value(bytes_array)
    remote_encoded_array = contract.functions.encodeBytes1Array(bytes_array).call()
    assert local_encoded_array == remote_encoded_array


def test_chain_hash_matches(contract):
    """Assert that the hashes we derive locally match the hashes derived on-chain."""
    # Initialize basic values
    s = "some string"
    u_i = 1234
    s_i = -7
    a = Web3.to_checksum_address(f"0x{os.urandom(20).hex()}")
    b = True
    bytes_30 = os.urandom(30)
    dyn_bytes = os.urandom(50)
    arr = [os.urandom(1) for _ in range(5)]

    # Initialize a Bar struct, and check it standalone
    bar_uint = 1337
    bar_struct = Bar(bar_uint=bar_uint)
    local_bar_hash = bar_struct.hash_struct()
    remote_bar_hash = contract.functions.hashBarStructFromParams(bar_uint).call()
    assert local_bar_hash == remote_bar_hash

    # Initialize a Foo struct (including the Bar struct above) and check the hashes
    foo_struct = Foo(s=s, u_i=u_i, s_i=s_i, a=a, b=b, bytes_30=bytes_30, dyn_bytes=dyn_bytes, bar=bar_struct, arr=arr)
    local_foo_hash = foo_struct.hash_struct()
    remote_foo_hash = get_chain_hash(contract, s, u_i, s_i, a, b, bytes_30, dyn_bytes, bar_uint, arr)
    assert local_foo_hash == remote_foo_hash
