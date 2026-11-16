"""
CA2 demo - CRUD operations with PyMongo on the CampusPulse database.
Creates a few DEMO complaints, reads/updates them, then deletes them again (your other data is untouched).

    python -m scripts.demo_crud
"""
from datetime import timedelta

from werkzeug.security import generate_password_hash

from database import repository as repo
from database.mongodb import get_db, init_db, next_id, utcnow
from scripts._show import heading, show, step

PRED = {"category": "Network", "category_confidence": 0.93, "urgency": "Medium", "urgency_confidence": 0.81}


def demo_doc(student, title, desc, location, category, urgency, hours_ago=1):
    now = utcnow() - timedelta(hours=hours_ago)
    return {
        "complaint_id": next_id("CMP", "complaints"), "student_id": student["user_id"],
        "student_name": student["name"], "title": title, "description": desc, "location": location,
        "predicted_category": category, "category_confidence": 0.9, "predicted_urgency": urgency,
        "urgency_confidence": 0.8, "final_urgency": urgency, "urgency_overridden": False,
        "status": "Pending", "assigned_department": None, "image_filename": None, "similar_complaints": [],
        "status_history": [{"status": "Pending", "updated_at": now, "updated_by": student["user_id"]}],
        "created_at": now, "updated_at": now, "resolved_at": None,
    }


