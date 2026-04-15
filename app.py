from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os, io

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, silhouette_score

app = Flask(__name__)
CORS(app)

# ── Static files ──────────────────────────────────────────────
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# ── Users helpers ─────────────────────────────────────────────
def _load_users():
    if os.path.exists("users.json"):
        with open("users.json") as f:
            try: return json.load(f)
            except: return []
    return []

def _save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

# ── Results helpers ───────────────────────────────────────────
RESULTS_FILE = "class_results.json"

def _load_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            try: return json.load(f)
            except: return {}
    return {}

def _save_results(data):
    with open(RESULTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── Register ──────────────────────────────────────────────────
@app.route("/register", methods=["POST"])
def register():
    d        = request.json or {}
    username = d.get("username", "").strip()
    password = d.get("password", "").strip()
    email    = d.get("email",    "").strip()
    role     = d.get("role",     "student").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Missing username or password"})
    if role not in ("teacher", "student"):
        return jsonify({"success": False, "message": "Invalid role"})

    users = _load_users()
    if any(u["username"] == username for u in users):
        return jsonify({"success": False, "message": "Username already taken"})

    users.append({"username": username, "password": password, "email": email, "role": role})
    _save_users(users)
    return jsonify({"success": True, "message": f"{role.title()} account created!"})

# ── Teacher Login ─────────────────────────────────────────────
@app.route("/login", methods=["POST"])
def login():
    d        = request.json or {}
    username = d.get("username", "").strip()
    password = d.get("password", "").strip()
    if not username or not password:
        return jsonify({"success": False, "message": "Missing fields"})
    for u in _load_users():
        if u["username"] == username and u["password"] == password:
            return jsonify({"success": True, "username": username, "role": u.get("role", "student")})
    return jsonify({"success": False, "message": "Invalid username or password"})

# ── Student Login (by Student_ID from CSV results) ────────────
@app.route("/student_login", methods=["POST"])
def student_login():
    """
    Students log in with their Student_ID (e.g. S01).
    Looked up in class_results.json saved after teacher uploads CSV.
    """
    d          = request.json or {}
    student_id = d.get("student_id", "").strip().upper()

    if not student_id:
        return jsonify({"success": False, "message": "Please enter your Student ID"})

    results = _load_results()
    detail  = results.get("students_detail", [])

    if not detail:
        return jsonify({
            "success": False,
            "message": "No class data found yet. Ask your teacher to upload the CSV first."
        })

    match = next(
        (s for s in detail if str(s.get("id", "")).upper() == student_id),
        None
    )

    if not match:
        return jsonify({
            "success": False,
            "message": f"Student ID '{student_id}' not found in class data."
        })

    # Compute percentile rank by test score
    all_scores = [s.get("test", 0) for s in detail]
    my_score   = match.get("test", 0)
    percentile = round(sum(1 for s in all_scores if s < my_score) / max(len(all_scores), 1) * 100)

    # Leaderboard (top 10 by test score)
    leaderboard = sorted(detail, key=lambda x: x.get("test", 0), reverse=True)[:10]

    payload = {
        "success":       True,
        "student_id":    match["id"],
        "attendance":    match.get("attendance", 0),
        "assignment":    match.get("assignment", 0),
        "test":          match.get("test", 0),
        "participation": match.get("participation", 0),
        "category":      match.get("category", "Unknown"),
        "percentile":    percentile,
        "class_avg":     results.get("class_avg", {}),
        "total_students": results.get("total_students", len(detail)),
        "leaderboard":   leaderboard,
    }
    return jsonify(payload)

# ── Save / get results ────────────────────────────────────────
@app.route("/save_results", methods=["POST"])
def save_results():
    data = request.json or {}
    _save_results(data)
    return jsonify({"success": True})

@app.route("/get_results", methods=["GET"])
def get_results():
    return jsonify(_load_results())

# ── Student data (legacy — kept for compatibility) ────────────
@app.route("/student_data", methods=["POST"])
def student_data():
    d        = request.json or {}
    username = d.get("username", "").strip()
    results  = _load_results()
    detail   = results.get("students_detail", [])
    match = next(
        (s for s in detail if str(s.get("id", "")).lower() == username.lower()),
        None
    )
    if match:
        return jsonify({"found": True, "data": match})
    return jsonify({"found": False})

# ── Manual predict ─────────────────────────────────────────────
@app.route("/predict", methods=["POST"])
def predict():
    try:
        d    = request.json or {}
        att  = float(d.get("attendance",    0))
        asg  = float(d.get("assignment",    0))
        test = float(d.get("test",          0))
        part = float(d.get("participation", 0))
        avg  = (att + asg + test + part) / 4
        result = "Strong" if avg >= 75 else "Average" if avg >= 50 else "Weak"
        return jsonify({"result": result, "average": round(avg, 2)})
    except Exception as e:
        return jsonify({"error": str(e)})

# ── CSV upload + full ML pipeline ─────────────────────────────
@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"})
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Empty filename"})

        df = pd.read_csv(io.StringIO(file.stream.read().decode("utf-8")))
        required = {
            "Student_ID", "Attendance_Percentage",
            "Assignment_Submission_Rate", "Average_Test_Score", "Participation_Score"
        }
        if not required.issubset(df.columns):
            return jsonify({"error": f"Missing columns: {required - set(df.columns)}"})

        df = df.dropna().reset_index(drop=True)
        feature_cols = [
            "Attendance_Percentage", "Assignment_Submission_Rate",
            "Average_Test_Score", "Participation_Score"
        ]
        X        = df[feature_cols]
        scaler   = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        kmeans   = KMeans(n_clusters=3, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)
        df["Cluster"] = clusters

        means     = df.groupby("Cluster")["Average_Test_Score"].mean()
        sc        = means.sort_values(ascending=False).index.tolist()
        label_map = {sc[0]: "Strong", sc[1]: "Average", sc[2]: "Weak"}
        df["Category"] = df["Cluster"].map(label_map)

        dt_accuracy = None
        if len(df) >= 10:
            Xtr, Xte, ytr, yte = train_test_split(
                X_scaled, df["Cluster"], test_size=0.2, random_state=42
            )
            dt = DecisionTreeClassifier(random_state=42)
            dt.fit(Xtr, ytr)
            dt_accuracy = round(accuracy_score(yte, dt.predict(Xte)) * 100, 2)

        sil_score = None
        if len(df) > 3:
            sil_score = round(float(silhouette_score(X_scaled, clusters)), 4)

        counts        = df["Category"].value_counts().to_dict()
        weak_students = df[df["Category"] == "Weak"]["Student_ID"].tolist()
        student_names = df["Student_ID"].tolist()

        students_detail = (
            df[["Student_ID", "Attendance_Percentage", "Assignment_Submission_Rate",
                "Average_Test_Score", "Participation_Score", "Category"]]
            .rename(columns={
                "Student_ID":                "id",
                "Attendance_Percentage":     "attendance",
                "Assignment_Submission_Rate":"assignment",
                "Average_Test_Score":        "test",
                "Participation_Score":       "participation",
                "Category":                  "category",
            })
            .to_dict(orient="records")
        )

        cluster_profile = (
            df.groupby("Category")[feature_cols].mean()
            .round(2).reset_index().to_dict(orient="records")
        )

        payload = {
            "message":         "Analysis Complete",
            "total_students":  len(df),
            "counts":          counts,
            "weak_students":   weak_students,
            "students":        student_names,
            "students_detail": students_detail,
            "cluster_profile": cluster_profile,
            "dt_accuracy":     dt_accuracy,
            "silhouette":      sil_score,
            "class_avg": {
                "attendance":    round(df["Attendance_Percentage"].mean(), 1),
                "assignment":    round(df["Assignment_Submission_Rate"].mean(), 1),
                "test":          round(df["Average_Test_Score"].mean(), 1),
                "participation": round(df["Participation_Score"].mean(), 1),
            },
        }
        _save_results(payload)
        return jsonify(payload)

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    print("\n✅  InsightX running at http://127.0.0.1:5001")
    print("👩‍🏫  Teacher : username=teacher  password=teacher123")
    print("🎓  Students: enter Student ID (e.g. S01) on the login screen\n")
    app.run(host="0.0.0.0", port=5001, debug=True)
