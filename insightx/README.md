# InsightX — Student Behavior Analytics

AI-powered classroom analytics dashboard for teachers and students.

## GitHub Folder Structure

```
insightx/
├── app.py                          ← Main Flask app
├── student_routes.py               ← Student login/dashboard blueprint
├── requirements.txt                ← Python dependencies
├── render.yaml                     ← Render.com deploy config
├── .gitignore
├── sample_student_behavior_data.csv ← Default student data (50 students)
├── class_results.json              ← Cached ML results
├── users.json                      ← Teacher & student accounts
│
├── static/                         ← CSS, JS, images (Flask serves these)
│   ├── style.css
│   ├── script.js
│   └── 1.jpg
│
└── templates/                      ← All HTML templates (Flask renders these)
    ├── index.html                  ← Teacher login + dashboard
    ├── course.html
    ├── logout.html
    └── student/                    ← Student section templates
        ├── login.html
        └── dashboard.html
```

## Student Login Credentials (sample data)

Login at `/student/login` using:
- **Student ID**: S01 through S50
- **Name**: Full name from the CSV (e.g., S01 → Aarav Sharma)

## Teacher Login

Login at `/` using:
- **Username**: teacher
- **Password**: teacher123

## Local Development

```bash
pip install -r requirements.txt
python app.py
```
Then open http://localhost:10000

## Deploy to Render

1. Push all files to GitHub (keep exact folder structure above)
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — click **Deploy**
5. Done! Your app is live.

## Uploading Your Own Student CSV

CSV must have these exact column headers:
```
Student_ID, Attendance_Percentage, Assignment_Submission_Rate, Average_Test_Score, Participation_Score
```
Optionally add a `Name` column for student login by name.
