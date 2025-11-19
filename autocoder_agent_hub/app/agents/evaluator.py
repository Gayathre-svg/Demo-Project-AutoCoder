# app/agents/evaluator.py
import os
from app.openai_client import get_openai_client

def generate_questions(topic):
    prompt = f"Generate 5 short questions (mix of MCQ and short answer) for this topic: {topic['title']}. Provide QIDs and short solutions."
    client = get_openai_client()
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":"You are an exam question generator."},
                  {"role":"user","content":prompt}],
        max_tokens=700,
        temperature=0.3
    )
    return r.choices[0].message.content

def grade_answer(question, student_answer, rubric_hint):
    prompt = f"""
Question: {question}
Model answer / rubric hint: {rubric_hint}
Student answer: {student_answer}
Provide:
- score: integer 0-10
- feedback: 1-2 sentence actionable feedback
Return in JSON like: {{ "score": 7, "feedback": "..." }}
"""
    client = get_openai_client()
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":"You are an objective grader. Return only JSON."},
                  {"role":"user","content":prompt}],
        temperature=0
    )
    return r.choices[0].message.content
