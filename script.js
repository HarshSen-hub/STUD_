// ================================================================
//  InsightX — script.js  (single source of truth)
// ================================================================

const BASE_URL = "http://127.0.0.1:5001";

// ── shared chart refs ──────────────────────────────────────────
let myChart     = null;
let classChart  = null;
let clusterChart = null;

// ── students from CSV ──────────────────────────────────────────
let globalStudents       = [];
let globalStudentsDetail = [];


// ================================================================
//  LOGIN
// ================================================================
function validateLogin() {
  const user = document.getElementById("username").value.trim();
  const pass = document.getElementById("password").value.trim();
  const msg  = document.getElementById("msg");
  const btn  = document.querySelector(".login-btn");

  msg.textContent = "";

  if (!user || !pass) {
    msg.textContent = "Please fill in all fields";
    msg.style.color = "#facc15";
    return;
  }

  msg.textContent = "Authenticating…";
  msg.style.color = "#38bdf8";
  btn.disabled    = true;
  btn.innerText   = "Please wait…";

  setTimeout(() => {
    fetch(`${BASE_URL}/login`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ username: user, password: pass })
    })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        msg.textContent = "Login successful ✅";
        msg.style.color = "#22c55e";

        sessionStorage.setItem("isLoggedIn", "true");
        sessionStorage.setItem("username",   data.username || user);

        setTimeout(() => {
          document.querySelector(".flip-container").style.display = "none";
          document.getElementById("analysisPage").style.display   = "flex";
          setWelcome();
        }, 700);
      } else {
        msg.textContent = data.message || "Invalid username or password";
        msg.style.color = "#ef4444";
      }
      btn.disabled  = false;
      btn.innerText = "Log In";
    })
    .catch(() => {
      msg.textContent = "⚠️ Server not running — start app.py first";
      msg.style.color = "#facc15";
      btn.disabled  = false;
      btn.innerText = "Log In";
    });
  }, 500);
}


// ================================================================
//  REGISTER
// ================================================================
function registerUser() {
  const username = document.getElementById("regUser").value.trim();
  const email    = document.getElementById("regEmail").value.trim();
  const password = document.getElementById("regPass").value.trim();
  const msg      = document.getElementById("msg");

  if (!username || !email || !password) {
    msg.textContent = "Please fill all fields";
    msg.style.color = "#facc15";
    return;
  }

  fetch(`${BASE_URL}/register`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ username, email, password })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      msg.textContent = "Account created! Please log in.";
      msg.style.color = "#22c55e";
      document.getElementById("regUser").value = "";
      document.getElementById("regEmail").value = "";
      document.getElementById("regPass").value = "";
      setTimeout(() => flipCard(), 1200);
    } else {
      msg.textContent = data.message || "Registration failed";
      msg.style.color = "#ef4444";
    }
  })
  .catch(() => {
    msg.textContent = "⚠️ Server not running — start app.py first";
    msg.style.color = "#facc15";
  });
}


// ================================================================
//  WELCOME TEXT
// ================================================================
function setWelcome() {
  const name    = sessionStorage.getItem("username");
  const welcome = document.getElementById("welcomeText");
  if (welcome && name) {
    welcome.innerHTML = `Welcome back, <span style="color:#38bdf8">${name}</span>!`;
  }
}

window.addEventListener("load", setWelcome);


// ================================================================
//  LOGOUT
// ================================================================
function logout() {
  sessionStorage.clear();
  window.location.href = "logout.html";
}


// ================================================================
//  PASSWORD TOGGLE
// ================================================================
function togglePassword() {
  const p = document.getElementById("password");
  if (p) p.type = p.type === "password" ? "text" : "password";
}


// ================================================================
//  FLIP CARD
// ================================================================
function flipCard() {
  const card = document.getElementById("flipCard");
  if (card) card.classList.toggle("flipped");
}


