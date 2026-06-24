import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.similarity import router as similarity_router
from retriever.faiss_retriever import ImageRetriever
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up the application...")
    dataset_dir = os.getenv("DATASET_DIR", "data/disc21/")
    model_size = os.getenv("MODEL_SIZE", "small")
    print(f"Using dataset directory: {dataset_dir}")
    app.state.retriever = ImageRetriever(model_size=model_size, dataset_dir=dataset_dir)
    print("Application started successfully.")
    yield
    app.state.retriever.save()

app = FastAPI(lifespan=lifespan)

app.include_router(similarity_router)

@app.get("/")
def read_root():
    return {"status": "API is running"}