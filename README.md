# CampusPulse – Smart Campus Complaint & Issue Management System

CampusPulse is a web-based complaint management system designed to simplify how students report campus issues and how administrators track, assign, and resolve them.

The application uses Machine Learning to automatically classify complaints and estimate their urgency, helping administrators prioritize issues more efficiently. It also identifies potentially similar complaints and provides an analytics dashboard for monitoring complaint trends and department performance.

## Live Application

**Live Demo:** https://campuspulse-yk8j.onrender.com

**GitHub Repository:** https://github.com/gurleen26/CampusPulse

## Key Features

### Student Module
- Student registration and secure login.
- Submit complaints with descriptions, categories, locations, and optional images.
- Automatic complaint category prediction using Machine Learning.
- Automatic urgency estimation (Low, Medium, High).
- Live complaint analysis before submission.
- Similar complaint detection to identify potentially duplicate issues.
- Track complaint status and resolution progress.
- Submit feedback after complaint resolution.

### Admin Module
- Secure administrator login.
- View and manage submitted complaints.
- Assign complaints to relevant departments.
- Update complaint statuses.
- Manually override predicted urgency when necessary.
- View complaint statistics and trends through an analytics dashboard.
- Export complaint records to CSV.

### Machine Learning
- TF-IDF-based text feature extraction.
- Logistic Regression classifiers for category and urgency prediction.
- Prediction confidence scores.
- Similarity detection using TF-IDF and cosine similarity.
- Model evaluation using accuracy, precision, recall, and F1-score.

## Technology Stack

| Component | Technologies |
|---|---|
| Backend | Python, Flask |
| Database | MongoDB Atlas, PyMongo |
| Machine Learning | Scikit-learn, TF-IDF, Logistic Regression |
| Data Processing | Pandas, NumPy |
| Visualization | Plotly |
| Frontend | HTML, CSS, JavaScript, Bootstrap |
| Authentication | Flask-Login, Werkzeug |
| Deployment | Render, Gunicorn |
| Version Control | Git, GitHub |

## Application Workflow

1. A student registers and logs into the application.
2. The student enters a complaint describing the campus issue.
3. The ML module processes the complaint text and predicts its category and urgency.
4. The system checks for potentially similar existing complaints.
5. The student submits the complaint, which is stored in MongoDB.
6. The administrator reviews the complaint, assigns it to a department, and updates its status.
7. Students can track progress, while administrators monitor overall performance through analytics.

## Machine Learning Approach

CampusPulse uses two independent classification models:

- **Category Classification:** Predicts the appropriate complaint category.
- **Urgency Classification:** Estimates whether a complaint should be treated as Low, Medium, or High priority.

### Model Training
- Text preprocessing and cleaning.
- TF-IDF vectorization with unigrams and bigrams.
- Logistic Regression classification.
- Stratified train-test split.
- Comparison against baseline classifiers.
- Evaluation using accuracy, macro F1-score, precision, and recall.

### Urgency Model Evaluation

| Metric | Result |
|---|---:|
| Dataset size | 1,798 |
| Training samples | 1,438 |
| Testing samples | 360 |
| Accuracy | 84.72% |
| Macro F1-score | 85.30% |

The model was also evaluated using a separate set of 40 manually written test examples, achieving 80% accuracy.

*Note: The dataset contains synthetic complaint examples. These evaluation results should be interpreted in that context and may not represent performance on real-world campus complaints.*

## Database Design

CampusPulse uses MongoDB as its primary database.

The application maintains the following collections:

| Collection | Purpose |
|---|---|
| `users` | Stores student and administrator information |
| `complaints` | Stores complaint details, predictions, assignments, and status updates |
| `departments` | Stores department information |
| `feedback` | Stores student feedback |
| `counters` | Supports sequential ID generation |

MongoDB schema validation and indexes are used to improve data consistency and query performance.

## Project Structure

```text
CampusPulse/
│
├── app.py
├── config.py
├── wsgi.py
├── requirements.txt
├── .env.example
│
├── database/
│   ├── mongodb.py
│   ├── repository.py
│   ├── schemas.py
│   └── aggregations.py
│
├── ml/
│   ├── preprocess.py
│   ├── trainer.py
│   ├── predict.py
│   └── similarity.py
│
├── models/
│   ├── category_model.pkl
│   ├── category_vectorizer.pkl
│   ├── urgency_model.pkl
│   └── urgency_vectorizer.pkl
│
├── routes/
│   ├── auth.py
│   ├── student.py
│   ├── admin.py
│   └── files.py
│
├── templates/
├── static/
├── data/
├── scripts/
├── tests/
└── docs/
```

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/gurleen26/CampusPulse.git
cd CampusPulse
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows**
```bash
venv\Scripts\activate
```

**Linux/macOS**
```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root using `.env.example` as a reference.

Configure the required values:

```env
SECRET_KEY=your-secret-key
MONGO_URI=your-mongodb-connection-string
MONGO_DB_NAME=campuspulse
FLASK_DEBUG=1
```

Add administrator configuration values if required by the application's initialization process.

**Important:** Never commit your `.env` file, database credentials, or secret keys to GitHub.

### 5. Initialize the database

Run the database initialization command used by the application:

```bash
python -c "from database.mongodb import init_db; init_db()"
```

### 6. Start the application

```bash
python app.py
```

Open the application at:

```text
http://127.0.0.1:5000
```

## Deployment

The application is deployed on **Render**, with MongoDB Atlas used as the cloud database.

- **Hosting:** Render
- **Database:** MongoDB Atlas
- **Application Server:** Gunicorn
- **Entry Point:** `wsgi.py`

Render configuration:

**Build Command**
```bash
pip install -r requirements.txt
```

**Start Command**
```bash
gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

Configure the required environment variables in the Render dashboard rather than hardcoding credentials in the source code.

## Limitations

- The ML models are trained on synthetic complaint data, so real-world performance requires further validation.
- Predicted urgency is advisory; administrators can review and override it.
- Similarity detection identifies textually similar complaints and does not guarantee that two complaints describe the same issue.
- Uploaded files require persistent storage or external object storage to survive application restarts and redeployments on ephemeral hosting environments.

## Future Enhancements

- Train and evaluate models using real campus complaint data.
- Introduce notification and email alert functionality.
- Improve duplicate complaint detection using semantic embeddings.
- Add role-based department access.
- Integrate persistent cloud storage for uploaded images.
- Improve ML performance through larger and more diverse datasets.

## Author

Developed as a full-stack application combining web development, NoSQL database design, and Machine Learning to address campus issue management.