// ================================================================
//  NAVIGATION
// ================================================================
function showPage(id) {
  ["analysisPage","aiPage","progressPage"].forEach(p => {
    const el = document.getElementById(p);
    if (el) el.style.display = "none";
  });
  const target = document.getElementById(id);
  if (target) target.style.display = "flex";
}

function openAI()          { showPage("aiPage");       }
function openProgress()    { showPage("progressPage"); fillStudentsDropdown(); loadProgressChart(); }
function backToDashboard() { showPage("analysisPage"); }


// ================================================================
//  ENTER KEY → LOGIN
// ================================================================
document.addEventListener("keydown", function(e) {
  const card = document.getElementById("flipCard");
  if (e.key === "Enter" && card && !card.classList.contains("flipped")) {
    validateLogin();
  }
});


// ================================================================
//  MANUAL PREDICT  (Dashboard page)
// ================================================================
function predict() {
  const att  = parseFloat(document.getElementById("att").value);
  const asg  = parseFloat(document.getElementById("asg").value);
  const test = parseFloat(document.getElementById("test").value);
  const part = parseFloat(document.getElementById("part").value);

  if (isNaN(att) || isNaN(asg) || isNaN(test) || isNaN(part)) {
    alert("Please fill all fields");
    return;
  }

  // Update top cards
  document.getElementById("attVal").innerText  = att  + "%";
  document.getElementById("asgVal").innerText  = asg  + "%";
  document.getElementById("testVal").innerText = test;

  // Send to Flask ML endpoint
  fetch(`${BASE_URL}/predict`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ attendance: att, assignment: asg, test: test, participation: part })
  })
  .then(r => r.json())
  .then(data => {
    const result = data.result || "Unknown";
    document.getElementById("result").innerText = result;

    // Mirror to AI page cards
    const weakArea = result === "Strong" ? "None" :
                     result === "Average" ? "Needs Practice" : "Low Scores";
    const rec      = result === "Strong" ? "Keep it up 🚀" :
                     result === "Average" ? "Focus on weak subjects" : "Study consistently daily";

    safeSet("aiPerformance",  result);
    safeSet("weakArea",       weakArea);
    safeSet("recommendation", rec);

    buildMyChart(att, asg, test);
  })
  .catch(() => {
    // Fallback local calc if server is down
    const avg = (att + asg + test) / 3;
    const result = avg >= 75 ? "Strong" : avg >= 50 ? "Average" : "Weak";
    document.getElementById("result").innerText = result;
    buildMyChart(att, asg, test);
  });
}

function safeSet(id, val) {
  const el = document.getElementById(id);
  if (el) el.innerText = val;
}


// ================================================================
//  PERFORMANCE BAR CHART  (Dashboard)
// ================================================================
function buildMyChart(att, asg, test) {
  const ctx = document.getElementById("myChart");
  if (!ctx) return;
  if (myChart) myChart.destroy();

  myChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Attendance", "Assignments", "Test Score"],
      datasets: [{
        label: "Your Scores",
        data: [att, asg, test],
        backgroundColor: ["#3b82f6aa", "#22c55eaa", "#a855f7aa"],
        borderColor:     ["#3b82f6",   "#22c55e",   "#a855f7"],
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true, max: 100, ticks: { color: "#94a3b8" } },
        x: { ticks: { color: "#94a3b8" } }
      },
      plugins: { legend: { labels: { color: "#e2e8f0" } } }
    }
  });
}


