from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import pandas as pd
import json
import os

student_bp = Blueprint('student', __name__, url_prefix='/student')

DATA_FILE = 'uploads/student_data.csv'         # path to your uploaded CSV
ANNOUNCEMENTS_FILE = 'data/announcements.json' # shared with teacher portal


def load_students():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame()
    return pd.read_csv(DATA_FILE)


def get_announcements():
    if not os.path.exists(ANNOUNCEMENTS_FILE):
        return []
    with open(ANNOUNCEMENTS_FILE, 'r') as f:
        return json.load(f)


def compute_cluster(row):
    """
    Assign cluster label at runtime based on a composite score.
    Mirrors what your ML model does — adjust weights if needed.
    """
    score = (
        row['attendance_percentage'] * 0.25 +
        row['assignment_submission_rate'] * 0.25 +
        row['avg_test_score'] * 0.35 +
        row['participation_score'] * 0.15
    )
    if score >= 75:
        return 'Strong'
    elif score >= 50:
        return 'Average'
    else:
        return 'Weak'


def get_student_record(student_id, name):
    df = load_students()
    if df.empty:
        return None

    # Normalize columns
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    # Match student — ID + name as password (case-insensitive)
    match = df[
        (df['student_id'].astype(str).str.strip() == str(student_id).strip()) &
        (df['name'].str.strip().str.lower() == name.strip().lower())
    ]

    if match.empty:
        return None

    row = match.iloc[0].to_dict()

    # Assign cluster at runtime
    row['cluster'] = compute_cluster(row)

    # Compute percentile rank based on avg_test_score
    df['avg_test_score'] = pd.to_numeric(df['avg_test_score'], errors='coerce')
    student_score = float(row['avg_test_score'])
    percentile = round((df['avg_test_score'] < student_score).sum() / len(df) * 100)
    row['percentile'] = percentile

    # Class averages for comparison
    row['class_avg_attendance'] = round(df['attendance_percentage'].mean(), 1)
    row['class_avg_test'] = round(df['avg_test_score'].mean(), 1)
    row['class_avg_assignment'] = round(df['assignment_submission_rate'].mean(), 1)
    row['class_avg_participation'] = round(df['participation_score'].mean(), 1)

    return row


# ── Routes ──────────────────────────────────────────────

@student_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        name = request.form.get('name', '').strip()

        student = get_student_record(student_id, name)
        if student:
            session['student_id'] = student_id
            session['student_name'] = student['name']
            return redirect(url_for('student.dashboard'))
        else:
            flash('Invalid Student ID or Name. Please try again.', 'error')

    return render_template('student/login.html')


@student_bp.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('student.login'))

    student = get_student_record(session['student_id'], session['student_name'])
    if not student:
        session.clear()
        return redirect(url_for('student.login'))

    announcements = get_announcements()
    return render_template('student/dashboard.html', student=student, announcements=announcements)


@student_bp.route('/logout')
def logout():
    session.pop('student_id', None)
    session.pop('student_name', None)
    return redirect(url_for('student.login'))