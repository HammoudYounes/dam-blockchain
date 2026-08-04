from eth_account import Account
from eth_account.messages import encode_defunct


def phash_to_bytes32(bitstring: str) -> str:
    """
    Convert a pHash bitstring (63 chars of '0'/'1') into a 0x-prefixed,
    32-byte (64 hex char) hex string suitable for bytes32 on-chain storage.

    Left-padded with zeros — same effect as NestJS's boolArrayToBytes32,
    which left-shifts each bit into a BigInt and pads to 64 hex chars.
    """
    as_int = int(bitstring, 2)
    return "0x" + format(as_int, "064x")

def sign_image(phash_bitstring: str, private_key: str) -> dict:
    """
    Sign a perceptual image hash with the service's Ethereum private key.

    Args:
        image_hash: hex string, e.g. "0xabc123..." (32 bytes / bytes32-compatible)
        private_key: the service's Ethereum private key (from PRIVATE_KEY env var)

    Returns:
        dict with the signature split into r, s, v — ready for
        DAMSignature.registerSignature(tokenId, hash, r, s, v, creator)
    """
    image_hash = phash_to_bytes32(phash_bitstring)
    message = encode_defunct(hexstr=image_hash)
    signed = Account.sign_message(message, private_key=private_key)

    return {
        "hash": image_hash,
        "r": hex(signed.r),
        "s": hex(signed.s),
        "v": signed.v,
        "signature": signed.signature.hex(),
    }