// ================================================================
//  CSV UPLOAD + FULL ML PIPELINE
// ================================================================
function uploadCSV() {
  const fileInput = document.getElementById("csvFile");
  const file      = fileInput.files[0];
  if (!file) { alert("Please select a CSV file"); return; }

  const loader = document.getElementById("loader");
  const status = document.getElementById("status");

  if (loader) loader.style.display = "flex";
  if (status) status.innerText = "Processing…";

  const formData = new FormData();
  formData.append("file", file);

  fetch(`${BASE_URL}/upload`, { method: "POST", body: formData })
  .then(r => r.json())
  .then(data => {
    if (loader) loader.style.display = "none";

    if (data.error) {
      if (status) status.innerText = "❌ " + data.error;
      return;
    }

    if (status) status.innerText =
      `✅ Analysis complete — ${data.total_students} students processed`;

    globalStudents       = data.students        || [];
    globalStudentsDetail = data.students_detail  || [];

    const counts = data.counts || {};
    showClassChart(counts["Weak"] || 0, counts["Average"] || 0, counts["Strong"] || 0);
    showWeakStudents(data.weak_students || []);
    showMLStats(data);

    if (data.cluster_profile && data.cluster_profile.length) {
      showClusterProfile(data.cluster_profile);
    }

    fileInput.value = "";
  })
  .catch(err => {
    if (loader) loader.style.display = "none";
    if (status) status.innerText = "❌ Error — is the server running?";
    console.error(err);
  });
}


// ================================================================
//  ML STATS BANNER
// ================================================================
function showMLStats(data) {
  let el = document.getElementById("mlStats");
  if (!el) {
    el = document.createElement("div");
    el.id = "mlStats";
    el.style.cssText = `
      background:#020617; border-radius:12px; padding:18px 24px;
      margin-top:20px; display:flex; gap:30px; flex-wrap:wrap;
      border:1px solid #1e293b;
    `;
    const statusEl = document.getElementById("status");
    if (statusEl) statusEl.parentNode.insertBefore(el, statusEl.nextSibling);
  }

  const sil = data.silhouette != null
    ? `<span style="color:#22c55e">${data.silhouette}</span>` : "N/A";
  const acc = data.dt_accuracy != null
    ? `<span style="color:#38bdf8">${data.dt_accuracy}%</span>` : "N/A";

  el.innerHTML = `
    <div><p style="color:#64748b;font-size:11px;margin:0">ALGORITHM</p>
         <p style="color:#e2e8f0;font-weight:600;margin:4px 0">K-Means (k=3) + Decision Tree</p></div>
    <div><p style="color:#64748b;font-size:11px;margin:0">SILHOUETTE SCORE</p>
         <p style="font-weight:600;margin:4px 0;font-size:18px">${sil}</p></div>
    <div><p style="color:#64748b;font-size:11px;margin:0">CLASSIFIER ACCURACY</p>
         <p style="font-weight:600;margin:4px 0;font-size:18px">${acc}</p></div>
    <div><p style="color:#64748b;font-size:11px;margin:0">TOTAL STUDENTS</p>
         <p style="color:#e2e8f0;font-weight:600;margin:4px 0;font-size:18px">${data.total_students}</p></div>
  `;
}


