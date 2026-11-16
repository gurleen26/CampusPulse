# CampusPulse - Smart Campus Complaint & Issue Management System

Flask + **MongoDB (PyMongo)** + scikit-learn. Students submit campus complaints; machine learning predicts the
**category** and **urgency**, warns about **similar complaints**, and admins manage everything from an analytics dashboard.
Built for CSE494 *Intelligent NoSQL Databases* - CA2 (validation, CRUD, aggregation, PyMongo).

## 1. Run it on your laptop

**You need:** Python 3.10+ (3.11 recommended) and a MongoDB (pick ONE):

| Option | Steps |
|---|---|
| **A. Local MongoDB (easiest)** | Install *MongoDB Community Server* from mongodb.com/try/download/community (Windows: tick "Install as a Service"). Nothing else to configure. |
| **B. MongoDB Atlas** | Create a free cluster, add a database user, allow your IP under *Network Access*, copy the connection string, and put it in `.env` as `MONGO_URI=mongodb+srv://...` |

**Windows:** extract the zip, double-click `setup.bat` (once), then `run.bat`.
**Linux/macOS:** `./setup.sh` then `./run.sh`.
**Or manually (VS Code terminal):**
```bash
python -m venv venv
venv\Scripts\activate            # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python -m scripts.seed_demo      # optional: loads ~155 demo complaints so the dashboard is not empty
python app.py                    # open http://127.0.0.1:5000
```
On first start the app creates the database, validated collections, indexes, departments and the admin account,
and trains the ML models automatically (a few seconds).

**Logins**

| Role | E-mail | Password |
|---|---|---|
| Admin | `admin@campuspulse.local` | `Admin@123` (change in `.env`) |
| Demo student (after seeding) | `student1@example.com` ... `student8@example.com` | `Student@123` |

The browser needs internet access (Bootstrap and Plotly load from a CDN).

## 2. Scripts for the CA2 demo / viva

```bash
python -m scripts.demo_validation     # $jsonSchema validator + rejected invalid inserts
python -m scripts.demo_crud           # insert/find/update/delete with PyMongo (cleans up after itself)
python -m scripts.demo_aggregations   # all 12 pipelines, their output, and index usage (explain)
python -m scripts.export_mongosh      # regenerates docs/mongosh_queries.js (mongosh / Compass syntax)
python -m ml.train_category           # retrain + print metrics (confusion matrix, baselines)
python -m ml.train_urgency
python -m pytest -q                   # 27 tests (uses a separate database: campuspulse_test)
```
`docs/sample_output/` holds example output of the three demo scripts - **run them yourself** and take your own screenshots.

## 3. CA2 requirement -> where to find it

| Requirement | Where |
|---|---|
| Document structure design | `database/schemas.py`, `docs/REPORT.md` section 3 (embedded `status_history`, referenced `student_id`, denormalised `student_name`) |
| Validation rules | `database/schemas.py` (`$jsonSchema`: required, types, enum, pattern, min/max length, range), unique + compound + text indexes in `database/mongodb.py` |
| CRUD | `database/repository.py` (used by the web app) and `scripts/demo_crud.py` |
| Aggregation | `database/aggregations.py` - 12 pipelines (`$group`, `$match`, `$lookup`, `$facet`, `$bucket`, `$filter`, `$dateToString`, ...) |
| PyMongo | `database/mongodb.py` (connection, `create_collection`/`collMod`, `create_index`, atomic counters), `repository.py`, `aggregations.py` |
| Report | `docs/REPORT.md` (adapt it to your own words before submitting) |

## 4. Project layout
```
app.py  config.py  analytics.py  utils.py  requirements.txt  .env
data/      generate_dataset.py, raw/complaints.csv (1,800 synthetic rows), raw/manual_test.csv (40 hand-written)
ml/        preprocess.py, trainer.py, train_category.py, train_urgency.py, predict.py, similarity.py
database/  mongodb.py (connection/validators/indexes/seed), schemas.py, repository.py, aggregations.py
routes/    auth.py, student.py, admin.py, files.py
templates/ static/ uploads/ models/ scripts/ tests/ docs/
```

## 5. Honest notes
* The training data is **synthetic** (generated from templates by `data/generate_dataset.py`), so the held-out scores
  are optimistic. The more honest figure is the score on the 40 hand-written complaints (see `docs/REPORT.md`).
  Real complaints would improve and properly test the models.
* Urgency prediction is advisory; admins can override it (`final_urgency` vs `predicted_urgency` are stored separately).
* Similarity compares only complaints from the same location and uses TF-IDF, so it matches shared words, not meaning.
* `nltk` from the blueprint was not used (a small built-in stop-word list avoids extra downloads).
* This is a development server (`app.run`); it is meant for demo, not production hosting.
