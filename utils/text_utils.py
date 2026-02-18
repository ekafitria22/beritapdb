# utils/text_utils.py

import re

def clean_text(s: str) -> str:
    s = re.sub(r"http\S+|www\.\S+", " ", s)
    s = s.lower()
    s = re.sub(r"(.)\1{2,}", r"\1", s)   # huruf berulang
    s = re.sub(r"\s+", " ", s).strip()
    return s

def split_sentences(text: str):
    # sederhana
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]

