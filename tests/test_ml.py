import json

from ml.predict import MODELS_DIR, get_similarity_vectorizer, predict
from ml.preprocess import clean_text
from ml.similarity import find_similar


def test_clean_text_keeps_negations_and_normalises_wifi():
    out = clean_text("The Wi-Fi is NOT working in the library!!")
    assert out == "wifi not working library"


def test_category_predictions_on_obvious_complaints():
    assert predict("Wi-Fi is not working in the library")["category"] == "Network"
    assert predict("Water supply has stopped in the hostel")["category"] == "Water Supply"
    assert predict("Projector is not working in room 204")["category"] == "Classroom Equipment"
    assert predict("Dustbins are overflowing near the cafeteria")["category"] == "Cleanliness"


def test_urgency_is_valid_and_confidence_in_range():
    p = predict("Sparks are coming out of the switch board in the hostel")
    assert p["urgency"] in {"Low", "Medium", "High"}
    assert 0 <= p["urgency_confidence"] <= 1 and 0 <= p["category_confidence"] <= 1


def test_widespread_outage_is_more_urgent_than_dustbin():
    order = {"Low": 0, "Medium": 1, "High": 2}
    big = predict("Wi-Fi is unavailable throughout the campus, nobody can access it")
    small = predict("A classroom dustbin is full")
    assert order[big["urgency"]] > order[small["urgency"]]


def test_similarity_finds_related_complaints_at_same_location_only():
    loc = "Central Library"
    existing = [
        {"complaint_id": "A", "text": "Wi-Fi not working in library.", "location": loc},
        {"complaint_id": "B", "text": "Unable to connect to library internet.", "location": loc},
        {"complaint_id": "C", "text": "Dustbin overflowing outside the central library", "location": loc},
        {"complaint_id": "D", "text": "Wi-Fi not working in Hostel Block A", "location": "Hostel Block A"},
    ]
    hits = find_similar("Cannot connect to internet in the library", existing, get_similarity_vectorizer(),
                        location=loc, threshold=0.25)
    ids = [h["complaint_id"] for h in hits]
    assert "B" in ids and "A" in ids
    assert "C" not in ids and "D" not in ids


def test_saved_metrics_meet_minimum_quality():
    cat = json.load(open(MODELS_DIR / "category_metrics.json"))
    urg = json.load(open(MODELS_DIR / "urgency_metrics.json"))
    assert cat["manual_test"]["accuracy"] >= 0.85
    assert urg["manual_test"]["accuracy"] >= 0.70
    assert urg["macro_f1"] > urg["baseline_macro_f1"]["most_frequent"]
