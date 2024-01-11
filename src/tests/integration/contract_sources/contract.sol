pragma solidity 0.8.19;
pragma experimental ABIEncoderV2;

contract TestContract {
    /********************
     * Constant Members *
     ********************/
    struct Bar {
        uint256 bar_uint;
    }

    struct Foo {
        string s;
        uint256 u_i;
        int8 s_i;
        address a;
        bool b;
        bytes30 bytes_30;
        bytes dyn_bytes;
        Bar bar;
        bytes1[] arr;
    }

    string public constant BarSig = "Bar(uint256 bar_uint)";
    string public constant FooSig =
        "Foo(string s,uint256 u_i,int8 s_i,address a,bool b,bytes30 bytes_30,bytes dyn_bytes,Bar bar,bytes1[] arr)Bar(uint256 bar_uint)";

    bytes32 public constant Bar_TYPEHASH =
        keccak256(abi.encodePacked("Bar(uint256 bar_uint)"));
    bytes32 public constant Foo_TYPEHASH =
        keccak256(
            abi.encodePacked(
                "Foo(string s,uint256 u_i,int8 s_i,address a,bool b,bytes30 bytes_30,bytes dyn_bytes,Bar bar,bytes1[] arr)Bar(uint256 bar_uint)"
            )
        );

    /******************/
    /* Hash Functions */
    /******************/
    function encodeBytes1Array(
        bytes1[] memory arr
    ) public pure returns (bytes32) {
        uint256 len = arr.length;
        bytes32[] memory padded = new bytes32[](len);
        for (uint256 i = 0; i < len; i++) {
            padded[i] = bytes32(arr[i]);
        }
        return keccak256(abi.encodePacked(padded));
    }

    function hashBarStruct(Bar memory bar) public pure returns (bytes32) {
        return keccak256(abi.encode(Bar_TYPEHASH, bar.bar_uint));
    }

    function hashFooStruct(Foo memory foo) public pure returns (bytes32) {
        return
            keccak256(
                abi.encode(
                    Foo_TYPEHASH,
                    keccak256(abi.encodePacked(foo.s)),
                    foo.u_i,
                    foo.s_i,
                    foo.a,
                    foo.b,
                    foo.bytes_30,
                    keccak256(abi.encodePacked(foo.dyn_bytes)),
                    hashBarStruct(foo.bar),
                    encodeBytes1Array(foo.arr)
                )
            );
    }

    function hashBarStructFromParams(
        uint256 bar_uint
    ) public pure returns (bytes32) {
        Bar memory bar;
        bar.bar_uint = bar_uint;
        return hashBarStruct(bar);
    }

    function hashFooStructFromParams(
        string memory s,
        uint256 u_i,
        int8 s_i,
        address a,
        bool b,
        bytes30 bytes_30,
        bytes memory dyn_bytes,
        uint256 bar_uint,
        bytes1[] memory arr
    ) public pure returns (bytes32) {
        // Construct Foo struct with basic types
        Foo memory foo;
        foo.s = s;
        foo.u_i = u_i;
        foo.s_i = s_i;
        foo.a = a;
        foo.b = b;
        foo.bytes_30 = bytes_30;
        foo.dyn_bytes = dyn_bytes;
        foo.arr = arr;

        // Construct Bar struct and add it to Foo
        Bar memory bar;
        bar.bar_uint = bar_uint;
        foo.bar = bar;

        return hashFooStruct(foo);
    }
}
