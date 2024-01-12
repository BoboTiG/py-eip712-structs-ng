from __future__ import annotations

import functools
import json
import operator
import re
from collections import OrderedDict, defaultdict
from collections.abc import Mapping
from typing import Any, NamedTuple

from eth_utils.crypto import keccak

import eip712_structs
from eip712_structs.types import Array, BytesJSONEncoder, EIP712Type, from_solidity_type


class OrderedAttributesMeta(type):
    """Metaclass to ensure struct attribute order is preserved."""

    @classmethod
    def __prepare__(cls, name: str, bases: tuple[type, ...], /, **kwargs: Any) -> Mapping[str, object]:
        return OrderedDict()


class EIP712Struct(EIP712Type, metaclass=OrderedAttributesMeta):
    """A representation of an EIP712 struct. Subclass it to use it.

    Example:
    -------
        from eip712_structs import EIP712Struct, String

        class MyStruct(EIP712Struct):
            some_param = String()

        struct_instance = MyStruct(some_param="some_value")
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(self.type_name, None)
        members = self.get_members()
        self.values = {}
        for name, kind in members:
            value = kwargs.get(name)
            if isinstance(value, dict):
                value = kind(**value)  # type: ignore[operator]
            self.values[name] = value

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.type_name = cls.__name__

    def encode_value(self, value: Any = None) -> bytes:
        """Returns the struct's encoded value.

        A struct's encoded value is a concatenation of the bytes32 representation of each member of the struct.
        Order is preserved.

        :param value: This parameter is not used for structs.
        """
        encoded_values = []
        for name, typ in self.get_members():
            if isinstance(typ, type) and issubclass(typ, EIP712Struct):
                # Nested structs are recursively hashed, with the resulting 32-byte hash appended to the list of values
                sub_struct = self.get_data_value(name)
                encoded_values.append(sub_struct.hash_struct())
            else:
                # Regular types are encoded as normal
                encoded_values.append(typ.encode_value(self.values[name]))
        return b"".join(encoded_values)

    def get_data_value(self, name: str) -> Any:
        """Get the value of the given struct parameter."""
        return self.values.get(name)

    def set_data_value(self, name: str, value: Any) -> None:
        """Set the value of the given struct parameter."""
        if name in self.values:
            self.values[name] = value

    def data_dict(self) -> dict:
        """Provide the entire data dictionary representing the struct.

        Nested structs instances are also converted to dict form.
        """
        return {
            k: v.data_dict()
            if isinstance(v, EIP712Struct)
            else [e.data_dict() for e in v]
            if isinstance(v, list) and len(v) and isinstance(v[0], EIP712Struct)
            else v
            for k, v in self.values.items()
        }

    @classmethod
    def encode_type(cls, resolve: bool = True) -> str:
        """Get the encoded type signature of the struct.

        Nested structs are also encoded if ``resolve`` is ``True``, and appended in alphabetical order.
        """
        member_sigs = [f"{typ.type_name} {name}" for name, typ in cls.get_members()]
        struct_sig = f"{cls.type_name}({','.join(member_sigs)})"

        if resolve:
            reference_structs: list[EIP712Struct] = []
            cls.gather_reference_structs(reference_structs)
            sorted_structs = sorted((s for s in reference_structs if s != cls), key=lambda s: s.type_name)
            for struct in sorted_structs:
                struct_sig += struct.encode_type(resolve=False)

        return struct_sig

    @classmethod
    def gather_reference_structs(cls, struct_lst: list[EIP712Struct]) -> None:
        """Finds reference structs defined in this struct type, and inserts them into the given set."""
        structs = [m[1] for m in cls.get_members() if isinstance(m[1], type) and issubclass(m[1], EIP712Struct)] + [
            m[1].member_type
            for m in cls.get_members()
            if isinstance(m[1], Array) and hasattr(m[1].member_type, "encode_type")
        ]
        for struct in structs:
            if struct not in struct_lst:
                struct_lst.append(struct)  # type: ignore[arg-type]
                struct.gather_reference_structs(struct_lst)  # type: ignore[union-attr]

    @classmethod
    def type_hash(cls) -> bytes:
        """Get the keccak hash of the struct"s encoded type."""
        return keccak(text=cls.encode_type())

    def hash_struct(self) -> bytes:
        """The hash of the struct.

        hash_struct => keccak(type_hash || encode_data)
        """
        return keccak(b"".join([self.type_hash(), self.encode_value()]))

    @classmethod
    def get_members(cls) -> list[tuple[str, EIP712Type]]:
        """A list of tuples of supported parameters.

        Each tuple is (<parameter_name>, <parameter_type>). The list"s order is determined by definition order.
        """
        return [
            m
            for m in cls.__dict__.items()
            if isinstance(m[1], EIP712Type) or (isinstance(m[1], type) and issubclass(m[1], EIP712Struct))
        ]

    @staticmethod
    def _assert_domain(domain: EIP712Struct | None) -> EIP712Struct:
        if result := domain or eip712_structs.default_domain:
            return result
        else:
            raise ValueError("Domain must be provided, or eip712_structs.default_domain must be set.")

    def to_message(self, domain: EIP712Struct | None = None) -> dict:
        """Convert a struct into a dictionary suitable for messaging.

        Dictionary is of the form:
            {
                "primaryType": Name of the primary type,
                "types": Definition of each included struct type (including the domain type)
                "domain": Values for the domain struct,
                "message": Values for the message struct,
            }

        :returns: This struct + the domain in dict form, structured as specified for EIP712 messages.
        """
        domain = self._assert_domain(domain)
        structs = [domain, self]
        self.gather_reference_structs(structs)

        # Build type dictionary
        types = {}
        for struct in structs:
            members_json = [
                {
                    "name": m[0],
                    "type": m[1].type_name,
                }
                for m in struct.get_members()
            ]
            types[struct.type_name] = members_json

        return {
            "primaryType": self.type_name,
            "types": types,
            "domain": domain.data_dict(),
            "message": self.data_dict(),
        }

    def to_message_json(self, domain: EIP712Struct | None = None) -> str:
        message = self.to_message(domain)
        return json.dumps(message, cls=BytesJSONEncoder)

    def signable_bytes(self, domain: EIP712Struct | None = None) -> bytes:
        """Return a ``bytes`` object suitable for signing, as specified for EIP712.

        As per the spec, bytes are constructed as follows:
            ``b"\x19\x01" + domain_hash_bytes + struct_hash_bytes``

        :param domain: The domain to include in the hash bytes. If None, uses ``eip712_structs.default_domain``
        :return: The bytes object
        """
        domain = self._assert_domain(domain)
        return b"\x19\x01" + domain.hash_struct() + self.hash_struct()

    @classmethod
    def from_message(cls, message_dict: dict) -> StructTuple:
        """Convert a message dictionary into two EIP712Struct objects - one for domain, another for the message struct.

        Returned as a StructTuple, which has the attributes ``message`` and ``domain``.

        Example:
        -------
            my_msg = { .. }
            deserialized = EIP712Struct.from_message(my_msg)
            msg_struct = deserialized.message
            domain_struct = deserialized.domain

        :param message_dict: The dictionary, such as what is produced by EIP712Struct.to_message.
        :return: A StructTuple object, containing the message and domain structs.
        """
        structs = {}
        unfulfilled_struct_params = defaultdict(list)

        for type_name in message_dict["types"]:
            # Dynamically construct struct class from dict representation
            struct_from_json = type(type_name, (EIP712Struct,), {})

            for member in message_dict["types"][type_name]:
                # Either a basic solidity type is set, or None if referring to a reference struct (we"ll fill it later)
                member_name = member["name"]
                member_sol_type = from_solidity_type(member["type"])
                setattr(struct_from_json, member_name, member_sol_type)
                if member_sol_type is None:
                    # Track the refs we"ll need to set later.
                    unfulfilled_struct_params[type_name].append((member_name, member["type"]))

            structs[type_name] = struct_from_json

        regex_pattern = r"([a-zA-Z0-9_]+)(\[(\d+)?\])?"

        # Now that custom structs have been parsed, pass through again to set the references
        for struct_name, unfulfilled_member_names in unfulfilled_struct_params.items():
            struct_class = structs[struct_name]
            for name, type_name in unfulfilled_member_names:
                if match := re.match(regex_pattern, type_name):
                    base_type_name = match[1]
                    ref_struct = structs[base_type_name]
                    if match[2]:
                        # The type is an array of the struct
                        arr_len = match[3] or 0  # length of 0 means the array is dynamically sized
                        setattr(struct_class, name, Array(ref_struct, fixed_length=int(arr_len)))
                    else:
                        setattr(struct_class, name, ref_struct)

        primary_struct = structs[message_dict["primaryType"]]
        domain_struct = structs["EIP712Domain"]

        primary_result = primary_struct(**message_dict["message"])
        domain_result = domain_struct(**message_dict["domain"])
        return StructTuple(message=primary_result, domain=domain_result)

    @classmethod
    def _assert_key_is_member(cls, key: str) -> None:
        member_names = {tup[0] for tup in cls.get_members()}
        if key not in member_names:
            raise KeyError(f"{key!r} is not defined for this struct.")

    @classmethod
    def _assert_property_type(cls, key: str, value: EIP712Struct | type[EIP712Struct]) -> None:
        """Eagerly check for a correct member type."""
        members = dict(cls.get_members())
        kind = members[key]

        if isinstance(kind, type) and issubclass(kind, EIP712Struct):
            # We expect an EIP712Struct instance. Assert that's true, and check the struct signature too.
            if isinstance(value, EIP712Struct):  # sourcery skip: merge-nested-ifs
                if value.encode_type(resolve=False) == kind.encode_type(resolve=False):  # type: ignore[attr-defined]
                    return
            raise ValueError(f"Given value is of type {type(value)}, but we expected {kind}")
        else:
            # Since it isn't a nested struct, its an EIP712Type
            try:
                kind.encode_value(value)
            except Exception as e:
                raise ValueError(
                    f"The Python type {type(value)} does not appear to be supported for data type {kind}.",
                ) from e

    def __getitem__(self, key: str) -> Any:
        """Provide access directly to the underlying value dictionary."""
        self._assert_key_is_member(key)
        return self.values.__getitem__(key)

    def __setitem__(self, key: str, value: EIP712Struct) -> None:
        """Provide access directly to the underlying value dictionary."""
        self._assert_key_is_member(key)
        self._assert_property_type(key, value)

        self.values.__setitem__(key, value)

    def __delitem__(self, _: str) -> None:
        raise TypeError("Deleting entries from an EIP712Struct is not allowed")

    def __eq__(self, other: object) -> bool:
        if self is other:
            # Check identity
            return True
        if not isinstance(other, EIP712Struct):
            # Check class
            return False
        # Our structs are considered equal if their type signature and encoded value signature match.
        # E.g., like computing signable bytes but without a domain separator
        return self.encode_type() == other.encode_type() and self.encode_value() == other.encode_value()

    def __hash__(self) -> int:
        value_hashes = [hash(k) ^ hash(v) for k, v in self.values.items()]
        return functools.reduce(operator.xor, value_hashes, hash(self.type_name))


class StructTuple(NamedTuple):
    message: EIP712Struct
    domain: EIP712Struct
