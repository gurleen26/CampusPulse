// =====================================================================================
// CampusPulse - MongoDB Shell (mongosh) queries
// Usage:  mongosh "<your connection string>"   then paste the sections you need,
//         or:  mongosh "<connection string>" --file docs/mongosh_queries.js   (runs read-only parts)
// Database used by the app: "campuspulse"
// =====================================================================================
use("campuspulse");

// ------------------------------------------------------------------ 1. VALIDATION ----
// (applied automatically by the app; shown here so you can explain / re-create them)

db.runCommand({ collMod: "users", validationLevel: "strict", validationAction: "error",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "User account",
      required: ["user_id", "name", "email", "password_hash", "role", "created_at"],
      additionalProperties: true,
      properties: {
        user_id: {
          bsonType: "string",
          pattern: "^USR\\d+$",
          description: "Business id such as USR1001"
        },
        name: {
          bsonType: "string",
          minLength: 2,
          maxLength: 80
        },
        email: {
          bsonType: "string",
          pattern: "^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$"
        },
        password_hash: {
          bsonType: "string",
          minLength: 20
        },
        role: {
          enum: ["student", "admin"]
        },
        created_at: {
          bsonType: "date"
        }
      }
    }
  } });

db.runCommand({ collMod: "complaints", validationLevel: "strict", validationAction: "error",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "Campus complaint",
      required: ["complaint_id", "student_id", "title", "description", "location", "predicted_category", "predicted_urgency", "final_urgency", "status", "status_history", "created_at"],
      properties: {
        complaint_id: {
          bsonType: "string",
          pattern: "^CMP\\d+$"
        },
        student_id: {
          bsonType: "string",
          pattern: "^USR\\d+$"
        },
        student_name: {
          bsonType: "string"
        },
        title: {
          bsonType: "string",
          minLength: 5,
          maxLength: 120
        },
        description: {
          bsonType: "string",
          minLength: 10,
          maxLength: 2000
        },
        location: {
          enum: ["Central Library", "Hostel Block A", "Hostel Block B", "Hostel Block C", "Cafeteria", "Computer Lab", "Academic Block 1", "Academic Block 2", "Admin Block", "Auditorium", "Sports Complex", "Main Gate", "Parking Area"]
        },
        predicted_category: {
          enum: ["Network", "Electricity", "Water Supply", "Classroom Equipment", "Hostel Maintenance", "Cleanliness", "Security", "Other"]
        },
        category_confidence: {
          bsonType: "number",
          minimum: 0,
          maximum: 1
        },
        predicted_urgency: {
          enum: ["Low", "Medium", "High"]
        },
        urgency_confidence: {
          bsonType: "number",
          minimum: 0,
          maximum: 1
        },
        final_urgency: {
          enum: ["Low", "Medium", "High"],
          description: "Urgency actually used; equals the prediction unless an admin overrides it"
        },
        urgency_overridden: {
          bsonType: "bool"
        },
        status: {
          enum: ["Pending", "In Progress", "Resolved", "Rejected"]
        },
        assigned_department: {
          bsonType: ["string", "null"]
        },
        image_filename: {
          bsonType: ["string", "null"]
        },
        similar_complaints: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["complaint_id", "score"],
            properties: {
              complaint_id: {
                bsonType: "string"
              },
              score: {
                bsonType: "number"
              }
            }
          }
        },
        status_history: {
          bsonType: "array",
          minItems: 1,
          items: {
            bsonType: "object",
            required: ["status", "updated_at"],
            properties: {
              status: {
                enum: ["Pending", "In Progress", "Resolved", "Rejected"]
              },
              updated_at: {
                bsonType: "date"
              },
              updated_by: {
                bsonType: "string"
              },
              note: {
                bsonType: "string"
              }
            }
          }
        },
        created_at: {
          bsonType: "date"
        },
        updated_at: {
          bsonType: "date"
        },
        resolved_at: {
          bsonType: ["date", "null"]
        }
      }
    }
  } });

db.runCommand({ collMod: "departments", validationLevel: "strict", validationAction: "error",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "Department",
      required: ["department_name", "responsibility", "contact_email"],
      properties: {
        department_name: {
          bsonType: "string",
          minLength: 3,
          maxLength: 80
        },
        responsibility: {
          bsonType: "string",
          minLength: 5
        },
        contact_email: {
          bsonType: "string",
          pattern: "^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$"
        },
        categories: {
          bsonType: "array",
          items: {
            enum: ["Network", "Electricity", "Water Supply", "Classroom Equipment", "Hostel Maintenance", "Cleanliness", "Security", "Other"]
          }
        }
      }
    }
  } });

