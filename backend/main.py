from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any
import uvicorn
import os

from analysis import load_data, get_dataset_overview, get_dataset_preview, get_dataset_analysis, get_visualization_data
from ai_service import get_insights, ask_question

app = FastAPI(title="NEXORAA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/favicon.svg")
def read_favicon():
    return FileResponse(os.path.join(FRONTEND_DIR, "favicon.svg"))

@app.get("/style.css")
def read_style():
    return FileResponse(os.path.join(FRONTEND_DIR, "style.css"))

@app.get("/app.js")
def read_app():
    return FileResponse(os.path.join(FRONTEND_DIR, "app.js"))

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV and XLSX are supported.")
    
    try:
        contents = await file.read()
        df = load_data(contents, file.filename)
        
        return {
            "filename": file.filename,
            "overview": get_dataset_overview(df),
            "preview": get_dataset_preview(df),
            "analysis": get_dataset_analysis(df),
            "viz": get_visualization_data(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/demo")
async def load_demo_dataset():
    try:
        demo_path = os.path.join(BASE_DIR, "data", "demo_dataset.csv")
        with open(demo_path, "rb") as f:
            contents = f.read()
            
        df = load_data(contents, "demo_dataset.csv")
        
        return {
            "filename": "demo_dataset.csv",
            "overview": get_dataset_overview(df),
            "preview": get_dataset_preview(df),
            "analysis": get_dataset_analysis(df),
            "viz": get_visualization_data(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class InsightsReq(BaseModel):
    summary: Dict[str, Any]

@app.post("/api/insights")
def generate_insights(req: InsightsReq):
    try:
        insights = get_insights(req.summary)
        return {"insights": insights}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class QuestionReq(BaseModel):
    question: str
    summary: Dict[str, Any]

@app.post("/api/ask")
def ask(req: QuestionReq):
    try:
        answer = ask_question(req.question, req.summary)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
