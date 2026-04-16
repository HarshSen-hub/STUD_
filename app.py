import os, io, json
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, silhouette_score

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "insightx-secret-key-change-me-in-production")
CORS(app)

# ── Register Student Blueprint ─────────────────────────────────
from student_routes import student_bp, get_student_record
app.register_blueprint(student_bp)


# ── File helpers ──────────────────────────────────────────────
USERS_FILE   = "users.json"
RESULTS_FILE = "class_results.json"
UPLOAD_DIR   = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            try:
                return json.load(f)
            except Exception:
                return default
    return default


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _load_users():   return _load_json(USERS_FILE, [])
def _save_users(u):  _save_json(USERS_FILE, u)
def _load_results(): return _load_json(RESULTS_FILE, {})
def _save_results(d):_save_json(RESULTS_FILE, d)


# ── Routes ─────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET"])
def login_page():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/get_results")
def get_results():
    return jsonify(_load_results())


# ── Auth ───────────────────────────────────────────────────────
@app.route("/register", methods=["POST"])
def register():
    d        = request.json or {}
    username = d.get("username", "").strip()
    password = d.get("password", "").strip()
    email    = d.get("email", "").strip()
    role     = d.get("role", "student").strip()

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


# ── Single Student Predict ─────────────────────────────────────
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


# ── CSV Upload & ML Analysis ───────────────────────────────────
@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"})
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Empty filename"})

        raw = file.stream.read().decode("utf-8")
        df  = pd.read_csv(io.StringIO(raw))

        # Normalize column names for matching
        df.columns = [c.strip() for c in df.columns]

        required = {"Student_ID", "Attendance_Percentage", "Assignment_Submission_Rate",
                    "Average_Test_Score", "Participation_Score"}
        missing = required - set(df.columns)
        if missing:
            return jsonify({"error": f"Missing columns: {missing}"})

        df = df.dropna(subset=list(required)).reset_index(drop=True)

        # Save uploaded file so student login can use it
        df.to_csv(os.path.join(UPLOAD_DIR, "student_data.csv"), index=False)

        feature_cols = ["Attendance_Percentage", "Assignment_Submission_Rate",
                        "Average_Test_Score", "Participation_Score"]
        X        = df[feature_cols]
        scaler   = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # KMeans clustering
        kmeans   = KMeans(n_clusters=3, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)
        df["Cluster"] = clusters

        means    = df.groupby("Cluster")["Average_Test_Score"].mean()
        sc       = means.sort_values(ascending=False).index.tolist()
        label_map = {sc[0]: "Strong", sc[1]: "Average", sc[2]: "Weak"}
        df["Category"] = df["Cluster"].map(label_map)

        # Decision Tree accuracy
        dt_accuracy = None
        if len(df) >= 10:
            Xtr, Xte, ytr, yte = train_test_split(X_scaled, df["Cluster"], test_size=0.2, random_state=42)
            dt = DecisionTreeClassifier(random_state=42)
            dt.fit(Xtr, ytr)
            dt_accuracy = round(accuracy_score(yte, dt.predict(Xte)) * 100, 2)

        # Silhouette score
        sil_score = None
        if len(df) > 3:
            sil_score = round(float(silhouette_score(X_scaled, clusters)), 4)

        counts       = df["Category"].value_counts().to_dict()
        weak_students = df[df["Category"] == "Weak"]["Student_ID"].tolist()
        student_names = df["Student_ID"].tolist()

        detail_cols = ["Student_ID", "Attendance_Percentage", "Assignment_Submission_Rate",
                       "Average_Test_Score", "Participation_Score", "Category"]
        students_detail = (df[detail_cols]
                           .rename(columns={
                               "Student_ID": "id",
                               "Attendance_Percentage": "attendance",
                               "Assignment_Submission_Rate": "assignment",
                               "Average_Test_Score": "test",
                               "Participation_Score": "participation",
                               "Category": "category"
                           }).to_dict(orient="records"))

        cluster_profile = (df.groupby("Category")[feature_cols].mean()
                           .round(2).reset_index().to_dict(orient="records"))

        payload = {
            "message":        "Analysis Complete",
            "total_students": len(df),
            "counts":         counts,
            "weak_students":  weak_students,
            "students":       student_names,
            "students_detail": students_detail,
            "cluster_profile": cluster_profile,
            "dt_accuracy":    dt_accuracy,
            "silhouette":     sil_score,
            "class_avg": {
                "attendance":    round(df["Attendance_Percentage"].mean(),        1),
                "assignment":    round(df["Assignment_Submission_Rate"].mean(),   1),
                "test":          round(df["Average_Test_Score"].mean(),           1),
                "participation": round(df["Participation_Score"].mean(),          1),
            }
        }
        _save_results(payload)
        return jsonify(payload)

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