db.runCommand({ collMod: "feedback", validationLevel: "strict", validationAction: "error",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "Resolution feedback",
      required: ["complaint_id", "student_id", "rating", "created_at"],
      properties: {
        complaint_id: {
          bsonType: "string",
          pattern: "^CMP\\d+$"
        },
        student_id: {
          bsonType: "string",
          pattern: "^USR\\d+$"
        },
        rating: {
          bsonType: ["int", "long"],
          minimum: 1,
          maximum: 5
        },
        feedback: {
          bsonType: "string",
          maxLength: 500
        },
        created_at: {
          bsonType: "date"
        }
      }
    }
  } });


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

// 1. category_counts
// How many complaints per predicted category?   ($group + $sort)
db.complaints.aggregate([
  {
    $group: {
      _id: "$predicted_category",
      count: {
        $sum: 1
      }
    }
  },
  {
    $sort: {
      count: -1
    }
  }
]);

// 2. urgency_counts
// Distribution of the final urgency level.   ($group + $sort)
db.complaints.aggregate([
  {
    $group: {
      _id: "$final_urgency",
      count: {
        $sum: 1
      }
    }
  },
  {
    $sort: {
      count: -1
    }
  }
]);

// 3. location_category_matrix
// Complaint count for every (location, category) pair - feeds the heat-map.   ($group on a compound key)
db.complaints.aggregate([
  {
    $group: {
      _id: {
        location: "$location",
        category: "$predicted_category"
      },
      count: {
        $sum: 1
      }
    }
  },
  {
    $sort: {
      count: -1
    }
  }
]);

// 4. daily_trend
// Complaints submitted per day in the last N days.   ($match + $dateToString + $group + $sort)
db.complaints.aggregate([
  {
    $match: {
      created_at: {
        $gte: new Date(Date.now() - 30 * 24*60*60*1000)
      }
    }
  },
  {
    $group: {
      _id: {
        $dateToString: {
          format: "%Y-%m-%d",
          date: "$created_at"
        }
      },
      count: {
        $sum: 1
      }
    }
  },
  {
    $sort: {
      _id: 1
    }
  }
]);

// 5. department_performance
// Per department: total, resolved, resolution rate %, average hours to resolve.
//     ($match + $group with $cond / $avg + $addFields + $sort)
db.complaints.aggregate([
  {
    $match: {
      assigned_department: {
        $ne: null
      }
    }
  },
  {
    $group: {
      _id: "$assigned_department",
      total: {
        $sum: 1
      },
      resolved: {
        $sum: {
          $cond: [
            {
              $eq: ["$status", "Resolved"]
            },
            1,
            0
          ]
        }
      },
      avg_hours: {
        $avg: {
          $cond: [
            {
              $and: [
                {
                  $eq: ["$status", "Resolved"]
                },
                {
                  $ne: ["$resolved_at", null]
                }
              ]
            },
            {
              $divide: [
                {
                  $subtract: ["$resolved_at", "$created_at"]
                },
                3600000
              ]
            },
            "$$REMOVE"
          ]
        }
      }
    }
  },
  {
    $addFields: {
      resolution_rate: {
        $round: [
          {
            $multiply: [
              {
                $divide: ["$resolved", "$total"]
              },
              100
            ]
          },
          1
        ]
      },
      avg_hours: {
        $round: ["$avg_hours", 1]
      }
    }
  },
  {
    $sort: {
      resolution_rate: -1,
      total: -1
    }
  }
]);

// 6. recurring_issues
// Same category at the same location reported >= min_count times recently = recurring issue.
//     ($match + $group + $push + $match on the group result + $sort)
db.complaints.aggregate([
  {
    $match: {
      created_at: {
        $gte: new Date(Date.now() - 30 * 24*60*60*1000)
      },
      status: {
        $ne: "Rejected"
      }
    }
  },
  {
    $group: {
      _id: {
        category: "$predicted_category",
        location: "$location"
      },
      count: {
        $sum: 1
      },
      open_count: {
        $sum: {
          $cond: [
            {
              $in: [
                "$status",
                ["Pending", "In Progress"]
              ]
            },
            1,
            0
          ]
        }
      },
      first_reported: {
        $min: "$created_at"
      },
      last_reported: {
        $max: "$created_at"
      },
      complaint_ids: {
        $push: "$complaint_id"
      }
    }
  },
  {
    $match: {
      count: {
        $gte: 3
      }
    }
  },
  {
    $sort: {
      count: -1,
      last_reported: -1
    }
  }
]);

