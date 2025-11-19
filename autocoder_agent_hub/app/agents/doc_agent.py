# app/agents/doc_agent.py
import re, json
from app.openai_client import get_openai_client

def generate_docs(feature_spec: str, code_summary: str):
    prompt = f"""
You are a technical writer. Given the feature spec and the code summary, produce:
- A short README section describing the new feature (2-4 paragraphs).
- A usage example (code snippet).
Return JSON: {{ "readme_md": "...", "usage_example": "..." }}
"""
    client = get_openai_client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":"You produce precise README sections."},
                  {"role":"user","content":prompt}],
        max_tokens=400,
        temperature=0.2
    )
    text = resp.choices[0].message.content
    m = re.search(r"(\{[\s\S]*\})", text)
    if not m:
        return {"readme_md": f"Feature: {feature_spec}", "usage_example": ""}
    return json.loads(m.group(1))
