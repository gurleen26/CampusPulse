"""
Aggregation pipelines used by the analytics dashboard and the CA2 demo scripts.
Each function RETURNS the pipeline (a Python list), so the same pipeline can be
printed, explained in the viva, or run with db.complaints.aggregate(pipeline).
"""
from datetime import timedelta

from database.mongodb import get_db, utcnow

MS_PER_HOUR = 3_600_000
MS_PER_DAY = 86_400_000
OPEN_STATUSES = ["Pending", "In Progress"]


def _hours_between(later, earlier):
    return {"$divide": [{"$subtract": [later, earlier]}, MS_PER_HOUR]}


# 1 --------------------------------------------------------------------------
def category_counts():
    """How many complaints per predicted category?   ($group + $sort)"""
    return [
        {"$group": {"_id": "$predicted_category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]


# 2 --------------------------------------------------------------------------
def urgency_counts():
    """Distribution of the final urgency level.   ($group + $sort)"""
    return [
        {"$group": {"_id": "$final_urgency", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]


# 3 --------------------------------------------------------------------------
def location_category_matrix():
    """Complaint count for every (location, category) pair - feeds the heat-map.   ($group on a compound key)"""
    return [
        {"$group": {"_id": {"location": "$location", "category": "$predicted_category"},
                    "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]


# 4 --------------------------------------------------------------------------
def daily_trend(days=30):
    """Complaints submitted per day in the last N days.   ($match + $dateToString + $group + $sort)"""
    since = utcnow() - timedelta(days=days)
    return [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]


# 5 --------------------------------------------------------------------------
def department_performance():
    """Per department: total, resolved, resolution rate %, average hours to resolve.
    ($match + $group with $cond / $avg + $addFields + $sort)"""
    resolved_flag = {"$cond": [{"$eq": ["$status", "Resolved"]}, 1, 0]}
    resolution_hours = {"$cond": [
        {"$and": [{"$eq": ["$status", "Resolved"]}, {"$ne": ["$resolved_at", None]}]},
        _hours_between("$resolved_at", "$created_at"),
        "$$REMOVE",                       # $avg ignores missing values
    ]}
    return [
        {"$match": {"assigned_department": {"$ne": None}}},
        {"$group": {"_id": "$assigned_department",
                    "total": {"$sum": 1},
                    "resolved": {"$sum": resolved_flag},
                    "avg_hours": {"$avg": resolution_hours}}},
        {"$addFields": {
            "resolution_rate": {"$round": [{"$multiply": [{"$divide": ["$resolved", "$total"]}, 100]}, 1]},
            "avg_hours": {"$round": ["$avg_hours", 1]}}},
        {"$sort": {"resolution_rate": -1, "total": -1}},
    ]


# 6 --------------------------------------------------------------------------
def recurring_issues(days=30, min_count=3):
    """Same category at the same location reported >= min_count times recently = recurring issue.
    ($match + $group + $push + $match on the group result + $sort)"""
    since = utcnow() - timedelta(days=days)
    return [
        {"$match": {"created_at": {"$gte": since}, "status": {"$ne": "Rejected"}}},
        {"$group": {"_id": {"category": "$predicted_category", "location": "$location"},
                    "count": {"$sum": 1},
                    "open_count": {"$sum": {"$cond": [{"$in": ["$status", OPEN_STATUSES]}, 1, 0]}},
                    "first_reported": {"$min": "$created_at"},
                    "last_reported": {"$max": "$created_at"},
                    "complaint_ids": {"$push": "$complaint_id"}}},
        {"$match": {"count": {"$gte": min_count}}},
        {"$sort": {"count": -1, "last_reported": -1}},
    ]


# 7 --------------------------------------------------------------------------
def overdue_complaints(days=3):
    """Open complaints older than N days, oldest first.   ($match + $addFields + $project + $sort)"""
    now = utcnow()
    cutoff = now - timedelta(days=days)
    return [
        {"$match": {"status": {"$in": OPEN_STATUSES}, "created_at": {"$lt": cutoff}}},
        {"$addFields": {"age_days": {"$round": [{"$divide": [{"$subtract": [now, "$created_at"]}, MS_PER_DAY]}, 1]}}},
        {"$project": {"_id": 0, "complaint_id": 1, "title": 1, "location": 1, "status": 1,
                      "final_urgency": 1, "assigned_department": 1, "age_days": 1}},
        {"$sort": {"age_days": -1}},
    ]


# 8 --------------------------------------------------------------------------
def feedback_by_department():
    """Average student rating per department by JOINING feedback with complaints.
    ($lookup + $unwind + $group + $sort)  - run on the *feedback* collection"""
    return [
        {"$lookup": {"from": "complaints", "localField": "complaint_id",
                     "foreignField": "complaint_id", "as": "complaint"}},
        {"$unwind": "$complaint"},
        {"$group": {"_id": {"$ifNull": ["$complaint.assigned_department", "Unassigned"]},
                    "avg_rating": {"$avg": "$rating"}, "responses": {"$sum": 1}}},
        {"$addFields": {"avg_rating": {"$round": ["$avg_rating", 2]}}},
        {"$sort": {"avg_rating": -1}},
    ]


# 9 --------------------------------------------------------------------------
def dashboard_summary():
    """Several small summaries in ONE round-trip.   ($facet)"""
    return [
        {"$facet": {
            "total": [{"$count": "n"}],
            "by_status": [{"$group": {"_id": "$status", "count": {"$sum": 1}}}],
            "open_high": [{"$match": {"status": {"$in": OPEN_STATUSES}, "final_urgency": "High"}},
                          {"$count": "n"}],
            "overridden": [{"$match": {"urgency_overridden": True}}, {"$count": "n"}],
        }}
    ]


# 10 -------------------------------------------------------------------------
def first_response_time_by_category():
    """Average hours from submission until the complaint first became 'In Progress'.
    Digs into the embedded status_history array.   ($addFields + $filter + $arrayElemAt + $group)"""
    return [
        {"$addFields": {"first_progress": {"$arrayElemAt": [
            {"$filter": {"input": "$status_history", "as": "h",
                         "cond": {"$eq": ["$$h.status", "In Progress"]}}}, 0]}}},
        {"$match": {"first_progress": {"$exists": True}}},
        {"$group": {"_id": "$predicted_category",
                    "avg_hours": {"$avg": _hours_between("$first_progress.updated_at", "$created_at")},
                    "complaints": {"$sum": 1}}},
        {"$addFields": {"avg_hours": {"$round": ["$avg_hours", 1]}}},
        {"$sort": {"avg_hours": 1}},
    ]


# 11 -------------------------------------------------------------------------
def resolution_time_buckets():
    """Resolved complaints grouped into time buckets (<1 day, 1-3 days, 3-7 days, 7+ days).   ($match + $bucket)"""
    return [
        {"$match": {"status": "Resolved", "resolved_at": {"$ne": None}}},
        {"$addFields": {"hours": _hours_between("$resolved_at", "$created_at")}},
        {"$bucket": {"groupBy": "$hours", "boundaries": [0, 24, 72, 168], "default": "168+",
                     "output": {"count": {"$sum": 1}}}},
    ]


# 12 -------------------------------------------------------------------------
def top_reporters(limit=5):
    """Students who filed the most complaints.   ($group + $sort + $limit)"""
    return [
        {"$group": {"_id": {"student_id": "$student_id", "name": "$student_name"}, "complaints": {"$sum": 1}}},
        {"$sort": {"complaints": -1}},
        {"$limit": limit},
    ]


# ------------------------------------------------------------------ runners --
def run(pipeline, collection="complaints"):
    return list(get_db()[collection].aggregate(pipeline))


def summary_numbers():
    """Flatten the $facet result into simple numbers for the dashboard cards."""
    res = run(dashboard_summary())
    r = res[0] if res else {}
    first = lambda key: (r.get(key) or [{"n": 0}])[0]["n"]
    status = {s["_id"]: s["count"] for s in r.get("by_status", [])}
    return {
        "total": first("total"),
        "pending": status.get("Pending", 0),
        "in_progress": status.get("In Progress", 0),
        "resolved": status.get("Resolved", 0),
        "rejected": status.get("Rejected", 0),
        "open_high": first("open_high"),
        "overridden": first("overridden"),
    }


ALL_PIPELINES = {
    "category_counts": (category_counts, "complaints"),
    "urgency_counts": (urgency_counts, "complaints"),
    "location_category_matrix": (location_category_matrix, "complaints"),
    "daily_trend": (daily_trend, "complaints"),
    "department_performance": (department_performance, "complaints"),
    "recurring_issues": (recurring_issues, "complaints"),
    "overdue_complaints": (overdue_complaints, "complaints"),
    "feedback_by_department": (feedback_by_department, "feedback"),
    "dashboard_summary": (dashboard_summary, "complaints"),
    "first_response_time_by_category": (first_response_time_by_category, "complaints"),
    "resolution_time_buckets": (resolution_time_buckets, "complaints"),
    "top_reporters": (top_reporters, "complaints"),
}
