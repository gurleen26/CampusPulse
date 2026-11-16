"""
MongoDB schema-validation rules ($jsonSchema) for every collection.

MongoDB is schema-less by default; these validators make the database itself
reject bad documents (wrong type, missing field, value outside the allowed list).
They are applied with validationLevel="strict" and validationAction="error".
"""
from config import CATEGORIES, LOCATIONS, STATUSES, URGENCY_LEVELS

EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
INT = ["int", "long"]

USERS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "title": "User account",
        "required": ["user_id", "name", "email", "password_hash", "role", "created_at"],
        "additionalProperties": True,
        "properties": {
            "user_id": {"bsonType": "string", "pattern": r"^USR\d+$",
                        "description": "Business id such as USR1001"},
            "name": {"bsonType": "string", "minLength": 2, "maxLength": 80},
            "email": {"bsonType": "string", "pattern": EMAIL_PATTERN},
            "password_hash": {"bsonType": "string", "minLength": 20},
            "role": {"enum": ["student", "admin"]},
            "created_at": {"bsonType": "date"},
        },
    }
}

COMPLAINTS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "title": "Campus complaint",
        "required": ["complaint_id", "student_id", "title", "description", "location",
                     "predicted_category", "predicted_urgency", "final_urgency",
                     "status", "status_history", "created_at"],
        "properties": {
            "complaint_id": {"bsonType": "string", "pattern": r"^CMP\d+$"},
            "student_id": {"bsonType": "string", "pattern": r"^USR\d+$"},
            "student_name": {"bsonType": "string"},
            "title": {"bsonType": "string", "minLength": 5, "maxLength": 120},
            "description": {"bsonType": "string", "minLength": 10, "maxLength": 2000},
            "location": {"enum": LOCATIONS},
            "predicted_category": {"enum": CATEGORIES},
            "category_confidence": {"bsonType": "number", "minimum": 0, "maximum": 1},
            "predicted_urgency": {"enum": URGENCY_LEVELS},
            "urgency_confidence": {"bsonType": "number", "minimum": 0, "maximum": 1},
            "final_urgency": {"enum": URGENCY_LEVELS,
                              "description": "Urgency actually used; equals the prediction unless an admin overrides it"},
            "urgency_overridden": {"bsonType": "bool"},
            "status": {"enum": STATUSES},
            "assigned_department": {"bsonType": ["string", "null"]},
            "image_filename": {"bsonType": ["string", "null"]},
            "similar_complaints": {
                "bsonType": "array",
                "items": {"bsonType": "object", "required": ["complaint_id", "score"],
                          "properties": {"complaint_id": {"bsonType": "string"},
                                         "score": {"bsonType": "number"}}},
            },
            "status_history": {
                "bsonType": "array",
                "minItems": 1,
                "items": {"bsonType": "object", "required": ["status", "updated_at"],
                          "properties": {"status": {"enum": STATUSES},
                                         "updated_at": {"bsonType": "date"},
                                         "updated_by": {"bsonType": "string"},
                                         "note": {"bsonType": "string"}}},
            },
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
            "resolved_at": {"bsonType": ["date", "null"]},
        },
    }
}

DEPARTMENTS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "title": "Department",
        "required": ["department_name", "responsibility", "contact_email"],
        "properties": {
            "department_name": {"bsonType": "string", "minLength": 3, "maxLength": 80},
            "responsibility": {"bsonType": "string", "minLength": 5},
            "contact_email": {"bsonType": "string", "pattern": EMAIL_PATTERN},
            "categories": {"bsonType": "array", "items": {"enum": CATEGORIES}},
        },
    }
}

FEEDBACK_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "title": "Resolution feedback",
        "required": ["complaint_id", "student_id", "rating", "created_at"],
        "properties": {
            "complaint_id": {"bsonType": "string", "pattern": r"^CMP\d+$"},
            "student_id": {"bsonType": "string", "pattern": r"^USR\d+$"},
            "rating": {"bsonType": INT, "minimum": 1, "maximum": 5},
            "feedback": {"bsonType": "string", "maxLength": 500},
            "created_at": {"bsonType": "date"},
        },
    }
}

VALIDATORS = {
    "users": USERS_VALIDATOR,
    "complaints": COMPLAINTS_VALIDATOR,
    "departments": DEPARTMENTS_VALIDATOR,
    "feedback": FEEDBACK_VALIDATOR,
}
