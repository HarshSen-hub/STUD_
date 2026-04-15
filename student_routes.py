from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import pandas as pd
import os

# IMPORTANT: Correct template folder for Render
student_bp = Blueprint('student', __name__, 
                       url_prefix='/student',
                       template_folder='../templates/student')

DATA_FILE = 'uploads/student_data.csv'

def load_students():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    elif os.path.exists('sample_student_behavior_data.csv'):
        return pd.read_csv('sample_student_behavior_data.csv')
    return pd.DataFrame()

def compute_cluster(row):
    score = (
        float(row.get('attendance_percentage', 0)) * 0.25 +
        float(row.get('assignment_submission_rate', 0)) * 0.25 +
        float(row.get('avg_test_score', 0)) * 0.35 +
        float(row.get('participation_score', 0)) * 0.15
    )
    if score >= 75:
        return 'Strong'
    elif score >= 50:
        return 'Average'
    else:
        return 'Weak'

def get_student_record(student_id):
    """Simplified: Login with Student ID only"""
    df = load_students()
    if df.empty:
        return None

    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    # Match only by Student_ID
    match = df[df['student_id'].astype(str).str.strip() == str(student_id).strip()]
    if match.empty:
        return None

    row = match.iloc[0].to_dict()
    row['cluster'] = compute_cluster(row)

    # Percentile
    df['avg_test_score'] = pd.to_numeric(df['avg_test_score'], errors='coerce')
    student_score = float(row.get('avg_test_score', 0))
    percentile = round((df['avg_test_score'] < student_score).sum() / len(df) * 100) if len(df) > 0 else 50
    row['percentile'] = percentile

    # Class averages
    row['class_avg_attendance'] = round(df['attendance_percentage'].mean(), 1)
    row['class_avg_test'] = round(df['avg_test_score'].mean(), 1)
    row['class_avg_assignment'] = round(df['assignment_submission_rate'].mean(), 1)
    row['class_avg_participation'] = round(df['participation_score'].mean(), 1)

    return row


# ====================== ROUTES ======================

@student_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()

        student = get_student_record(student_id)
        if student:
            session['student_id'] = student_id
            session['student_name'] = student.get('name', f"Student {student_id}")
            return redirect(url_for('student.dashboard'))
        else:
            flash('Invalid Student ID. Please try again.', 'error')

    return render_template('student/login.html')


@student_bp.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('student.login'))

    student = get_student_record(session['student_id'])
    if not student:
        session.clear()
        flash('Session expired. Please login again.', 'error')
        return redirect(url_for('student.login'))

    return render_template('student/dashboard.html', student=student, announcements=[])


@student_bp.route('/logout')
def logout():
    session.pop('student_id', None)
    session.pop('student_name', None)
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('student.login'))
