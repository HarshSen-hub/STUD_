// ================= LOGIN VALIDATION =================
function validateLogin() {
  const user = document.getElementById("username").value.trim();
  const pass = document.getElementById("password").value.trim();
  const msg = document.getElementById("msg");

  msg.textContent = "";

  // Empty check
  if (user === "" || pass === "") {
    msg.textContent = "⚠️ Please fill in all fields";
    msg.style.color = "#facc15";
    return;
  }

  // Loading state
  msg.textContent = "🔐 Authenticating...";
  msg.style.color = "#38bdf8";

  setTimeout(() => {
    if (user === "student" && pass === "1234") {
      msg.textContent = "✅ Login successful!";
      msg.style.color = "#22c55e";

      // Save session
      sessionStorage.setItem("isLoggedIn", "true");

      // Show dashboard (same page)
      setTimeout(() => {
        document.getElementById("loginPage").style.display = "none";
        document.getElementById("analysisPage").style.display = "block";
      }, 800);

    } else {
      msg.textContent = "❌ Invalid username or password";
      msg.style.color = "#ef4444";
    }
  }, 700);
}

// ================= PASSWORD TOGGLE =================
function togglePassword() {
  const p = document.getElementById("password");
  p.type = p.type === "password" ? "text" : "password";
}

// ================= GOOGLE LOGIN (DEMO) =================
function googleLogin() {
  window.open("https://accounts.google.com", "_blank");
}

// ================= ENTER KEY SUPPORT =================
document.addEventListener("keydown", function (e) {
  if (e.key === "Enter") {
    validateLogin();
  }
});

// ================= LOGOUT =================
function logout() {
  sessionStorage.clear();
  document.getElementById("analysisPage").style.display = "none";
  document.getElementById("loginPage").style.display = "grid";
}

// ================= PERFORMANCE PREDICTION =================
function predict() {
  const att = Number(document.getElementById("att").value);
  const asg = Number(document.getElementById("asg").value);
  const test = Number(document.getElementById("test").value);
  const part = Number(document.getElementById("part").value);
  const result = document.getElementById("result");

  if (!att || !asg || !test || !part) {
    result.textContent = "⚠️ Please fill all fields";
    result.style.color = "#facc15";
    return;
  }

  const score = (att + asg + test + part * 10) / 4;

  if (score >= 75) {
    result.textContent = "🟢 High Performer";
    result.style.color = "#22c55e";
  } else if (score >= 50) {
    result.textContent = "🟡 Average Performer";
    result.style.color = "#eab308";
  } else {
    result.textContent = "🔴 Needs Improvement";
    result.style.color = "#ef4444";
  }
}

// ================= PDF REPORT =================
function generatePDF() {
  const { jsPDF } = window.jspdf;
  const pdf = new jsPDF();

  pdf.setFontSize(16);
  pdf.text("Student Performance Report", 20, 20);

  pdf.setFontSize(12);
  pdf.text(`Attendance: ${att.value}%`, 20, 40);
  pdf.text(`Assignment: ${asg.value}%`, 20, 50);
  pdf.text(`Test Score: ${test.value}`, 20, 60);
  pdf.text(`Participation: ${part.value}`, 20, 70);
  pdf.text(`Result: ${result.textContent}`, 20, 90);

  pdf.save("Student_Report.pdf");
}
