# Viva cheat-sheet (read the code once, then answer in your own words)

**Why MongoDB?** Complaints have nested/variable parts (status history, similar complaints, optional image) -> documents fit
better than many joined tables; aggregation pipeline gives analytics; schema validation still keeps data clean.

**Embed or reference?** Embedded: `status_history` (read together, small). Referenced: student and feedback (different
lifecycle, aggregated separately, `$lookup`).

**Where is validation?** `database/schemas.py` -> `$jsonSchema` (`required`, `bsonType`, `enum`, `pattern`, `minLength`, `minimum`).
`validationLevel: strict`, `validationAction: error`. Demo: `python -m scripts.demo_validation`.

**Why indexes?** `status_created` and `category_location` speed filters/aggregation `$match`; unique indexes enforce
uniqueness; text index enables `$text` search. Show `explain()` -> IXSCAN.

**Explain recurring_issues:** `$match` last 30 days, `$group` by (category, location) counting and `$push`-ing ids, then a
second `$match count >= 3` (like SQL HAVING), `$sort`.

**Explain department_performance:** `$group` by department; `$cond` turns "resolved" into 1/0 for a sum; `$avg` of hours
(`resolved_at - created_at` in ms / 3,600,000), `$$REMOVE` skips unresolved ones; `$addFields` computes the percentage.

**Difference `$lookup` vs embedding?** `$lookup` joins at query time (feedback -> complaints); embedding stores together.

**Why `find_one_and_update` with `$inc` for ids?** Atomic - two simultaneous submissions can never get the same id.

**ML:** TF-IDF turns text into weighted word vectors; Logistic Regression learns weights per class; cosine similarity
measures the angle between two vectors. Held-out category score is inflated by synthetic data - the 40 hand-written
complaints give the honest number. Urgency is advisory (admin override keeps `predicted_urgency`).

**Be ready to write a query live,** e.g. "complaints in Hostel Block A that are High urgency and not resolved":
`db.complaints.find({location:"Hostel Block A", final_urgency:"High", status:{$ne:"Resolved"}})`
"average rating per category": `$lookup` feedback -> `$group` by `$complaint.predicted_category` with `$avg:"$rating"`.
