# app/openai_client.py
from openai import OpenAI
import os

def get_openai_client():
    """
    Returns an initialized OpenAI client instance.
    Uses OPENAI_API_KEY from the environment.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in environment")
    return OpenAI(api_key=api_key)
