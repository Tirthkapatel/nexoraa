import os
import json

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    from google import genai
    from google.genai import types
    has_genai = True
except ImportError:
    has_genai = False

def get_insights(analysis_summary):
    if has_genai and GEMINI_API_KEY:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            prompt = f"""
            You are a strict data analyst AI for the NEXORAA platform.
            Analyze the following dataset summary and provide 3-5 key insights.
            Be concise, professional, and focus on anomalies, trends, or notable statistics.
            Do not include any outside information. Use ONLY the provided dataset summary.
            
            Dataset Summary:
            {json.dumps(analysis_summary, indent=2)}
            """
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            return _fallback_insights(analysis_summary)
    else:
        return _fallback_insights(analysis_summary)

def _fallback_insights(analysis_summary):
    # Deterministic fallback based on pandas stats
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
    if has_genai and GEMINI_API_KEY:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            prompt = f"""
            You are a strict data assistant for the NEXORAA platform.
            You must answer the user's question based STRICTLY and ONLY on the provided Dataset Summary below.
            Do not use any outside knowledge, do not make assumptions, and do not answer general knowledge questions.
            If the answer cannot be determined explicitly from the summary, politely state: "I don't have enough information in the dataset to answer that."
            Keep your answer short, precise, and professional.
            
            Dataset Summary:
            {json.dumps(analysis_summary, indent=2)}
            
            Question: {question}
            """
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            return f"Error communicating with AI service: {str(e)}"
    else:
        return f"AI integration is currently unavailable (no API key). I cannot answer natural language questions, but you can explore the statistics in the Data Quality and Statistical Analysis tabs."
