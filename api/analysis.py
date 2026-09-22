import pandas as pd
import numpy as np
import io

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
    # Handle NaN values to avoid JSON serialization errors
    df_preview = df.head(max_rows).replace({np.nan: None})
    return df_preview.to_dict(orient="records")

def get_dataset_analysis(df):
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    
    analysis = {
        "numerical": {},
        "categorical": {}
    }
    
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
    # Prepare aggregated data for charts to avoid sending huge arrays to frontend
    viz_data = {}
    
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    
    # 1. Distribution of top categorical column (Bar chart)
    if cat_cols:
        # Pick categorical with fewest unique > 1
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
            
    # 2. Histogram of first numerical column
    if num_cols:
        best_num = num_cols[0]
        hist_data = df[best_num].dropna().tolist()
        # Subsample if too large
        if len(hist_data) > 1000:
            hist_data = pd.Series(hist_data).sample(1000).tolist()
        viz_data["histogram"] = {
            "x": hist_data,
            "title": f"Distribution of {best_num}",
            "type": "histogram",
            "col": best_num
        }
        
    # 3. Scatter plot of first two numerical columns
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
        
    # Also just send raw numeric / categorical column names so the frontend can build dynamic charts
    viz_data["meta"] = {
        "numerical": num_cols,
        "categorical": cat_cols
    }
    
    return viz_data
