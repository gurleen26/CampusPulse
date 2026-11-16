"""
CA2 demo - every aggregation pipeline used by CampusPulse, with its output, plus index usage (explain).

    python -m scripts.demo_aggregations
"""
from database import aggregations as agg
from database.mongodb import get_db, init_db
from scripts._show import as_json, heading, show, step


def stages(plan):
    """Collect the stage names of a query plan (e.g. IXSCAN, COLLSCAN)."""
    out = []
    if isinstance(plan, dict):
        if "stage" in plan:
            out.append(plan["stage"])
        for v in plan.values():
            out.extend(stages(v))
    elif isinstance(plan, list):
        for v in plan:
            out.extend(stages(v))
    return out


def main():
    db = init_db()
    heading("CampusPulse - aggregation demo")
    print(f"complaints in database: {db.complaints.count_documents({})}")
    for i, (name, (fn, coll)) in enumerate(agg.ALL_PIPELINES.items(), start=1):
        pipeline = fn()
        step(f"{i}. {name}  ({coll} collection)  -  {(fn.__doc__ or '').strip().splitlines()[0]}")
        print("    pipeline:")
        print("    " + as_json(pipeline).replace("\n", "\n    "))
        print("    output:")
        show(agg.run(pipeline, coll), limit=5)

    heading("Index usage (explain)")
    for label, query in [("status filter", {"status": "Pending"}),
                         ("category + location", {"predicted_category": "Network", "location": "Central Library"}),
                         ("one complaint by id", {"complaint_id": "CMP1001"})]:
        plan = db.complaints.find(query).explain()["queryPlanner"]["winningPlan"]
        print(f"   {label:<22} -> {' > '.join(stages(plan))}")


if __name__ == "__main__":
    main()
