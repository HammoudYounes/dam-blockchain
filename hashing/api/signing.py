"""
API endpoints for perceptual hashing, cryptographic signing, and ownership
verification. Wires signer.py / verifier.py into HTTP so the NestJS
SignatureModule can call them during the mint and verification flows.

Endpoints:
    POST /hash             -> compute the pHash for an uploaded image
    POST /sign              -> compute the pHash and sign it with the
                                service's trusted-signer key (BD.5)
    POST /verify-ownership  -> recompute the pHash for a submitted image
                                and check a stored signature against it
"""
import os
from PIL import Image, UnidentifiedImageError
import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from utils.hash_utils import get_hash
from signer import sign_image, phash_to_bytes32
from verifier import verify_ownership

router = APIRouter()

# Same validation constants used in api/similarity.py — kept consistent
# across every upload-accepting endpoint in this service.
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp", "image/bmp"}
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))  # 10 MB


def validate_image_bytes(image_bytes: bytes) -> None:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image.",
        )


async def read_and_validate_upload(file: UploadFile) -> bytes:
    """Shared upload handling: content-type check, size check, image validity check."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type.")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the maximum allowed upload size of {MAX_UPLOAD_SIZE} bytes.",
        )

    validate_image_bytes(contents)
    return contents


def get_private_key() -> str:
    """
    Load the service's trusted-signer private key from the environment.
    This is the DAM backend's own key (BD.5 — service-key model), never a
    user's wallet key. Raising 503 rather than crashing the process lets
    the rest of the service (similarity/retrieval) keep working even if
    signing is temporarily misconfigured.
    """
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Signing is not configured: PRIVATE_KEY is not set.",
        )
    return private_key


class HashResponse(BaseModel):
    phash_bitstring: str
    phash_bytes32: str


class SignResponse(BaseModel):
    hash: str        # bytes32 hex — matches DAMSignature.registerSignature's `hash` arg
    r: str
    s: str
    v: int
    signature: str    # full 65-byte signature hex, for reference/logging


class VerifyOwnershipResponse(BaseModel):
    valid: bool


@router.post("/hash", response_model=HashResponse)
async def hash_image(file: UploadFile = File(...)):
    """
    Compute the pHash for an uploaded image.
    Returns both the raw 63-bit bitstring (for debugging/logging) and the
    bytes32 hex form (what DAMSignature.registerSignature actually stores).
    """
    contents = await read_and_validate_upload(file)
    bitstring = get_hash("phash", contents)
    return HashResponse(
        phash_bitstring=bitstring,
        phash_bytes32=phash_to_bytes32(bitstring),
    )


@router.post("/sign", response_model=SignResponse)
async def sign(file: UploadFile = File(...)):
    """
    Compute the pHash for an uploaded image and sign it with the service's
    trusted-signer key. This signature attests that the DAM backend's
    hashing pipeline produced this exact hash for this image — it is NOT
    a personal signature from the uploading creator's wallet (see BD.5).

    NestJS NftModule calls this once per mint, then passes the returned
    r/s/v straight into DAMSignature.registerSignature(tokenId, hash, r, s, v, creator).
    """
    contents = await read_and_validate_upload(file)
    bitstring = get_hash("phash", contents)
    private_key = get_private_key()

    result = sign_image(bitstring, private_key)
    return SignResponse(**result)


@router.post("/verify-ownership", response_model=VerifyOwnershipResponse)
async def verify_ownership_endpoint(
    file: UploadFile = File(...),
    signature: str = Form(...),
    expected_address: str = Form(...),
):
    contents = await read_and_validate_upload(file)
    bitstring = get_hash("phash", contents)

    try:
        is_valid = verify_ownership(bitstring, signature, expected_address)
    except Exception:
        # Malformed signature/address input — not a server fault, a bad request.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to verify: malformed signature or address.",
        )

    return VerifyOwnershipResponse(valid=is_valid)