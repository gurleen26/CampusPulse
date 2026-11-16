# CampusPulse - Project Report
**Course:** CSE494 Intelligent NoSQL Databases  **Task:** CA2 (Project)  **Database:** MongoDB  **Language:** Python (PyMongo, Flask)

> Draft report generated with the project. Replace this line with your name/registration number, re-run the demo
> scripts on your machine, paste your own screenshots, and edit the text so it is in your own words.

## 1. Problem and real-world relevance
Colleges handle complaints (Wi-Fi, electricity, water, classrooms, hostels, cleanliness, security) through paper forms,
e-mails and word of mouth. Complaints get lost, reach the wrong department late, repeat without anyone noticing, and
there is no transparency or data to find recurring problems. CampusPulse centralises this: students submit and track
complaints, ML suggests category/urgency and flags duplicates, and administrators assign, update and analyse complaints.

## 2. Objectives
Central complaint platform; student submit/track; automatic category and urgency prediction; similar-complaint
detection; recurring-issue detection; admin tools; MongoDB as the primary database; analytics reports.

## 3. Database design (MongoDB)
Database `campuspulse`, five collections.

| Collection | Purpose | Key fields |
|---|---|---|
| `users` | students and admins | `user_id` (USR1001), `name`, `email` (unique), `password_hash`, `role`, `created_at` |
| `complaints` | complaints + ML output | `complaint_id` (CMP1001, unique), `student_id`, `title`, `description`, `location`, `predicted_category`, `predicted_urgency`, `final_urgency`, `status`, `assigned_department`, `similar_complaints[]`, `status_history[]`, `created_at`, `resolved_at` |
| `departments` | responsible departments | `department_name` (unique), `responsibility`, `contact_email`, `categories[]` |
| `feedback` | rating after resolution | `complaint_id` (unique), `student_id`, `rating` 1-5, `feedback`, `created_at` |
| `counters` | atomic auto-increment ids | `_id` ("complaints"/"users"), `seq` |

**Design decisions (why MongoDB suits this):**
* **Embedding** - `status_history` and `similar_complaints` are arrays inside the complaint: they are always read with the
  complaint, never queried alone, and grow slowly, so one read returns the whole timeline (no join).
* **Referencing** - complaints refer to students by `student_id`; feedback refers to complaints by `complaint_id`
  (feedback is created later, by a different actor, and aggregated separately -> `$lookup` when needed).
* **Denormalisation** - `student_name` is copied into the complaint so admin lists need no join.
* **Predicted vs final urgency** - `predicted_urgency` is never overwritten; an admin override changes `final_urgency`
  and sets `urgency_overridden`, keeping the ML output available for evaluation.
* **Dates** are stored as BSON dates so aggregation can compute durations.

Example complaint document:
```json
{ "complaint_id": "CMP1024", "student_id": "USR1003", "student_name": "Demo Student 2",
  "title": "Wi-Fi not working", "description": "Wi-Fi is unavailable in the library", "location": "Central Library",
  "predicted_category": "Network", "category_confidence": 0.91,
  "predicted_urgency": "Medium", "urgency_confidence": 0.74, "final_urgency": "Medium", "urgency_overridden": false,
  "status": "In Progress", "assigned_department": "IT Department", "image_filename": null,
  "similar_complaints": [{"complaint_id": "CMP1019", "score": 0.62}],
  "status_history": [{"status": "Pending", "updated_at": "...", "updated_by": "USR1003", "note": "Complaint submitted"},
                    {"status": "In Progress", "updated_at": "...", "updated_by": "USR1001", "note": "Assigned to IT"}],
  "created_at": "...", "updated_at": "...", "resolved_at": null }
```
**Indexes** (`database/mongodb.py`): unique `email`, `user_id`, `complaint_id`, `department_name`, feedback `complaint_id`;
compound `(status, created_at)`, `(predicted_category, location)`, `(student_id, created_at)`, `(assigned_department, status)`;
`created_at`; text index on `title + description`. `explain()` shows `IXSCAN` for the main queries
(`docs/sample_output/aggregation_output.txt`).

## 4. Validation rules
Implemented with `$jsonSchema` validators (`database/schemas.py`) applied with `validationLevel: strict` and
`validationAction: error` - MongoDB itself rejects invalid documents, independent of the Python code.

| Collection | Rules |
|---|---|
| complaints | required fields; `complaint_id` pattern `^CMP\d+$`; `title` 5-120 chars; `description` 10-2000 chars; `location`, `predicted_category`, `predicted_urgency`, `final_urgency`, `status` restricted by `enum`; confidences 0-1; dates must be BSON `date`; `status_history` array with at least one valid entry |
| users | e-mail regex; `role` in {student, admin}; name 2-80 chars; hash min length; unique e-mail |
| feedback | `rating` integer 1-5; comment max 500; one feedback per complaint (unique index) |
| departments | name, responsibility, valid contact e-mail; `categories` restricted by `enum` |

`python -m scripts.demo_validation` inserts invalid documents (wrong status, short title, unknown location, string date,
missing field, bad e-mail, rating 9, duplicate e-mail) and shows MongoDB rejecting each with the exact rule that failed.
The web application adds a second layer (form validation, CSRF token, password rules).

## 5. CRUD operations (PyMongo)
All in `database/repository.py`; demonstrated step by step in `scripts/demo_crud.py` (and `docs/mongosh_queries.js`).

