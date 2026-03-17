from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import json

app = Flask(__name__)
CORS(app)

# ================= LOAD DATASET =================
data = pd.read_csv("students.csv")

# Features and labels
X = data[['attendance','assignment','test','participation']]
y = data['result']

# Train ML model
model = RandomForestClassifier()
model.fit(X, y)


# ================= REGISTER API =================
@app.route("/register", methods=["POST"])
def register():

    data = request.json
    username = data["username"]
    password = data["password"]

    try:
        with open("users.json","r") as f:
            users = json.load(f)
    except:
        users = []

    users.append({
        "username": username,
        "password": password
    })

    with open("users.json","w") as f:
        json.dump(users, f)

    return jsonify({"message": "User registered successfully"})


# ================= LOGIN API =================
@app.route("/login", methods=["POST"])
def login():

    data = request.json
    username = data["username"]
    password = data["password"]

    try:
        with open("users.json","r") as f:
            users = json.load(f)
    except:
        users = []

    for user in users:
        if user["username"] == username and user["password"] == password:
            return jsonify({"success": True})

    return jsonify({"success": False})


# ================= PREDICTION API =================
@app.route("/predict", methods=["POST"])
def predict():

    data = request.json

    attendance = data["attendance"]
    assignment = data["assignment"]
    test = data["test"]
    participation = data["participation"]

    prediction = model.predict([[attendance, assignment, test, participation]])

    return jsonify({"result": prediction[0]})


# ================= RUN SERVER =================
if __name__ == "__main__":
    app.run(debug=True)