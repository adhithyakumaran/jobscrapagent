import re

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s\-]{8,14}\d")
EXP_RANGE_RE = re.compile(
    r"(\d+)\s*[-–to]+\s*(\d+)\s*years?",
    re.I,
)
EXP_MIN_RE = re.compile(r"(\d+)\s*\+\s*years?", re.I)
FRESHER_RE = re.compile(
    r"\b(fresher|freshers|entry\s*level|graduate|0\s*[-–]?\s*1\s*year|trainee|campus)\b",
    re.I,
)
