
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import os
import pandas as pd

student_bp = Blueprint('student', __name__, url_prefix='/student', template_folder='templates')


DATA_FILE = os.path.join("uploads", "student_data.csv")
SAMPLE_FILE = "sample_student_behavior_data.csv"


def load_students():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    if os.path.exists(SAMPLE_FILE):
        return pd.read_csv(SAMPLE_FILE)
    return pd.DataFrame()


def compute_cluster(row):
    score = (
        float(row.get("attendance_percentage", 0)) * 0.25
        + float(row.get("assignment_submission_rate", 0)) * 0.25
        + float(row.get("avg_test_score", 0)) * 0.35
        + float(row.get("participation_score", 0)) * 0.15
    )
    if score >= 75:
        return "Strong"
    if score >= 50:
        return "Average"
    return "Weak"


def normalize_cols(df):
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df.rename(
        columns={
            "average_test_score": "avg_test_score",
            "student_name": "name",
        }
    )


def get_student_record(student_id):
    df = load_students()
    if df.empty:
        return None

    df = normalize_cols(df)

    required_cols = [
        "attendance_percentage",
        "assignment_submission_rate",
        "avg_test_score",
        "participation_score",
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0

    id_col = "student_id" if "student_id" in df.columns else "id"
    if id_col not in df.columns:
        return None

    match = df[
        df[id_col].astype(str).str.strip().str.upper()
        == str(student_id).strip().upper()
    ]
    if match.empty:
        return None

    row = match.iloc[0].to_dict()
    row["cluster"] = compute_cluster(row)

    df["avg_test_score"] = pd.to_numeric(df["avg_test_score"], errors="coerce")
    student_score = float(row.get("avg_test_score", 0))
    percentile = (
        round((df["avg_test_score"] < student_score).sum() / len(df) * 100)
        if len(df) > 0
        else 50
    )
    row["percentile"] = percentile

    row["class_avg_attendance"] = round(
        pd.to_numeric(df["attendance_percentage"], errors="coerce").mean(), 1
    )
    row["class_avg_test"] = round(
        pd.to_numeric(df["avg_test_score"], errors="coerce").mean(), 1
    )
    row["class_avg_assignment"] = round(
        pd.to_numeric(df["assignment_submission_rate"], errors="coerce").mean(), 1
    )
    row["class_avg_participation"] = round(
        pd.to_numeric(df["participation_score"], errors="coerce").mean(), 1
    )

    if "name" not in row or not row["name"]:
        row["name"] = f"Student {student_id}"

    return row


@student_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        name_input = request.form.get("name", "").strip().lower()

        student = get_student_record(student_id)
        if student:
            csv_name = str(student.get("name", "")).strip().lower()
            if csv_name and csv_name != f"student {student_id}".lower():
                if name_input != csv_name:
                    flash("Invalid Student ID or Name. Please try again.", "error")
                    return render_template("student/login.html")

            session["student_id"] = student_id
            session["student_name"] = student.get("name", f"Student {student_id}")
            return redirect(url_for("student.dashboard"))

        flash("Invalid Student ID. Please try again.", "error")

    return render_template("student/login.html")


@student_bp.route("/dashboard")
def dashboard():
    if "student_id" not in session:
        return redirect(url_for("student.login"))

    student = get_student_record(session["student_id"])
    if not student:
        session.clear()
        flash("Session expired. Please login again.", "error")
        return redirect(url_for("student.login"))

    return render_template("student/dashboard.html", student=student, announcements=[])


@student_bp.route("/logout")
def logout():
    session.pop("student_id", None)
    session.pop("student_name", None)
    flash("You have been successfully logged out.", "success")
    return redirect(url_for("student.login"))
