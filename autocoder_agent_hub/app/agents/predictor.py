# app/agents/predictor.py
"""
Predictor Agent
- Loads past_questions.json (if present) which should be a list of objects:
  [{"topic_id":"SCI_01_T2", "question_text":"..."} , ...]
- If there are relevant past questions, returns a sample of them.
- Otherwise, asks the LLM to propose likely exam questions.
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict
from app.openai_client import get_openai_client

PAST_Q_PATH = Path(__file__).resolve().parent.parent / "past_questions.json"

def load_past_questions() -> List[Dict]:
    if not PAST_Q_PATH.exists():
        return []
    try:
        with open(PAST_Q_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []

def _sample_top_n(items: List, n: int = 5) -> List:
    # simple deterministic "sample" (first n) — you can randomize if desired
    return items[:n]

def predict_questions(topic_id: str, user_history: Optional[Dict] = None) -> Dict:
    """
    Returns:
      {
        "predicted": [...], 
        "source": "past_papers"|"llm",
        "count": int
      }
    """
    past = load_past_questions()
    # find relevant questions (exact match on topic_id)
    relevant = [p for p in past if str(p.get("topic_id")) == str(topic_id)]

    if len(relevant) > 0:
        selected = _sample_top_n([r.get("question_text", "") for r in relevant], n=5)
        return {"predicted": selected, "source": "past_papers", "count": len(relevant)}

    # No past questions found -> call LLM to suggest likely questions
    try:
        client = get_openai_client()
    except Exception as e:
        # If OpenAI client isn't available, return a helpful fallback
        return {"predicted": [], "source": "none", "count": 0, "error": f"openai init failed: {e}"}

    prompt = f"""You are an exam question predictor.
Given the topic id: {topic_id}, suggest 5 likely exam-style questions a school would ask.
Return them as a numbered list, short and clear."""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You suggest likely school exam questions."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=400,
        temperature=0.3,
    )

    # Extract text (handle attribute or dict style)
    try:
        text = resp.choices[0].message.content
    except Exception:
        # fallback if the object is mapping-like
        text = resp["choices"][0]["message"]["content"]

    # Simple post-process: split lines into items and keep first 5 non-empty lines
    lines = [l.strip("-. \t") for l in text.splitlines() if l.strip()]
    # filter out numbered prefixes like "1. " or "Q1:" etc.
    cleaned = []
    for ln in lines:
        # remove leading numbering like '1.' or '1)'
        cleaned.append(ln.lstrip("0123456789. )\t"))
    cleaned = [c for c in cleaned if c]
    predicted = cleaned[:5] if cleaned else [text]

    return {"predicted": predicted, "source": "llm", "count": len(predicted)}