def main():
    db = init_db()
    heading("CampusPulse - CRUD demo (PyMongo)")
    student = repo.find_user_by_email("demo.crud@example.com") or repo.create_user(
        "Demo CRUD Student", "demo.crud@example.com", generate_password_hash("Student@123"))

    # ------------------------------------------------------------------ CREATE
    heading("1. CREATE")
    step("insert_one - one complaint (with the ML prediction)",
         'db.complaints.insertOne({complaint_id:"CMP...", title:"DEMO: Wi-Fi not working", ...})')
    one = repo.create_complaint(student, "DEMO: Wi-Fi not working", "Wi-Fi is unavailable in the central library",
                                "Central Library", PRED, [])
    show({"inserted": one["complaint_id"], "status": one["status"], "category": one["predicted_category"]})

    step("insert_many - three more complaints in one call",
         "db.complaints.insertMany([ {...}, {...}, {...} ])")
    docs = [
        demo_doc(student, "DEMO: Projector not working", "Projector in room 204 shows no display", "Academic Block 1",
                 "Classroom Equipment", "Medium", 5),
        demo_doc(student, "DEMO: Dustbin overflowing", "Dustbins near cafeteria are overflowing", "Cafeteria",
                 "Cleanliness", "Low", 30),
        demo_doc(student, "DEMO: No water in hostel", "No water supply in the entire hostel since morning",
                 "Hostel Block A", "Water Supply", "High", 3),
    ]
    res = db.complaints.insert_many(docs)
    show({"inserted_count": len(res.inserted_ids), "ids": [d["complaint_id"] for d in docs]})

    # -------------------------------------------------------------------- READ
    heading("2. READ")
    cid = one["complaint_id"]
    step("find_one - by complaint_id (unique index)", f'db.complaints.findOne({{complaint_id:"{cid}"}})')
    d = db.complaints.find_one({"complaint_id": cid}, {"_id": 0, "status_history": 0})
    show(d)

    step("find - filter + projection + sort + limit",
         'db.complaints.find({status:"Pending", final_urgency:"High"}, {complaint_id:1,title:1,location:1,_id:0}).sort({created_at:-1}).limit(5)')
    show(list(db.complaints.find({"status": "Pending", "final_urgency": "High"},
                                 {"_id": 0, "complaint_id": 1, "title": 1, "location": 1})
              .sort("created_at", -1).limit(5)))

    step("comparison + logical operators ($in, $gte, $or)",
         'db.complaints.find({$or:[{final_urgency:"High"},{predicted_category:{$in:["Security","Electricity"]}}], created_at:{$gte: ISODate(<7 days ago>)}})')
    week = utcnow() - timedelta(days=7)
    n = db.complaints.count_documents({"$or": [{"final_urgency": "High"},
                                               {"predicted_category": {"$in": ["Security", "Electricity"]}}],
                                       "created_at": {"$gte": week}})
    show({"matching_documents": n})

    step("regex search on title", 'db.complaints.find({title:{$regex:"^DEMO", $options:"i"}}).count()')
    show({"count": db.complaints.count_documents({"title": {"$regex": "^DEMO", "$options": "i"}})})

    step("$text search (uses the text index on title + description)", 'db.complaints.find({$text:{$search:"wifi library"}})')
    show([{"complaint_id": r["complaint_id"], "title": r["title"]}
          for r in db.complaints.find({"$text": {"$search": "wifi library"}}).limit(4)])

    step("count_documents and distinct", 'db.complaints.countDocuments({status:"Pending"}) ; db.complaints.distinct("location")')
    show({"pending": db.complaints.count_documents({"status": "Pending"}),
          "locations_used": db.complaints.distinct("location")})

    step("query inside an embedded array ($elemMatch on status_history)",
         'db.complaints.find({status_history:{$elemMatch:{status:"Pending"}}}).count()')
    show({"count": db.complaints.count_documents({"status_history": {"$elemMatch": {"status": "Pending"}}})})

    # ------------------------------------------------------------------ UPDATE
    heading("3. UPDATE")
    step("update_one - $set the department and $push a status-history entry",
         f'db.complaints.updateOne({{complaint_id:"{cid}"}}, {{$set:{{status:"In Progress", assigned_department:"IT Department"}}, $push:{{status_history:{{...}}}}}})')
    db.complaints.update_one({"complaint_id": cid}, {
        "$set": {"status": "In Progress", "assigned_department": "IT Department", "updated_at": utcnow()},
        "$push": {"status_history": {"status": "In Progress", "updated_at": utcnow(), "updated_by": "USR1001",
                                     "note": "Assigned to IT"}}})
    show(db.complaints.find_one({"complaint_id": cid}, {"_id": 0, "status": 1, "assigned_department": 1, "status_history.status": 1}))

    step("update_many - assign every pending DEMO complaint to a department",
         'db.complaints.updateMany({title:/^DEMO/, status:"Pending"}, {$set:{assigned_department:"General Administration"}})')
    r = db.complaints.update_many({"title": {"$regex": "^DEMO"}, "status": "Pending"},
                                  {"$set": {"assigned_department": "General Administration"}})
    show({"matched": r.matched_count, "modified": r.modified_count})

    step("find_one_and_update - atomically change and return the new document (admin urgency override)",
         f'db.complaints.findOneAndUpdate({{complaint_id:"{cid}"}}, {{$set:{{final_urgency:"High", urgency_overridden:true}}}}, {{returnDocument:"after"}})')
    from pymongo import ReturnDocument
    d = db.complaints.find_one_and_update({"complaint_id": cid},
                                          {"$set": {"final_urgency": "High", "urgency_overridden": True}},
                                          return_document=ReturnDocument.AFTER)
    show({k: d[k] for k in ("complaint_id", "predicted_urgency", "final_urgency", "urgency_overridden")})

    step("upsert - create the department document if it does not exist",
         'db.departments.updateOne({department_name:"Demo Dept"}, {$set:{...}}, {upsert:true})')
    r = db.departments.update_one({"department_name": "Demo Dept"},
                                  {"$set": {"responsibility": "Temporary demo department", "contact_email": "demo@campuspulse.local"}},
                                  upsert=True)
    show({"upserted_id": str(r.upserted_id) if r.upserted_id else None})

    step("Auto-increment ids: the counters document is changed with $inc + upsert inside next_id()",
         'db.counters.findOneAndUpdate({_id:"complaints"}, {$inc:{seq:1}}, {upsert:true, returnDocument:"after"})')
    show(db.counters.find_one({"_id": "complaints"}))

    # ------------------------------------------------------------------ DELETE
    heading("4. DELETE")
    step("delete_one", f'db.complaints.deleteOne({{complaint_id:"{cid}"}})')
    show({"deleted": db.complaints.delete_one({"complaint_id": cid}).deleted_count})
    step("delete_many - remove the remaining DEMO complaints", 'db.complaints.deleteMany({title:/^DEMO/})')
    show({"deleted": db.complaints.delete_many({"title": {"$regex": "^DEMO"}}).deleted_count})
    show({"demo_department_removed": db.departments.delete_one({"department_name": "Demo Dept"}).deleted_count})
    db.users.delete_one({"email": "demo.crud@example.com"})
    print("\nCRUD demo finished - demo documents were cleaned up.")


if __name__ == "__main__":
    main()
