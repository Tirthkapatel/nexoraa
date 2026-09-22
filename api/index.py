import os
import json
import io
import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, Any

# ==========================================
# AI SERVICE
# ==========================================
import random

# Load all available keys from environment variables
API_KEYS = []
for k, v in os.environ.items():
    if k.startswith("GEMINI_API_KEY") and v.strip():
        API_KEYS.append(v.strip())

try:
    from google import genai
    has_genai = True
except ImportError:
    has_genai = False

def _call_gemini(prompt):
    if not has_genai or not API_KEYS:
        raise ValueError("AI integration unavailable (No API keys or library).")
        
    last_err = None
    # Shuffle keys to distribute load
    keys_to_try = list(API_KEYS)
    random.shuffle(keys_to_try)
    
    for key in keys_to_try:
        try:
            client = genai.Client(api_key=key)
            # Try 1.5 flash which has the highest rate limits
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            last_err = e
            if "404" in str(e):
                # If model not found, try alternative model
                try:
                    response = client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=prompt,
                    )
                    return response.text
                except Exception as inner_e:
                    last_err = inner_e
            # If 503 or quota error, try next key
            continue
            
    raise last_err

def get_insights(analysis_summary):
    prompt = f"""
    You are a strict data analyst AI for the NEXORAA platform.
    Analyze the following dataset summary and provide 3-5 key insights.
    Be concise, professional, and focus on anomalies, trends, or notable statistics.
    Do not include any outside information. Use ONLY the provided dataset summary.
    
    Dataset Summary:
    {json.dumps(analysis_summary, indent=2)}
    """
    
    try:
        return _call_gemini(prompt)
    except Exception:
        return _fallback_insights(analysis_summary)

def _fallback_insights(analysis_summary):
    insights = []
    analysis = analysis_summary.get("analysis", {})
    num_cols = analysis.get("numerical", {})
    cat_cols = analysis.get("categorical", {})
    insights.append(f"The dataset contains {len(num_cols)} numerical columns and {len(cat_cols)} categorical columns.")
    if num_cols:
        highest_var_col = None
        highest_var = -1
        for col, stats in num_cols.items():
            if stats["mean"] and stats["std"]:
                cv = stats["std"] / (stats["mean"] + 1e-9)
                if cv > highest_var:
                    highest_var = cv
                    highest_var_col = col
        if highest_var_col:
            insights.append(f"The numerical column '{highest_var_col}' shows the highest relative variance.")
    if cat_cols:
        for col, stats in list(cat_cols.items())[:2]:
            if stats["top_values"]:
                top_val = stats["top_values"][0]
                freq = stats["frequencies"][0]
                insights.append(f"In the '{col}' category, '{top_val}' is the most frequent value (appearing {freq} times).")
    return "\n\n".join(insights)

def ask_question(question, analysis_summary):
    prompt = f"""
    You are NEXORAA, a highly intelligent and professional AI data analyst assistant.
    You must answer the user's question based STRICTLY and ONLY on the provided Dataset Summary below.
    If the user asks who you are, what your name is, or what you can do, introduce yourself proudly as NEXORAA and briefly explain that you are here to analyze their dataset.
    Do not use any outside knowledge for data-related questions, do not make assumptions, and do not answer general knowledge questions.
    If a data-related answer cannot be determined explicitly from the summary, politely state: "I don't have enough information in the dataset to answer that."
    Keep your answer short, precise, and professional.
    
    Dataset Summary:
    {json.dumps(analysis_summary, indent=2)}
    
    Question: {question}
    """
    
    try:
        return _call_gemini(prompt)
    except Exception as e:
        if "503" in str(e) or "quota" in str(e).lower() or "UNAVAILABLE" in str(e):
            return "My AI engines are currently cooling down due to extremely high demand on Google's servers. Please wait a moment and try asking again!"
        return f"Error communicating with AI service: {str(e)}"


# ==========================================
# ANALYSIS SERVICE
# ==========================================
def load_data(file_bytes, filename):
    if filename.endswith('.csv'):
        return pd.read_csv(io.BytesIO(file_bytes))
    elif filename.endswith('.xlsx'):
        return pd.read_excel(io.BytesIO(file_bytes))
    else:
        raise ValueError("Unsupported file format")

def get_dataset_overview(df):
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing_values": df.isnull().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "numerical_columns": num_cols,
        "categorical_columns": cat_cols
    }

def get_dataset_preview(df, max_rows=50):
    df_preview = df.head(max_rows).replace({np.nan: None})
    return df_preview.to_dict(orient="records")

def get_dataset_analysis(df):
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    analysis = {"numerical": {}, "categorical": {}}
    for col in num_cols:
        col_data = df[col].dropna()
        if len(col_data) > 0:
            analysis["numerical"][col] = {
                "count": int(col_data.count()),
                "mean": float(col_data.mean()),
                "median": float(col_data.median()),
                "min": float(col_data.min()),
                "max": float(col_data.max()),
                "std": float(col_data.std()) if len(col_data) > 1 else 0.0
            }
        else:
            analysis["numerical"][col] = {"count": 0, "mean": None, "median": None, "min": None, "max": None, "std": None}
    for col in cat_cols:
        col_data = df[col].dropna()
        if len(col_data) > 0:
            val_counts = col_data.value_counts().head(10)
            analysis["categorical"][col] = {
                "unique_count": int(col_data.nunique()),
                "top_values": val_counts.index.tolist(),
                "frequencies": val_counts.tolist()
            }
        else:
            analysis["categorical"][col] = {"unique_count": 0, "top_values": [], "frequencies": []}
    return analysis

def get_visualization_data(df):
    viz_data = {}
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    if cat_cols:
        best_cat = min(cat_cols, key=lambda c: df[c].nunique() if df[c].nunique() > 1 else 9999)
        if df[best_cat].nunique() <= 20:
            vc = df[best_cat].value_counts()
            viz_data["bar"] = {
                "x": vc.index.tolist(),
                "y": vc.tolist(),
                "title": f"Distribution of {best_cat}",
                "type": "bar",
                "col": best_cat
            }
    if num_cols:
        best_num = num_cols[0]
        hist_data = df[best_num].dropna().tolist()
        if len(hist_data) > 1000:
            hist_data = pd.Series(hist_data).sample(1000).tolist()
        viz_data["histogram"] = {
            "x": hist_data,
            "title": f"Distribution of {best_num}",
            "type": "histogram",
            "col": best_num
        }
    if len(num_cols) >= 2:
        df_scatter = df.dropna(subset=[num_cols[0], num_cols[1]])
        if len(df_scatter) > 1000:
            df_scatter = df_scatter.sample(1000)
        viz_data["scatter"] = {
            "x": df_scatter[num_cols[0]].tolist(),
            "y": df_scatter[num_cols[1]].tolist(),
            "title": f"{num_cols[1]} vs {num_cols[0]}",
            "type": "scatter",
            "x_col": num_cols[0],
            "y_col": num_cols[1]
        }
    viz_data["meta"] = {"numerical": num_cols, "categorical": cat_cols}
    return viz_data


# ==========================================
# FASTAPI APP
# ==========================================
app = FastAPI(title="NEXORAA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "public")

IS_VERCEL = os.environ.get("VERCEL") == "1"

if not IS_VERCEL:
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

    @app.get("/demo_dataset.csv")
    def read_demo():
        return FileResponse(os.path.join(FRONTEND_DIR, "demo_dataset.csv"))

@app.get("/api/health")
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
    import uvicorn
    uvicorn.run("index:app", host="0.0.0.0", port=8000, reload=True)
