import re
import html
import pandas as pd

BLOOMS_KEYWORDS = {
    "Remembering": [
        "recall", "recognize", "define", "name", "list", "state", "identify",
        "repeat", "duplicate", "memorize", "retrieve", "label", "match", "cite"
    ],
    "Understanding": [
        "explain", "clarify", "describe", "discuss", "interpret", "paraphrase",
        "summarize", "classify", "compare", "contrast", "illustrate", "translate",
        "differentiate", "comprehend", "mean", "meaning", "concept", "overview"
    ],
    "Applying": [
        "implement", "execute", "run", "calculate", "compute", "solve", "apply",
        "modify", "operate", "convert", "parse", "import", "export", "format",
        "filter", "sort", "read", "write", "iterate", "traverse", "render",
        "serialize", "deserialize", "call", "invoke", "install", "configure",
        "handle", "pass", "return", "print", "plot", "load", "save", "send"
    ],
    "Analyzing": [
        "debug", "troubleshoot", "profile", "benchmark", "diagnose", "trace",
        "inspect", "breakdown", "deconstruct", "investigate", "isolate",
        "bottleneck", "complexity", "leak", "deadlock", "concurrency", "race condition"
    ],
    "Evaluating": [
        "evaluate", "assess", "critique", "judge", "justify", "defend",
        "prioritize", "rate", "recommend", "audit", "trade-off", "tradeoff",
        "pros and cons", "best practice", "security flaw", "vulnerability", "benchmark comparison"
    ],
    "Creating": [
        "architect", "design", "invent", "compose", "synthesize", "formulate",
        "refactor", "re-architect", "scaffold", "rebuild", "redesign", "engineer",
        "framework", "pipeline"
    ]
}

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = html.unescape(text)
    text = re.sub(r"<code>.*?</code>", " ", text, flags=re.DOTALL)
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^\w\s-]", " ", text)
    return text.lower()

def classify_text_with_reason(text):
    cleaned = clean_text(text)
    words = set(re.findall(r"\b[a-z0-9_-]+\b", cleaned))

    detected_keywords = {}
    for level, keywords in BLOOMS_KEYWORDS.items():
        matched = []
        for kw in keywords:
            if " " in kw or "-" in kw:
                if kw in cleaned:
                    matched.append(kw)
            else:
                if kw in words:
                    matched.append(kw)
        if matched:
            detected_keywords[level] = matched

    priority_order = ["Creating", "Evaluating", "Analyzing", "Applying", "Understanding", "Remembering"]
    for level in priority_order:
        if level in detected_keywords:
            return level, f"Matched '{detected_keywords[level][0]}' ({level})"

    return "Applying", "Default: Technical implementation / coding query (no explicit ACM keyword matched)"

def classify_text(text):
    level, _ = classify_text_with_reason(text)
    return level

def classify_questions(questions_df):
    df = questions_df.copy()
    categories = []
    reasons = []

    for _, row in df.iterrows():
        title = str(row.get("title", ""))
        body = str(row.get("body", ""))
        combined_text = f"{title} {title} {body}"
        level, reason = classify_text_with_reason(combined_text)
        categories.append(level)
        reasons.append(reason)

    df["blooms_level"] = categories
    df["classification_reason"] = reasons
    return df

def get_blooms_distribution(classified_df):
    all_levels = ["Remembering", "Understanding", "Applying", "Analyzing", "Evaluating", "Creating"]
    counts = classified_df["blooms_level"].value_counts().to_dict()
    return {level: counts.get(level, 0) for level in all_levels}
