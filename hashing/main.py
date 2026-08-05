import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.similarity import router as similarity_router
from api.signing import router as signing_router
from retriever.faiss_retriever import ImageRetriever
from retriever.embedder import ImageEmbedder
from retriever.index import VectorIndex
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up the application...")
    dataset_dir = os.getenv("DATASET_DIR", "data/merged")
    # If not absolute, anchor to /work/app (standard app directory)
    if not os.path.isabs(dataset_dir):
        dataset_dir = os.path.join("/work/app", dataset_dir)
    model_size = os.getenv("MODEL_SIZE", "small")
    print(f"Using dataset directory: {dataset_dir}")
    app.state.retriever = ImageRetriever(
        embedder=ImageEmbedder(model_size=model_size),
        vector_index=VectorIndex(
            index_file=os.path.join(dataset_dir, "index", f"faiss_index_{model_size}.bin"),
            meta_file=os.path.join(dataset_dir, "index", f"faiss_index_{model_size}.json")
        ),
        dataset_dir=dataset_dir
    )
    app.state.retriever.initialize()
    print("Application started successfully.")
    yield
    print("Saving index...")
    app.state.retriever.index.save()
    print("Saved index successfully.")

app = FastAPI(lifespan=lifespan)

app.include_router(similarity_router)
app.include_router(signing_router)

@app.get("/")
def read_root():
    return {"status": "API is running"}