from eth_account import Account
from eth_account.messages import encode_defunct

from signer import phash_to_bytes32


def verify_ownership(image_hash_or_bitstring: str, signature: str, expected_address: str) -> bool:
    """
    Verify that a signature over a given pHash was produced by the expected address.

    Accepts the hash in either form:
      - a raw pHash bitstring (63 chars of '0'/'1'), as freshly computed from an image
      - an already-converted bytes32 hex string (e.g. pulled from DAMSignature.getAssetSignature)

    Args:
        image_hash_or_bitstring: either format above
        signature: the full 65-byte signature hex string
        expected_address: the Ethereum address to check the signature against

    Returns:
        True if the signature was produced by expected_address, False otherwise
    """
    if image_hash_or_bitstring.startswith("0x"):
        image_hash = image_hash_or_bitstring
    else:
        image_hash = phash_to_bytes32(image_hash_or_bitstring)

    message = encode_defunct(hexstr=image_hash)
    recovered_address = Account.recover_message(message, signature=signature)
    return recovered_address.lower() == expected_address.lower()