"""
CA2 demo - MongoDB schema validation ($jsonSchema).
Shows the validator stored in the database and what happens when invalid documents are inserted.

    python -m scripts.demo_validation
"""
from pymongo.errors import DuplicateKeyError, WriteError

from database.mongodb import get_db, init_db, utcnow
from scripts._show import as_json, heading, step, show


def why_failed(err):
    """Pull the failed rule out of MongoDB's error (errInfo.details)."""
    info = (err.details or {}).get("errInfo", {}).get("details", {})
    parts = []
    for rule in info.get("schemaRulesNotSatisfied", []):
        if rule.get("operatorName") == "required":
            parts.append("missing required field: " + ", ".join(rule.get("missingProperties", [])))
        for prop in rule.get("propertiesNotSatisfied", []):
            for d in prop.get("details", []):
                parts.append(f"{prop['propertyName']} violates '{d.get('operatorName')}'")
    return "; ".join(parts)


def try_insert(db, collection, doc, why):
    print(f"\n   Trying: {why}")
    try:
        db[collection].insert_one(doc)
        print("   RESULT: inserted (unexpected!)")
        db[collection].delete_one({"_id": doc["_id"]})
    except WriteError as e:
        print(f"   RESULT: REJECTED by MongoDB -> {e.details.get('errmsg')}: {why_failed(e)}")
    except DuplicateKeyError as e:
        print(f"   RESULT: REJECTED by unique index -> {str(e)[:110]}")


def main():
    db = init_db()
    heading("CampusPulse - validation demo")

    step("The validator is stored with the collection", 'db.getCollectionInfos({name:"complaints"})')
    opts = db.command("listCollections", filter={"name": "complaints"})["cursor"]["firstBatch"][0]["options"]
    print("   validationLevel :", opts["validationLevel"], "| validationAction :", opts["validationAction"])
    schema = opts["validator"]["$jsonSchema"]
    print("   required fields :", schema["required"])
    print("   status allowed  :", schema["properties"]["status"]["enum"])
    print("   title length    :", schema["properties"]["title"]["minLength"], "-", schema["properties"]["title"]["maxLength"])

    base = {
        "complaint_id": "CMP9000001", "student_id": "USR9000001", "student_name": "Validation Test",
        "title": "Wi-Fi not working", "description": "Wi-Fi is unavailable in the library", "location": "Central Library",
        "predicted_category": "Network", "predicted_urgency": "Medium", "final_urgency": "Medium", "status": "Pending",
        "status_history": [{"status": "Pending", "updated_at": utcnow()}], "created_at": utcnow(),
    }
    heading("Invalid complaints (all must be rejected)")
    try_insert(db, "complaints", dict(base, status="Done"), 'status = "Done" (not in the allowed list)')
    try_insert(db, "complaints", dict(base, title="abc"), "title shorter than 5 characters")
    try_insert(db, "complaints", dict(base, location="Moon Base"), 'location "Moon Base" is not a campus location')
    try_insert(db, "complaints", dict(base, predicted_category="Food"), 'category "Food" is not allowed')
    try_insert(db, "complaints", dict(base, created_at="2026-11-15"), "created_at is a string instead of a date")
    try_insert(db, "complaints", dict(base, complaint_id="ABC1"), "complaint_id does not match ^CMP[0-9]+$")
    missing = dict(base)
    del missing["description"]
    try_insert(db, "complaints", missing, "required field 'description' is missing")

    heading("Invalid users / feedback / unique indexes")
    user = {"user_id": "USR9000001", "name": "Test", "email": "x@y.co", "password_hash": "h" * 30,
            "role": "student", "created_at": utcnow()}
    try_insert(db, "users", dict(user, email="not-an-email"), "invalid e-mail address")
    try_insert(db, "users", dict(user, role="superuser"), 'role "superuser" is not student/admin')
    try_insert(db, "feedback", {"complaint_id": "CMP1001", "student_id": "USR1001", "rating": 9, "created_at": utcnow()},
               "rating 9 (allowed range is 1-5)")
    admin = db.users.find_one({"role": "admin"})
    try_insert(db, "users", dict(user, user_id="USR9000002", email=admin["email"]), "duplicate e-mail (unique index)")

    heading("A valid complaint is accepted")
    ok = dict(base)
    r = db.complaints.insert_one(ok)
    print("   RESULT: inserted ->", ok["complaint_id"])
    db.complaints.delete_one({"_id": r.inserted_id})
    print("   (demo document removed again)")

    step("Indexes on the complaints collection", "db.complaints.getIndexes()")
    for name, info in db.complaints.index_information().items():
        print(f"    {name:<18} keys={info['key']}  unique={info.get('unique', False)}")


if __name__ == "__main__":
    main()
