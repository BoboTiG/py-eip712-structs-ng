from eip712_structs.domain_separator import make_domain
from eip712_structs.struct import EIP712Struct
from eip712_structs.types import Address, Array, Boolean, Bytes, Int, String, Uint

__version__ = "2.0.1"
__all__ = (
    "make_domain",
    "EIP712Struct",
    "Address",
    "Array",
    "Boolean",
    "Bytes",
    "Int",
    "String",
    "Uint",
)
default_domain = None