// 7. overdue_complaints
// Open complaints older than N days, oldest first.   ($match + $addFields + $project + $sort)
db.complaints.aggregate([
  {
    $match: {
      status: {
        $in: ["Pending", "In Progress"]
      },
      created_at: {
        $lt: new Date(Date.now() - 3 * 24*60*60*1000)
      }
    }
  },
  {
    $addFields: {
      age_days: {
        $round: [
          {
            $divide: [
              {
                $subtract: [new Date(), "$created_at"]
              },
              86400000
            ]
          },
          1
        ]
      }
    }
  },
  {
    $project: {
      _id: 0,
      complaint_id: 1,
      title: 1,
      location: 1,
      status: 1,
      final_urgency: 1,
      assigned_department: 1,
      age_days: 1
    }
  },
  {
    $sort: {
      age_days: -1
    }
  }
]);

// 8. feedback_by_department
// Average student rating per department by JOINING feedback with complaints.
//     ($lookup + $unwind + $group + $sort)  - run on the *feedback* collection
db.feedback.aggregate([
  {
    $lookup: {
      from: "complaints",
      localField: "complaint_id",
      foreignField: "complaint_id",
      as: "complaint"
    }
  },
  {
    $unwind: "$complaint"
  },
  {
    $group: {
      _id: {
        $ifNull: ["$complaint.assigned_department", "Unassigned"]
      },
      avg_rating: {
        $avg: "$rating"
      },
      responses: {
        $sum: 1
      }
    }
  },
  {
    $addFields: {
      avg_rating: {
        $round: ["$avg_rating", 2]
      }
    }
  },
  {
    $sort: {
      avg_rating: -1
    }
  }
]);

// 9. dashboard_summary
// Several small summaries in ONE round-trip.   ($facet)
db.complaints.aggregate([
  {
    $facet: {
      total: [
        {
          $count: "n"
        }
      ],
      by_status: [
        {
          $group: {
            _id: "$status",
            count: {
              $sum: 1
            }
          }
        }
      ],
      open_high: [
        {
          $match: {
            status: {
              $in: ["Pending", "In Progress"]
            },
            final_urgency: "High"
          }
        },
        {
          $count: "n"
        }
      ],
      overridden: [
        {
          $match: {
            urgency_overridden: true
          }
        },
        {
          $count: "n"
        }
      ]
    }
  }
]);

// 10. first_response_time_by_category
// Average hours from submission until the complaint first became 'In Progress'.
//     Digs into the embedded status_history array.   ($addFields + $filter + $arrayElemAt + $group)
db.complaints.aggregate([
  {
    $addFields: {
      first_progress: {
        $arrayElemAt: [
          {
            $filter: {
              input: "$status_history",
              as: "h",
              cond: {
                $eq: ["$$h.status", "In Progress"]
              }
            }
          },
          0
        ]
      }
    }
  },
  {
    $match: {
      first_progress: {
        $exists: true
      }
    }
  },
  {
    $group: {
      _id: "$predicted_category",
      avg_hours: {
        $avg: {
          $divide: [
            {
              $subtract: ["$first_progress.updated_at", "$created_at"]
            },
            3600000
          ]
        }
      },
      complaints: {
        $sum: 1
      }
    }
  },
  {
    $addFields: {
      avg_hours: {
        $round: ["$avg_hours", 1]
      }
    }
  },
  {
    $sort: {
      avg_hours: 1
    }
  }
]);

// 11. resolution_time_buckets
// Resolved complaints grouped into time buckets (<1 day, 1-3 days, 3-7 days, 7+ days).   ($match + $bucket)
db.complaints.aggregate([
  {
    $match: {
      status: "Resolved",
      resolved_at: {
        $ne: null
      }
    }
  },
  {
    $addFields: {
      hours: {
        $divide: [
          {
            $subtract: ["$resolved_at", "$created_at"]
          },
          3600000
        ]
      }
    }
  },
  {
    $bucket: {
      groupBy: "$hours",
      boundaries: [0, 24, 72, 168],
      default: "168+",
      output: {
        count: {
          $sum: 1
        }
      }
    }
  }
]);

// 12. top_reporters
// Students who filed the most complaints.   ($group + $sort + $limit)
db.complaints.aggregate([
  {
    $group: {
      _id: {
        student_id: "$student_id",
        name: "$student_name"
      },
      complaints: {
        $sum: 1
      }
    }
  },
  {
    $sort: {
      complaints: -1
    }
  },
  {
    $limit: 5
  }
]);
