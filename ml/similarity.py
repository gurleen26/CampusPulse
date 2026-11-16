"""Similar-complaint detection: TF-IDF vectors + cosine similarity."""
from ml.preprocess import clean_text

# Words that carry no information about WHAT is wrong. Location words are already
# handled by the same-location filter; "not working" is in almost every complaint.
FILLER = {
    "not", "no", "working", "work", "since", "morning", "yesterday", "today", "night",
    "afternoon", "central", "library", "hostel", "block", "academic", "admin",
    "cafeteria", "auditorium", "sports", "complex", "gate", "parking", "area",
    "building", "campus", "room", "floor",
}


def similarity_text(text: str) -> str:
    return " ".join(t for t in clean_text(text).split() if t not in FILLER)


def find_similar(text, candidates, vectorizer, location=None, threshold=0.3, top_k=3):
    """
    text       : the new complaint text (title + description)
    candidates : list of dicts with 'complaint_id', 'text' and optionally 'location'
    location   : campus location of the new complaint. When given, only complaints
                 from the SAME location are compared (the same fault in another
                 building is a different complaint; repeated faults across places are
                 found by the recurring-issue aggregation instead).
    returns    : up to top_k candidates with cosine score >= threshold, best first.
    Possible matches are only *suggested*; complaints are never merged automatically.
    """
    if location:
        candidates = [c for c in candidates if c.get("location") == location]
    if not candidates:
        return []
    cleaned = similarity_text(text)
    if not cleaned:
        return []
    new_vec = vectorizer.transform([cleaned])
    cand_vecs = vectorizer.transform([similarity_text(c["text"]) for c in candidates])
    # TfidfVectorizer output is L2-normalised, so the dot product IS the cosine similarity
    scores = (cand_vecs @ new_vec.T).toarray().ravel()
    ranked = sorted(zip(scores, candidates), key=lambda p: p[0], reverse=True)
    out = []
    for score, cand in ranked[:top_k]:
        if score >= threshold:
            item = dict(cand)
            item["score"] = round(float(score), 3)
            out.append(item)
    return out
