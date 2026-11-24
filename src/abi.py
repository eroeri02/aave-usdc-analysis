"""Hand-written helpers for Ethereum ABI encoding and decoding."""

from Crypto.Hash import keccak

WORD_HEX_CHARS = 64  # one ABI word = 32 bytes = 64 hex characters


def function_selector(signature: str) -> str:
    """First 4 bytes of keccak256(signature), e.g. 'totalSupply()' -> '0x18160ddd'."""
    k = keccak.new(digest_bits=256)
    k.update(signature.encode("ascii"))
    return "0x" + k.hexdigest()[:8]


def encode_address(address: str) -> str:
    """ABI-encode an address argument as one word: 64 hex chars, no '0x' prefix."""
    # Drop the "0x", then left-pad with "0" to WORD_HEX_CHARS characters.
    hex_part = address.removeprefix("0x")
    return hex_part.lower().rjust(WORD_HEX_CHARS, "0")


def split_words(hex_data: str) -> list[str]:
    """Split a raw eth_call result ('0x...') into words of 64 hex chars each."""
    # Drop the "0x", then cut the rest into chunks of WORD_HEX_CHARS.
    hex_part = hex_data.removeprefix("0x")
    words = []
    for i in range(0, len(hex_part), WORD_HEX_CHARS):
        words.append(hex_part[i:i + WORD_HEX_CHARS])
    return words


def decode_uint(word: str) -> int:
    """Read a word as an unsigned integer (uint256)."""
    return int(word, 16)


def decode_address(word: str) -> str:
    """Read a word as an address: its last 20 bytes (40 hex chars), with '0x'."""
    return "0x" + word[-40:]


if __name__ == "__main__":
    print(function_selector("totalSupply()"))
    print(encode_address("0xdAC17F958D2ee523a2206206994597C13D831ec7"))
