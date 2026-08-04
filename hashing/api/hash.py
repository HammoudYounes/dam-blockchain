from fastapi import APIRouter, UploadFile, File
from algorithms.phash import PerceptualHash
import io
from PIL import Image

router = APIRouter()
hasher = PerceptualHash()

@router.post("/hash")
async def get_hash(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    phash_str = hasher.compute(image)
    # Convert bitstring to hex as bytes32 for chain
    phash_int = int(phash_str, 2)
    phash_hex = hex(phash_int)
    return {"phash_hex": phash_hex}