// ================================================================
//  CLASS PIE CHART
// ================================================================
function showClassChart(weak, avg, strong) {
  const ctx = document.getElementById("classChart");
  if (!ctx) return;
  if (classChart) classChart.destroy();

  classChart = new Chart(ctx, {
    type: "pie",
    data: {
      labels: ["Weak", "Average", "Strong"],
      datasets: [{
        data: [weak, avg, strong],
        backgroundColor: ["#991b1b", "#1e3a8a", "#166534"],
        borderColor: "#0f172a",
        borderWidth: 4,
        hoverOffset: 15
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#e5e7eb", font: { size: 14, weight: "bold" } } },
        tooltip: {
          callbacks: {
            label(context) {
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const pct   = ((context.raw / total) * 100).toFixed(1);
              return `${context.label}: ${context.raw} students (${pct}%)`;
            }
          }
        }
      },
      animation: { animateRotate: true, duration: 1200 }
    }
  });
}


// ================================================================
//  CLUSTER PROFILE BAR CHART
// ================================================================
function showClusterProfile(profile) {
  let container = document.getElementById("clusterProfileSection");
  if (!container) {
    container = document.createElement("section");
    container.id        = "clusterProfileSection";
    container.className = "analysis-box";
    container.innerHTML = `
      <h3>📊 Cluster Profile — Average Scores per Category</h3>
      <canvas id="clusterChart"></canvas>
    `;
    const classBox = document.getElementById("classChart");
    if (classBox) classBox.closest(".analysis-box").insertAdjacentElement("afterend", container);
  }

  const ctx = document.getElementById("clusterChart");
  if (!ctx) return;
  if (clusterChart) clusterChart.destroy();

  const labels      = ["Attendance %", "Assignment %", "Test Score", "Participation"];
  const featureKeys = ["Attendance_Percentage","Assignment_Submission_Rate","Average_Test_Score","Participation_Score"];
  const colors      = { Strong: "#22c55e", Average: "#3b82f6", Weak: "#ef4444" };

  clusterChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: profile.map(cat => ({
        label: cat.Category,
        data:  featureKeys.map(k => cat[k]),
        backgroundColor: (colors[cat.Category] || "#94a3b8") + "aa",
        borderColor:      colors[cat.Category] || "#94a3b8",
        borderWidth: 2
      }))
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true, max: 100, ticks: { color: "#94a3b8" } },
        x: { ticks: { color: "#94a3b8" } }
      },
      plugins: { legend: { labels: { color: "#e2e8f0" } } }
    }
  });
}


// ================================================================
//  WEAK STUDENTS LIST
// ================================================================
function showWeakStudents(list) {
  const ul = document.getElementById("weakList");
  if (!ul) return;
  ul.innerHTML = "";

  if (!list.length) {
    ul.innerHTML = "<li style='color:lightgreen'>No weak students 🎉</li>";
    return;
  }

  list.forEach(name => {
    const li = document.createElement("li");
    li.innerText   = name;
    li.style.cssText = "color:#ef4444; font-weight:bold; margin:6px 0;";
    ul.appendChild(li);
  });
}


// ================================================================
//  PROGRESS PAGE
// ================================================================
function fillStudentsDropdown() {
  const dropdown = document.getElementById("studentSelect");
  if (!dropdown) return;
  dropdown.innerHTML = `<option value="">Select Student</option>`;
  globalStudents.forEach(name => {
    const opt       = document.createElement("option");
    opt.value       = name;
    opt.textContent = name;
    dropdown.appendChild(opt);
  });
}

function saveProgress() {
  const student = document.getElementById("studentSelect").value;
  const math    = Number(document.getElementById("math").value);
  const dbms    = Number(document.getElementById("dbms").value);
  const os      = Number(document.getElementById("os").value);

  if (!student)                              { alert("Select a student"); return; }
  if (isNaN(math) || isNaN(dbms) || isNaN(os)) { alert("Fill all fields"); return; }

  const detail   = globalStudentsDetail.find(s => s.id === student);
  const category = detail ? detail.category : "N/A";

  const catEl = document.getElementById("progressStudentCategory");
  if (catEl) catEl.textContent = `ML Category: ${category}`;

  localStorage.setItem("progressData", JSON.stringify({ student, math, dbms, os }));
  loadProgressChart();
}

let progressChart = null;

function loadProgressChart() {
  const ctx    = document.getElementById("progressChart");
  if (!ctx) return;
  const stored = JSON.parse(localStorage.getItem("progressData"));
  if (!stored) return;

  if (progressChart) { progressChart.destroy(); progressChart = null; }

  progressChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Math", "DBMS", "OS"],
      datasets: [{
        label: stored.student || "Student",
        data:  [stored.math, stored.dbms, stored.os],
        backgroundColor: ["#3b82f6aa", "#22c55eaa", "#a855f7aa"],
        borderColor:     ["#3b82f6",   "#22c55e",   "#a855f7"],
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true, max: 100, ticks: { color: "#94a3b8" } },
        x: { ticks: { color: "#94a3b8" } }
      },
      plugins: { legend: { labels: { color: "#e2e8f0" } } }
    }
  });
}
