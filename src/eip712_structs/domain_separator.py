from __future__ import annotations

from eip712_structs.struct import EIP712Struct
from eip712_structs.types import Address, Bytes, String, Uint


def make_domain(
    name: str | None = None,
    version: str | None = None,
    chainId: int | None = None,
    verifyingContract: str | None = None,
    salt: str | None = None,
) -> EIP712Struct:
    """Helper method to create the standard EIP712Domain struct for you.

    Per the standard, if a value is not used then the parameter is omitted from the struct entirely.
    """
    if all(i is None for i in [name, version, chainId, verifyingContract, salt]):
        raise ValueError("At least one argument must be given.")

    class EIP712Domain(EIP712Struct):
        pass

    kwargs: dict[str, str | int] = {}
    if name is not None:
        EIP712Domain.name = String()  # type: ignore[attr-defined]
        kwargs["name"] = str(name)
    if version is not None:
        EIP712Domain.version = String()  # type: ignore[attr-defined]
        kwargs["version"] = str(version)
    if chainId is not None:
        EIP712Domain.chainId = Uint(256)  # type: ignore[attr-defined]
        kwargs["chainId"] = int(chainId)
    if verifyingContract is not None:
        EIP712Domain.verifyingContract = Address()  # type: ignore[attr-defined]
        kwargs["verifyingContract"] = verifyingContract
    if salt is not None:
        EIP712Domain.salt = Bytes(32)  # type: ignore[attr-defined]
        kwargs["salt"] = salt

    return EIP712Domain(**kwargs)
