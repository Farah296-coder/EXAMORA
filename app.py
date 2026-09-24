import os
import runpy
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

for folder in ["output", os.path.join("data", "uploads"), "vector_db"]:
    os.makedirs(os.path.join(BASE_DIR, folder), exist_ok=True)

import streamlit as st

for secret_key in ["GROQ_API_KEY", "GROQ_MODEL"]:
    if os.environ.get(secret_key):
        continue
    try:
        value = st.secrets[secret_key]
    except Exception:
        continue
    if value:
        os.environ[secret_key] = str(value)

from api_server import ensure_api_running

os.environ["EXAMORA_API_URL"] = ensure_api_running()

runpy.run_path(os.path.join(SRC_DIR, "examora_chat.py"), run_name="__main__")
