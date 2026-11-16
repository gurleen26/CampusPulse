"""Text cleaning used by BOTH training and prediction (they must match)."""
import re

# A deliberately small stop-word list. Negations and scope words such as
# "not", "no", "all", "entire", "only" are KEPT because they change the meaning
# of a complaint ("Wi-Fi is not working", "no water in the entire hostel").
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "am",
    "in", "on", "at", "of", "to", "for", "and", "or", "it", "its", "this", "that",
    "these", "those", "with", "from", "by", "as", "has", "have", "had", "i", "we",
    "my", "our", "me", "us", "you", "your", "please", "kindly", "hello", "hi",
    "sir", "madam", "there", "some", "so", "can", "could", "would", "will", "do",
    "does", "did", "location", "complaint", "request", "regarding",
}


def clean_text(text: str) -> str:
    """lower-case -> normalise wi-fi -> drop symbols/numbers' punctuation -> drop stop-words."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"wi[\s\-]?fi", "wifi", text)
    text = re.sub(r"\b(internet|wlan|broadband)\b", "wifi", text)   # simple synonym merge
    text = re.sub(r"[^a-z0-9\s]", " ", text)       # remove punctuation / symbols
    tokens = [t for t in text.split() if t not in STOPWORDS]
    return " ".join(tokens)


def combine_title_description(title: str, description: str) -> str:
    """The models are trained on one text field, so title + description are joined."""
    return f"{(title or '').strip()}. {(description or '').strip()}".strip(". ")
