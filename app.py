import os
import io
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, silhouette_score

from student_routes import student_bp, get_student_record

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "insightx-secret-key-change-me-in-production")
CORS(app)

app.register_blueprint(student_bp)

USERS_FILE = "users.json"
RESULTS_FILE = "class_results.json"
UPLOAD_DIR = "uploads"
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


def _load_users():
    return _load_json(USERS_FILE, [])


def _save_users(users):
    _save_json(USERS_FILE, users)


def _load_results():
    return _load_json(RESULTS_FILE, {})


def _save_results(data):
    _save_json(RESULTS_FILE, data)


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


@app.route("/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    email = data.get("email", "").strip()
    role = data.get("role", "student").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Missing username or password"})
    if role not in ("teacher", "student"):
        return jsonify({"success": False, "message": "Invalid role"})

    users = _load_users()
    if any(user["username"] == username for user in users):
        return jsonify({"success": False, "message": "Username already taken"})

    users.append({
        "username": username,
        "password": password,
        "email": email,
        "role": role,
    })
    _save_users(users)
    return jsonify({"success": True, "message": f"{role.title()} account created!"})


@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Missing fields"})

    for user in _load_users():
        if user["username"] == username and user["password"] == password:
            return jsonify({
                "success": True,
                "username": username,
                "role": user.get("role", "student"),
            })

    return jsonify({"success": False, "message": "Invalid username or password"})


@app.route("/student_login", methods=["POST"])
def student_login():
    data = request.json or {}
    student_id = data.get("student_id", "").strip()

    if not student_id:
        return jsonify({"success": False, "message": "Student ID is required"})

    student = get_student_record(student_id)
    if not student:
        return jsonify({"success": False, "message": "Student ID not found"})

    results = _load_results()
    leaderboard = []
    if isinstance(results, dict):
        leaderboard = sorted(
            results.get("students_detail", []),
            key=lambda item: item.get("test", 0),
            reverse=True,
        )[:10]

    return jsonify({
        "success": True,
        "student_id": student_id,
        "name": student.get("name", f"Student {student_id}"),
        "category": student.get("cluster", "Unknown"),
        "percentile": student.get("percentile", 50),
        "attendance": round(float(student.get("attendance_percentage", 0)), 1),
        "assignment": round(float(student.get("assignment_submission_rate", 0)), 1),
        "test": round(float(student.get("avg_test_score", 0)), 1),
        "participation": round(float(student.get("participation_score", 0)), 1),
        "class_avg": {
            "attendance": student.get("class_avg_attendance"),
            "assignment": student.get("class_avg_assignment"),
            "test": student.get("class_avg_test"),
            "participation": student.get("class_avg_participation"),
        },
        "leaderboard": leaderboard,
    })


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json or {}
        attendance = float(data.get("attendance", 0))
        assignment = float(data.get("assignment", 0))
        test = float(data.get("test", 0))
        participation = float(data.get("participation", 0))

        average = (attendance + assignment + test + participation) / 4
        result = "Strong" if average >= 75 else "Average" if average >= 50 else "Weak"

        return jsonify({
            "result": result,
            "average": round(average, 2),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)})


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"})

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Empty filename"})

        raw = file.stream.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(raw))
        df.columns = [col.strip() for col in df.columns]

        required = {
            "Student_ID",
            "Attendance_Percentage",
            "Assignment_Submission_Rate",
            "Average_Test_Score",
            "Participation_Score",
        }
        missing = required - set(df.columns)
        if missing:
            return jsonify({"error": f"Missing columns: {missing}"})

        df = df.dropna(subset=list(required)).reset_index(drop=True)
        df.to_csv(os.path.join(UPLOAD_DIR, "student_data.csv"), index=False)

        feature_cols = [
            "Attendance_Percentage",
            "Assignment_Submission_Rate",
            "Average_Test_Score",
            "Participation_Score",
        ]

        X = df[feature_cols]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)
        df["Cluster"] = clusters

        means = df.groupby("Cluster")["Average_Test_Score"].mean()
        sorted_clusters = means.sort_values(ascending=False).index.tolist()
        label_map = {
            sorted_clusters[0]: "Strong",
            sorted_clusters[1]: "Average",
            sorted_clusters[2]: "Weak",
        }
        df["Category"] = df["Cluster"].map(label_map)

        dt_accuracy = None
        if len(df) >= 10:
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, df["Cluster"], test_size=0.2, random_state=42
            )
            model = DecisionTreeClassifier(random_state=42)
            model.fit(X_train, y_train)
            dt_accuracy = round(accuracy_score(y_test, model.predict(X_test)) * 100, 2)

        silhouette = None
        if len(df) > 3:
            silhouette = round(float(silhouette_score(X_scaled, clusters)), 4)

        counts = df["Category"].value_counts().to_dict()
        weak_students = df[df["Category"] == "Weak"]["Student_ID"].tolist()
        student_names = df["Student_ID"].tolist()

        detail_cols = [
            "Student_ID",
            "Attendance_Percentage",
            "Assignment_Submission_Rate",
            "Average_Test_Score",
            "Participation_Score",
            "Category",
        ]
        students_detail = (
            df[detail_cols]
            .rename(columns={
                "Student_ID": "id",
                "Attendance_Percentage": "attendance",
                "Assignment_Submission_Rate": "assignment",
                "Average_Test_Score": "test",
                "Participation_Score": "participation",
                "Category": "category",
            })
            .to_dict(orient="records")
        )

        cluster_profile = (
            df.groupby("Category")[feature_cols]
            .mean()
            .round(2)
            .reset_index()
            .to_dict(orient="records")
        )

        payload = {
            "message": "Analysis Complete",
            "total_students": len(df),
            "counts": counts,
            "weak_students": weak_students,
            "students": student_names,
            "students_detail": students_detail,
            "cluster_profile": cluster_profile,
            "dt_accuracy": dt_accuracy,
            "silhouette": silhouette,
            "class_avg": {
                "attendance": round(df["Attendance_Percentage"].mean(), 1),
                "assignment": round(df["Assignment_Submission_Rate"].mean(), 1),
                "test": round(df["Average_Test_Score"].mean(), 1),
                "participation": round(df["Participation_Score"].mean(), 1),
            },
        }

        _save_results(payload)
        return jsonify(payload)

    except Exception as exc:
        return jsonify({"error": str(exc)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)