| Operation | PyMongo call | Used for |
|---|---|---|
| Create | `insert_one`, `insert_many` | register user, submit complaint, add feedback, seed data |
| Read | `find_one`, `find` + filter/projection/sort/skip/limit, `count_documents`, `distinct`, `$regex`, `$text`, `$in`, `$or`, `$elemMatch` | login, my complaints, admin filters + search + paging |
| Update | `update_one` (`$set` + `$push`), `update_many`, `find_one_and_update` (`$inc`, upsert) | status change with history, department assignment, urgency override, id counters |
| Delete | `delete_one`, `delete_many` | demo clean-up (deliberately not exposed to students) |

## 6. Aggregation pipelines
12 pipelines in `database/aggregations.py`; each returns a plain Python list, so it is the same pipeline that is shown in
`docs/mongosh_queries.js` and run by the dashboard.

| # | Pipeline | Stages / operators | Answers |
|---|---|---|---|
| 1 | category_counts | `$group`, `$sum`, `$sort` | complaints per category |
| 2 | urgency_counts | `$group`, `$sort` | urgency distribution |
| 3 | location_category_matrix | `$group` on a compound `_id` | heat-map data |
| 4 | daily_trend | `$match`, `$dateToString`, `$group` | complaints per day |
| 5 | department_performance | `$match`, `$group` + `$cond`/`$avg`/`$$REMOVE`, `$addFields`, `$round` | resolution rate, average hours |
| 6 | recurring_issues | `$match`, `$group`, `$push`/`$min`/`$max`, second `$match` | same category + location >= 3 times in 30 days |
| 7 | overdue_complaints | `$match`, `$addFields`, `$subtract`/`$divide`, `$project` | open complaints older than 3 days |
| 8 | feedback_by_department | `$lookup`, `$unwind`, `$group`, `$avg` | satisfaction per department (join) |
| 9 | dashboard_summary | `$facet` | several summaries in one query |
| 10 | first_response_time_by_category | `$filter`, `$arrayElemAt` on `status_history`, `$group` | time until work started |
| 11 | resolution_time_buckets | `$bucket` | <1 day / 1-3 days / 3-7 days / 7+ |
| 12 | top_reporters | `$group`, `$sort`, `$limit` | most active students |

## 7. PyMongo implementation
`database/mongodb.py`: `MongoClient(MONGO_URI)`; connection check with `ping` and a friendly error; `create_collection`
with validator (or `collMod` for existing collections, so the app is safe to restart); `create_index`;
`update_one(..., upsert=True)` for seeding; `find_one_and_update` with `$inc` for atomic auto-increment ids (safe when
two students submit at the same moment). Errors handled in the web layer: `DuplicateKeyError`, `WriteError`.
Credentials live in `.env`, never in the code.

## 8. Machine-learning module
* **Text cleaning** (`ml/preprocess.py`): lower-case, normalise Wi-Fi/internet spelling, strip punctuation, small stop-word
  list that keeps negations ("not", "no") and scope words ("all", "entire").
* **Features:** TF-IDF, 1-2 grams. **Models:** Logistic Regression for category and for urgency.
* **Similarity:** TF-IDF cosine similarity between a new complaint and stored complaints of the *same location*
  (location words and "not working" removed before comparing); threshold 0.25; matches are only suggested.
* **Data:** 1,800 synthetic complaints (1,798 after removing duplicates) generated from templates with written urgency
  rules (`data/generate_dataset.py`) + 40 hand-written complaints used only for testing.

Measured results (this project's run; reproduce with `python -m ml.train_category` / `train_urgency`):

| Model | Held-out test (360 rows) accuracy | Macro-F1 | Best baseline (Naive Bayes) macro-F1 | 40 hand-written complaints accuracy |
|---|---|---|---|---|
| Category | 1.000 | 1.000 | 0.994 | **0.925** |
| Urgency | 0.847 | 0.853 | 0.771 | **0.800** (High-urgency recall 0.80) |

Urgency per-class recall on the held-out set: Low 0.97, Medium 0.78, High 0.82. Confusion matrix (rows = true,
columns = Low/Medium/High): `[[97,3,0],[10,108,20],[1,21,100]]` - most errors are Medium vs High.

**Interpretation / limitations.** The 1.000 held-out category score is inflated because the data is template-generated
(test rows resemble training rows); the hand-written set is the fairer estimate. Typical misses: "ceiling fan in my
classroom" (Electricity vs Classroom Equipment), "CCTV not working" (Security vs Electricity). Urgency is the harder task
and missed High cases exist, which is why it is advisory and admin-overridable. TF-IDF similarity matches words, not
meaning. Training on real anonymised complaints would be the main improvement.

## 9. Application features
Student: register/login, submit (with live prediction and duplicate warning), optional image, track status timeline,
feedback after resolution. Admin: dashboard (KPI cards, 5 Plotly charts, recurring issues, overdue list, department
performance, satisfaction), filter/search/paginate complaints, assign department (suggestion pre-selected), change
status (history recorded), override urgency, CSV export. Security: hashed passwords, role-based access, students see
only their own complaints, CSRF tokens, validated image uploads, environment variables for secrets.

## 10. Testing
`python -m pytest -q` - 27 tests against a real MongoDB (separate database): ML predictions and similarity, validators
reject bad documents, unique indexes, CRUD lifecycle, aggregation results, registration/login, access control,
complaint submission and validation, other-student access (404), image upload checks, admin workflow, feedback rules,
CSRF, CSV export. All 27 passed in the development environment.
The browser UI (Bootstrap/Plotly from CDN) was tested through HTTP requests and rendered templates, but was **not**
viewed in a real browser during development - check it once on your machine and add screenshots.

## 11. Conclusion and future work
CampusPulse shows MongoDB's strengths for this domain: flexible documents with embedded history, strict validation where
needed, indexes for filtering, and aggregation pipelines for analytics. Future work: real training data, sentence
embeddings for similarity, e-mail notifications to departments, SLA rules per urgency, deployment with a production server.
