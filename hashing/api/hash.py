from fastapi import APIRouter, File, UploadFile, HTTPException, status
from algorithms.phash import PerceptualHash

router = APIRouter()
PHASHER = PerceptualHash()
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp", "image/bmp"}

@router.post("/phash")
async def compute_phash(newFile: UploadFile = File(...)):
    if newFile.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type.")
    contents = await newFile.read()
    phash_bin = PHASHER.compute(contents)
    
    # Convert binary string to hex
    phash_int = int(phash_bin, 2)
    phash_hex = hex(phash_int)
    
    return {"status": "success", "data": {"phash": phash_hex}}
