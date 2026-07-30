import io
import os
import uuid
import joblib
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from retriever.faiss_retriever import ImageRetriever
from utils.hash_utils import compute_features, compute_similarities

router = APIRouter()

# Load model
MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "model" / "copymint_logreg.joblib"
MODEL = joblib.load(MODEL_PATH)
FEATURES_ORDER = ["ahash_dist", "phash_dist", "dhash_dist", "hsvhash_dist", "rhash_dist", "chash_dist", "cosine_similarity"]

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp", "image/bmp"}
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))  # 10 MB

def validate_image_bytes(image_bytes: bytes) -> str:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()
            return img.format.lower() if img.format else "jpg"
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a valid image.")

def get_retriever(request: Request) -> ImageRetriever:
    retriever = getattr(request.app.state, "retriever", None)
    if retriever is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image retriever service is not ready.",
        )
    return retriever

@router.post("/similarity")
async def compute_similarity(
    newFile: UploadFile = File(...),
    k: int = 5,
    retriever: ImageRetriever = Depends(get_retriever),
):
    """
    Endpoint to compute similarity between the uploaded image and images in the dataset.
    """
    if newFile.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type.")

    contents = await newFile.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the maximum allowed upload size of {MAX_UPLOAD_SIZE} bytes.",
        )

    validate_image_bytes(contents)

    # Offload the heavy synchronous FAISS task to a threadpool
    similar_images = await run_in_threadpool(retriever.get_similar_images_from_bytes, contents, k)

    results_with_scores = []

    for image_name, distance in similar_images:
        target_image_path = retriever.get_image_by_name(image_name)
        with open(target_image_path, "rb") as f:
            target_image_bytes = f.read()

        computed_features = await run_in_threadpool(compute_features, contents, target_image_bytes)
        hash_similarities = await run_in_threadpool(compute_similarities, contents, target_image_bytes)
        computed_features["cosine_similarity"] = await run_in_threadpool(retriever.cosine_similarity, contents, target_image_bytes)
        
        # Prepare for model
        features_ordered = [computed_features[f] for f in FEATURES_ORDER]
        prob = MODEL.predict_proba([features_ordered])[0, 1]

        results_with_scores.append({
            "image_name": image_name,
            "id": retriever.get_id_by_name(image_name),
            "distance": distance,
            "duplicateProbability": float(prob),
            "computedFeatures": computed_features,
            "hashSimilarities": hash_similarities
        })

    return {"status": "success", "data": {"similar_images": results_with_scores}}


@router.post("/image")
async def upload_image(
    newFile: UploadFile = File(...),
    retriever: ImageRetriever = Depends(get_retriever),
):
    """
    Endpoint to upload an image and add it to the index
    """
    if newFile.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type.")

    contents = await newFile.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the maximum allowed upload size of {MAX_UPLOAD_SIZE} bytes.",
        )

    image_format = validate_image_bytes(contents)

    app_root = Path(__file__).resolve().parents[1]
    dest_dir = app_root / "data" / "new"
    dest_dir.mkdir(parents=True, exist_ok=True)

    original_filename = Path(newFile.filename).name
    if not original_filename:
        original_filename = f"upload.{image_format.lower()}"

    stem = Path(original_filename).stem
    suffix = Path(original_filename).suffix or f".{image_format.lower()}"
    dest_path = dest_dir / original_filename

    if dest_path.exists():
        unique_id = uuid.uuid4().hex[:8]
        dest_path = dest_dir / f"{stem}_{unique_id}{suffix}"

    # Persist the uploaded file copy
    dest_path.write_bytes(contents)

    # Offload the heavy synchronous indexing task to a threadpool using in-memory bytes
    result = await run_in_threadpool(retriever.index_image_from_bytes, contents, dest_path.name)

    if result.get("success"):
        return {
            "status": "success",
            "data": {
                "message": "Image uploaded and added to index.",
                "imageId": result["image_id"]
            }
        }
    
    # If indexing fails, raise a 500 server error
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("error", "Unknown error"))


@router.delete("/image")
async def delete_image(imageId: int, retriever: ImageRetriever = Depends(get_retriever)):
    """
    Endpoint to delete an image from the index
    """
    # Assuming remove_image is also a synchronous blocking operation
    success = await run_in_threadpool(retriever.remove_image, imageId)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Image with ID {imageId} not found.")

    return {
        "status": "success",
        "data": {
            "message": f"Image with ID {imageId} deleted successfully."
        }
    }


@router.get("/image")
async def get_image(imageId: int, retriever: ImageRetriever = Depends(get_retriever)):
    """
    Endpoint to retrieve an image by its ID
    """
    image_bytes = await run_in_threadpool(retriever.get_image_by_id, imageId)

    if image_bytes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Image with ID {imageId} not found.")

    return Response(content=image_bytes, media_type="image/jpeg")
