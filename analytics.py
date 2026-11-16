"""Builds the Plotly charts and report tables for the admin dashboard from aggregation results."""
import json

import plotly.graph_objects as go

from config import CATEGORIES, LOCATIONS, URGENCY_LEVELS, Config
from database import aggregations as agg

URGENCY_COLORS = {"Low": "#2e9e5b", "Medium": "#f0ad2b", "High": "#d9534f"}


def _fig_to_dict(fig, height=320):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=40, r=20, t=40, b=40),
                      font=dict(size=12), title_font=dict(size=15))
    return json.loads(fig.to_json())


def build_dashboard():
    cat = agg.run(agg.category_counts())
    urg = {r["_id"]: r["count"] for r in agg.run(agg.urgency_counts())}
    matrix_rows = agg.run(agg.location_category_matrix())
    trend = agg.run(agg.daily_trend(30))
    dept = agg.run(agg.department_performance())
    recurring = agg.run(agg.recurring_issues(Config.RECURRING_WINDOW_DAYS, Config.RECURRING_MIN_COUNT))
    overdue = agg.run(agg.overdue_complaints(Config.OVERDUE_AFTER_DAYS))
    feedback = agg.run(agg.feedback_by_department(), "feedback")
    first_resp = agg.run(agg.first_response_time_by_category())

    charts = {}
    charts["category"] = _fig_to_dict(go.Figure(
        go.Bar(x=[r["_id"] for r in cat], y=[r["count"] for r in cat], marker_color="#3b6fd4"),
        layout=dict(title="Complaints by category")))
    charts["urgency"] = _fig_to_dict(go.Figure(
        go.Pie(labels=URGENCY_LEVELS, values=[urg.get(u, 0) for u in URGENCY_LEVELS], hole=0.5,
               marker=dict(colors=[URGENCY_COLORS[u] for u in URGENCY_LEVELS]), sort=False),
        layout=dict(title="Urgency distribution")))

    z = [[0] * len(CATEGORIES) for _ in LOCATIONS]
    for r in matrix_rows:
        z[LOCATIONS.index(r["_id"]["location"])][CATEGORIES.index(r["_id"]["category"])] = r["count"]
    charts["heatmap"] = _fig_to_dict(go.Figure(
        go.Heatmap(z=z, x=CATEGORIES, y=LOCATIONS, colorscale="YlOrRd", hovertemplate="%{y}<br>%{x}: %{z}<extra></extra>"),
        layout=dict(title="Complaint heat-map: location x category")), height=430)

    charts["trend"] = _fig_to_dict(go.Figure(
        go.Scatter(x=[r["_id"] for r in trend], y=[r["count"] for r in trend], mode="lines+markers",
                   line=dict(color="#3b6fd4")),
        layout=dict(title="Complaints per day (last 30 days)")))

    hours = [d for d in dept if d.get("avg_hours") is not None]
    charts["dept_hours"] = _fig_to_dict(go.Figure(
        go.Bar(x=[d["_id"] for d in hours], y=[d["avg_hours"] for d in hours], marker_color="#6c4fc4"),
        layout=dict(title="Average resolution time by department (hours)")))

    return {
        "numbers": agg.summary_numbers(),
        "charts": charts,
        "departments": dept,
        "recurring": recurring,
        "overdue": overdue[:10],
        "overdue_total": len(overdue),
        "feedback": feedback,
        "first_response": first_resp,
    }
