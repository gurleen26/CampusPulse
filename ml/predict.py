"""Loads the saved models and predicts category + urgency for new complaint text."""
import threading
from pathlib import Path

import joblib

from ml.preprocess import clean_text

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
_FILES = ["category_model.pkl", "category_vectorizer.pkl", "urgency_model.pkl", "urgency_vectorizer.pkl"]
_lock = threading.Lock()
_cache = {}


def models_exist() -> bool:
    return all((MODELS_DIR / f).exists() for f in _FILES)


def ensure_models():
    """Train the models automatically the first time the app starts."""
    if models_exist():
        return
    print("[ML] Trained models not found - training them now (takes a few seconds)...")
    from ml import train_category, train_urgency
    train_category.train(verbose=False)
    train_urgency.train(verbose=False)
    print("[ML] Training finished.")


def _load():
    with _lock:
        if not _cache:
            ensure_models()
            _cache["cat_model"] = joblib.load(MODELS_DIR / "category_model.pkl")
            _cache["cat_vec"] = joblib.load(MODELS_DIR / "category_vectorizer.pkl")
            _cache["urg_model"] = joblib.load(MODELS_DIR / "urgency_model.pkl")
            _cache["urg_vec"] = joblib.load(MODELS_DIR / "urgency_vectorizer.pkl")
    return _cache


def reset_cache():
    with _lock:
        _cache.clear()


def get_similarity_vectorizer():
    """The category TF-IDF vectoriser is reused for similarity search."""
    return _load()["cat_vec"]


def predict(text: str) -> dict:
    m = _load()
    cleaned = clean_text(text)
    cat_probs = m["cat_model"].predict_proba(m["cat_vec"].transform([cleaned]))[0]
    urg_probs = m["urg_model"].predict_proba(m["urg_vec"].transform([cleaned]))[0]
    ci, ui = int(cat_probs.argmax()), int(urg_probs.argmax())
    return {
        "category": str(m["cat_model"].classes_[ci]),
        "category_confidence": round(float(cat_probs[ci]), 3),
        "urgency": str(m["urg_model"].classes_[ui]),
        "urgency_confidence": round(float(urg_probs[ui]), 3),
    }
