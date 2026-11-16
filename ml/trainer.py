"""
Shared training / evaluation code for the category and the urgency classifier.

Pipeline: clean text -> TF-IDF (1-2 grams) -> Logistic Regression.
Steps: dedupe -> stratified 80/20 split -> fit on train -> evaluate on held-out
test set -> also evaluate on a hand-written manual test set -> compare with
baselines -> refit on ALL data -> save model + vectorizer with joblib.
"""
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB

from ml.preprocess import clean_text

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "data" / "raw" / "complaints.csv"
MANUAL_TEST = ROOT / "data" / "raw" / "manual_test.csv"
MODELS_DIR = ROOT / "models"


def _vectorizer():
    return TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)


def _classifier():
    return LogisticRegression(max_iter=2000, C=5.0, class_weight="balanced")


def load_dataset():
    if not DATASET.exists():
        from data.generate_dataset import generate
        generate()
    df = pd.read_csv(DATASET)
    df["clean"] = df["complaint_text"].map(clean_text)
    before = len(df)
    df = df[df["clean"].str.len() > 0].drop_duplicates(subset="clean").reset_index(drop=True)
    return df, before - len(df)


def train_target(target: str, labels: list, name: str, verbose: bool = True):
    """target = 'category' or 'urgency'; name = file prefix for the saved model."""
    df, removed = load_dataset()
    X, y = df["clean"], df[target]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    vec = _vectorizer().fit(X_tr)
    clf = _classifier().fit(vec.transform(X_tr), y_tr)
    pred = clf.predict(vec.transform(X_te))

    metrics = {
        "target": target,
        "rows_used": int(len(df)),
        "duplicates_removed": int(removed),
        "train_size": int(len(X_tr)),
        "test_size": int(len(X_te)),
        "class_counts": y.value_counts().to_dict(),
        "accuracy": round(accuracy_score(y_te, pred), 4),
        "macro_f1": round(f1_score(y_te, pred, average="macro"), 4),
        "report": classification_report(y_te, pred, labels=labels, output_dict=True, zero_division=0),
        "confusion_matrix": {"labels": labels,
                             "matrix": confusion_matrix(y_te, pred, labels=labels).tolist()},
    }

    # --- baselines -----------------------------------------------------
    base = {}
    dummy = DummyClassifier(strategy="most_frequent").fit(vec.transform(X_tr), y_tr)
    base["most_frequent"] = round(f1_score(y_te, dummy.predict(vec.transform(X_te)), average="macro"), 4)
    nb = MultinomialNB().fit(vec.transform(X_tr), y_tr)
    base["naive_bayes"] = round(f1_score(y_te, nb.predict(vec.transform(X_te)), average="macro"), 4)
    base["logistic_regression"] = metrics["macro_f1"]
    metrics["baseline_macro_f1"] = base

    # --- hand-written, unseen complaints (the honest generalisation check) ---
    if MANUAL_TEST.exists():
        man = pd.read_csv(MANUAL_TEST)
        mp = clf.predict(vec.transform(man["complaint_text"].map(clean_text)))
        metrics["manual_test"] = {
            "size": int(len(man)),
            "accuracy": round(accuracy_score(man[target], mp), 4),
            "macro_f1": round(f1_score(man[target], mp, average="macro"), 4),
            "wrong_examples": [
                {"text": t, "true": a, "predicted": b}
                for t, a, b in zip(man["complaint_text"], man[target], mp) if a != b
            ],
        }
        if target == "urgency":
            high = man[target] == "High"
            hits = sum(1 for a, b in zip(man[target][high], mp[high.values]) if a == b)
            metrics["manual_test"]["high_recall"] = round(hits / max(int(high.sum()), 1), 4)

    # --- refit on all data and save -----------------------------------------
    vec_all = _vectorizer().fit(X)
    clf_all = _classifier().fit(vec_all.transform(X), y)
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(clf_all, MODELS_DIR / f"{name}_model.pkl")
    joblib.dump(vec_all, MODELS_DIR / f"{name}_vectorizer.pkl")
    with open(MODELS_DIR / f"{name}_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    if verbose:
        print_report(metrics, labels)
    return metrics


def print_report(m, labels):
    print("=" * 66)
    print(f"{m['target'].upper()} CLASSIFIER  (TF-IDF + Logistic Regression)")
    print("=" * 66)
    print(f"rows used: {m['rows_used']}  (duplicates removed: {m['duplicates_removed']})")
    print(f"train/test: {m['train_size']}/{m['test_size']}")
    print(f"held-out test  accuracy={m['accuracy']}  macro-F1={m['macro_f1']}")
    print(f"{'class':<22}{'precision':>10}{'recall':>10}{'f1':>10}{'support':>9}")
    for lab in labels:
        r = m["report"].get(lab)
        if r:
            print(f"{lab:<22}{r['precision']:>10.3f}{r['recall']:>10.3f}{r['f1-score']:>10.3f}{int(r['support']):>9}")
    print("confusion matrix (rows=true, cols=predicted):")
    print("   " + " | ".join(l[:8] for l in m["confusion_matrix"]["labels"]))
    for lab, row in zip(m["confusion_matrix"]["labels"], m["confusion_matrix"]["matrix"]):
        print(f"{lab[:10]:<11}", row)
    print("baselines (macro-F1):", m["baseline_macro_f1"])
    if "manual_test" in m:
        mt = m["manual_test"]
        extra = f"  High-recall={mt['high_recall']}" if "high_recall" in mt else ""
        print(f"manual test ({mt['size']} unseen hand-written complaints): "
              f"accuracy={mt['accuracy']}  macro-F1={mt['macro_f1']}{extra}")
        for w in mt["wrong_examples"][:8]:
            print(f"   MISS: {w['text'][:70]!r} true={w['true']} predicted={w['predicted']}")
    print()
