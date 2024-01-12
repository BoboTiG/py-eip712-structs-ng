# EIP-712 Structs

[![PyPI version](https://badge.fury.io/py/eip712-structs-ng.svg)](https://badge.fury.io/py/eip712-structs-ng)
[![Python versions](https://img.shields.io/pypi/pyversions/eip712-structs-ng.svg)](https://pypi.python.org/pypi/eip712-structs-ng)

A Python interface for [EIP-712](https://github.com/ethereum/EIPs/blob/master/EIPS/eip-712.md) struct construction.

> Note: this is a **drop-in replacement** for the [eip712-structs](https://pypi.org/project/eip712-structs/) module, which is dead since 2019.
>
> It brings the same objects as its predecessor with some sugar:
> - the code is fully typed
> - dependencies were cleaned up
> - support for Python 3.8 and newer
> - code modernization, including Sourcery clean-up
> - 99% tests coverage
> - simplified testing (no more need for docker)

> **Warning**: Remove any installation of the old `eip712-structs` module to prevent import mismatches: `python -m pip uninstall -y eip712-structs`

In this module, a "struct" is structured data as defined in the standard.
It is not the same as the Python standard library's [struct](https://docs.python.org/3/library/struct.html).

## Supported Python Versions

Python 3.8 and newer.

## Install

```bash
python -m pip install -U eip712-structs-ng
```

## Usage

See [API.md](API.md) for a succinct summary of available methods.

Examples & details below.

## Quickstart

Say we want to represent the following struct, convert it to a message and sign it:

```solidity
struct MyStruct {
    string some_string;
    uint256 some_number;
}
```

With this module, that would look like:

```python
from eip712_structs import make_domain, EIP712Struct, String, Uint


# Make a domain separator
domain = make_domain(name='Some name', version='1.0.0')

# Define your struct type
class MyStruct(EIP712Struct):
    some_string = String()
    some_number = Uint(256)

# Create an instance with some data
mine = MyStruct(some_string="hello world", some_number=1234)

# Values can be get/set dictionary-style:
mine["some_number"] = 4567
assert mine["some_string"] == "hello world"
assert mine["some_number"] == 4567

# Into a message dict - domain required
my_msg = mine.to_message(domain)

# Into message JSON - domain required.
# This method converts bytes types for you, which the default JSON encoder won't handle.
my_msg_json = mine.to_message_json(domain)

# Into signable bytes - domain required
my_bytes = mine.signable_bytes(domain)
```

See [Member Types](#member-types) for more information on supported types.

### Dynamic Construction

Attributes may be added dynamically as well.
This may be necessary if you want to use a reserved keyword like `from`:

```python
from eip712_structs import EIP712Struct, Address


class Message(EIP712Struct):
    pass

Message.to = Address()
setattr(Message, "from", Address())

# At this point, `Message` is equivalent to `struct Message { address to; address from; }`
```

### The Domain Separator

EIP-712 specifies a domain struct, to differentiate between identical structs that may be unrelated.
A helper method exists for this purpose.
All values to the `make_domain()` function are optional - but at least one must be defined.
If omitted, the resulting domain struct's definition leaves out the parameter entirely.

The full signature:

```python
make_domain(name: string, version: string, chainId: uint256, verifyingContract: address, salt: bytes32)
```

#### Setting a Default Domain

Constantly providing the same domain can be cumbersome. You can optionally set a default, and then forget it.
It is automatically used by `.to_message()` and `.signable_bytes()`:

```python
import eip712_structs


foo = SomeStruct()

my_domain = eip712_structs.make_domain(name="hello world")
eip712_structs.default_domain = my_domain

assert foo.to_message() == foo.to_message(my_domain)
assert foo.signable_bytes() == foo.signable_bytes(my_domain)
```

## Member Types

### Basic Types

EIP712's basic types map directly to solidity types:

```python
from eip712_structs import Address, Boolean, Bytes, Int, String, Uint


Address()  # Solidity's 'address'
Boolean()  # 'bool'
Bytes()    # 'bytes'
Bytes(N)   # 'bytesN' - N must be an int from 1 through 32
Int(N)     # 'intN' - N must be a multiple of 8, from 8 to 256
String()   # 'string'
Uint(N)    # 'uintN' - N must be a multiple of 8, from 8 to 256
```

Use like:

```python
from eip712_structs import EIP712Struct, Address, Bytes


class Foo(EIP712Struct):
    member_name_0 = Address()
    member_name_1 = Bytes(5)
    # etc.
```

### Struct References

In addition to holding basic types, EIP-712 structs may also hold other structs!
Usage is almost the same - the difference is you don't "instantiate" the class.

Example:

```python
from eip712_structs import EIP712Struct, String


class Dog(EIP712Struct):
    name = String()
    breed = String()

class Person(EIP712Struct):
    name = String()
    dog = Dog  # Take note - no parentheses!

# Dog "stands alone"
Dog.encode_type()  # Dog(string name,string breed)

# But Person knows how to include Dog
Person.encode_type()  # Person(string name,Dog dog)Dog(string name,string breed)
```

Instantiating the structs with nested values may be done a couple different ways:

```python
# Method one: set it to a struct
dog = Dog(name="Mochi", breed="Corgi")
person = Person(name="E.M.", dog=dog)

# Method two: set it to a dict - the underlying struct is built for you
person = Person(
    name="E.M.",
    dog={
        "name": "Mochi",
        "breed": "Corgi",
    }
)
```

### Arrays

Arrays are also supported for the standard:

```python
array_member = Array(<item_type>[, <optional_length>])
```

- `<item_type>` - The basic type or struct that will live in the array
- `<optional_length>` - If given, the array is set to that length.

For example:

```python
dynamic_array = Array(String())      # String[] dynamic_array
static_array  = Array(String(), 10)  # String[10] static_array
struct_array  = Array(MyStruct, 10)  # MyStruct[10] - again, don't instantiate structs like the basic types
```

## Development

Contributions always welcome.

Setup a development environment:

```bash
python -m venv venv
. venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -U pip
python -m pip install -e '.[tests]'
```

Run tests:

```bash
python -m pytest
```

Run linters before submitting a PR:

```bash
./checks.sh
```

### Solidity Contract

When changing the code of the Solidity test contract, you will have to regenerate its Python data code:

```shell
cd src/tests/integration/contract_sources && ./compile.sh
```

That's it! Do not forget to commit those changes.

## Deploying a New Version

- Bump the version number in `__init__.py`, commit it into the `main` branch.
- Make a release tag on the `main` branch in GitHub.
- The CI will handle the PyPi publishing.

## Shameless Plug

Originally written by [ConsenSys](https://consensys.net) for the world! And continued by [BoboTiG](https://github.com/BoboTiG)! :heart:
