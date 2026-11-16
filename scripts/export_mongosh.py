"""
Writes docs/mongosh_queries.js - the validators, CRUD queries and ALL aggregation pipelines of
CampusPulse in MongoDB Shell (mongosh / Compass) syntax. The pipelines are generated from the
very same Python objects the application runs, so the file can never drift out of date.

    python -m scripts.export_mongosh
"""
import json
import re
from datetime import datetime
from pathlib import Path

from database import aggregations as agg
from database.mongodb import utcnow
from database.schemas import VALIDATORS

OUT = Path(__file__).resolve().parent.parent / "docs" / "mongosh_queries.js"
DAY_MS = 86_400_000
IDENT = re.compile(r"^[$A-Za-z_][$A-Za-z0-9_]*$")


def to_js(value, now, indent=0):
    """Python structure -> mongosh source text (datetimes become relative `new Date(...)` expressions)."""
    pad = "  " * indent
    if isinstance(value, datetime):
        delta_ms = (now - value).total_seconds() * 1000
        if abs(delta_ms) < 2000:
            return "new Date()"
        return f"new Date(Date.now() - {round(delta_ms / DAY_MS)} * 24*60*60*1000)"
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [f'{pad}  {k if IDENT.match(k) else json.dumps(k)}: {to_js(v, now, indent + 1)}'
                 for k, v in value.items()]
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    if isinstance(value, (list, tuple)):
        if not value:
            return "[]"
        if all(not isinstance(v, (dict, list, tuple)) for v in value):
            return "[" + ", ".join(to_js(v, now) for v in value) + "]"
        items = [f"{pad}  {to_js(v, now, indent + 1)}" for v in value]
        return "[\n" + ",\n".join(items) + f"\n{pad}]"
    if value is None:
        return "null"
    return json.dumps(value)


HEADER = '''// =====================================================================================
// CampusPulse - MongoDB Shell (mongosh) queries
// Usage:  mongosh "<your connection string>"   then paste the sections you need,
//         or:  mongosh "<connection string>" --file docs/mongosh_queries.js   (runs read-only parts)
// Database used by the app: "campuspulse"
// =====================================================================================
use("campuspulse");

// ------------------------------------------------------------------ 1. VALIDATION ----
// (applied automatically by the app; shown here so you can explain / re-create them)
'''

CRUD = '''
// ------------------------------------------------------------------ 2. CRUD -----------
// ---- CREATE
db.complaints.insertOne({ /* a full complaint document - see docs/REPORT.md for the structure */ });
db.complaints.insertMany([ /* doc1, doc2, doc3 */ ]);

// ---- READ
db.complaints.findOne({ complaint_id: "CMP1010" });
db.complaints.find({ status: "Pending", final_urgency: "High" },
                   { complaint_id: 1, title: 1, location: 1, _id: 0 }).sort({ created_at: -1 }).limit(5);
db.complaints.find({ $or: [ { final_urgency: "High" }, { predicted_category: { $in: ["Security", "Electricity"] } } ] });
db.complaints.find({ title: { $regex: "wifi", $options: "i" } });
db.complaints.find({ $text: { $search: "wifi library" } });          // uses the text index
db.complaints.find({ status_history: { $elemMatch: { status: "Resolved" } } });
db.complaints.countDocuments({ status: "Pending" });
db.complaints.distinct("location");

// ---- UPDATE
db.complaints.updateOne(
  { complaint_id: "CMP1010" },
  { $set: { status: "In Progress", assigned_department: "IT Department", updated_at: new Date() },
    $push: { status_history: { status: "In Progress", updated_at: new Date(), updated_by: "USR1001", note: "Assigned to IT" } } });
db.complaints.updateMany({ status: "Pending", predicted_category: "Network" }, { $set: { assigned_department: "IT Department" } });
db.complaints.findOneAndUpdate({ complaint_id: "CMP1010" },
  { $set: { final_urgency: "High", urgency_overridden: true } }, { returnDocument: "after" });
db.departments.updateOne({ department_name: "Demo Dept" },
  { $set: { responsibility: "Temporary department", contact_email: "demo@campuspulse.local" } }, { upsert: true });
db.counters.findOneAndUpdate({ _id: "complaints" }, { $inc: { seq: 1 } }, { upsert: true, returnDocument: "after" });

// ---- DELETE
db.complaints.deleteOne({ complaint_id: "CMP1010" });
db.complaints.deleteMany({ title: /^DEMO/ });

// ------------------------------------------------------------------ 3. INDEXES ---------
db.complaints.getIndexes();
db.complaints.find({ status: "Pending" }).explain("queryPlanner");     // look for IXSCAN

// ------------------------------------------------------------------ 4. AGGREGATIONS ----
'''


def main():
    now = utcnow()
    parts = [HEADER]
    for name, validator in VALIDATORS.items():
        parts.append(f'db.runCommand({{ collMod: "{name}", validationLevel: "strict", validationAction: "error",\n  validator: {to_js(validator, now, 1)} }});\n')
    parts.append(CRUD)
    for i, (name, (fn, coll)) in enumerate(agg.ALL_PIPELINES.items(), start=1):
        doc = (fn.__doc__ or "").strip().replace("\n", "\n// ")
        parts.append(f"// {i}. {name}\n// {doc}\ndb.{coll}.aggregate({to_js(fn(), now)});\n")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
