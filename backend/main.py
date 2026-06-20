from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import io
import json
from typing import Optional

from backend.sieve_engine import SieveEngine
from backend.synthetic_data import generate_synthetic_rag_dataset

app = FastAPI(title="DataSieve AI API", description="Automated Data Sanitization & Pattern Discovery Engine API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global engine variable, loaded lazily at startup
engine: Optional[SieveEngine] = None

@app.on_event("startup")
def startup_event():
    global engine
    # Initialize the model on startup so it's ready when requests come in
    try:
        engine = SieveEngine()
    except Exception as e:
        print(f"Error loading SieveEngine: {e}")

class SiftRequest(BaseModel):
    texts: list[str]
    n_clusters: int = 5
    outlier_percentile: float = 90.0

@app.get("/api/status")
def get_status():
    global engine
    if engine is None:
        return {"status": "loading", "message": "ML model is initializing"}
    return {"status": "ready", "message": "ML model loaded and ready"}

@app.get("/api/generate_synthetic")
def get_synthetic_data():
    try:
        data = generate_synthetic_rag_dataset()
        return {"texts": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sift")
def sift_data(request: SiftRequest):
    global engine
    if engine is None:
        raise HTTPException(status_code=503, detail="Model is still loading, please try again in a few seconds.")
    
    if not request.texts:
        raise HTTPException(status_code=400, detail="Text list cannot be empty")
        
    try:
        results = engine.cluster_and_sift(
            texts=request.texts,
            n_clusters=request.n_clusters,
            outlier_percentile=request.outlier_percentile
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sifting data: {str(e)}")

@app.post("/api/upload")
def upload_csv_and_sift(
    file: UploadFile = File(...),
    n_clusters: int = Form(5),
    outlier_percentile: float = Form(90.0),
    column_name: Optional[str] = Form(None)
):
    global engine
    if engine is None:
        raise HTTPException(status_code=503, detail="Model is still loading, please try again in a few seconds.")

    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        if df.empty:
            raise HTTPException(status_code=400, detail="CSV file is empty")
            
        # Detect text column if not specified
        if not column_name:
            # Pick the first text-like column
            text_cols = [col for col in df.columns if df[col].dtype == 'object']
            if not text_cols:
                raise HTTPException(status_code=400, detail="No text columns found in CSV. Please ensure you have a text column.")
            column_name = text_cols[0]
            
        if column_name not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{column_name}' not found in CSV")
            
        # Filter out nulls/empty rows
        texts = df[column_name].dropna().astype(str).tolist()
        
        if not texts:
            raise HTTPException(status_code=400, detail=f"No valid text records found in column '{column_name}'")
            
        results = engine.cluster_and_sift(
            texts=texts,
            n_clusters=n_clusters,
            outlier_percentile=outlier_percentile
        )
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV processing failed: {str(e)}")
