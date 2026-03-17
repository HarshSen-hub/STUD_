// ================= LOGIN VALIDATION =================
function validateLogin() {
  const user = document.getElementById("username").value.trim();
  const pass = document.getElementById("password").value.trim();
  const msg = document.getElementById("msg");

  msg.textContent = "";

  if (user === "" || pass === "") {
    msg.textContent = "⚠️ Please fill in all fields";
    msg.style.color = "#facc15";
    return;
  }

  msg.textContent = "🔐 Authenticating...";
  msg.style.color = "#38bdf8";

  setTimeout(() => {

    fetch("http://127.0.0.1:5000/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        username: user,
        password: pass
      })
    })

    .then(response => response.json())
    .then(data => {

      if (data.success) {

        msg.textContent = "✅ Login successful!";
        msg.style.color = "#22c55e";

        sessionStorage.setItem("isLoggedIn", "true");

        setTimeout(() => {
          document.getElementById("loginPage").style.display = "none";
          document.getElementById("analysisPage").style.display = "flex";
        }, 800);

      } else {

        msg.textContent = "❌ Invalid username or password";
        msg.style.color = "#ef4444";

      }

    });

  }, 700);
}


// ================= REGISTER USER =================
function registerUser() {

  const username = document.getElementById("regUser").value.trim();
  const password = document.getElementById("regPass").value.trim();
  const msg = document.getElementById("msg");

  if (username === "" || password === "") {
    msg.textContent = "⚠️ Fill all register fields";
    msg.style.color = "#facc15";
    return;
  }

  fetch("http://127.0.0.1:5000/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      username: username,
      password: password
    })
  })

  .then(response => response.json())
  .then(data => {

    msg.textContent = "✅ Registered successfully. You can login now.";
    msg.style.color = "#22c55e";

    document.getElementById("regUser").value = "";
    document.getElementById("regPass").value = "";

  });

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
  if (e.key === "Enter" && document.getElementById("loginPage").style.display !== "none") {
    validateLogin();
  }
});


// ================= LOGOUT =================
function logout() {
  sessionStorage.clear();
  document.getElementById("analysisPage").style.display = "none";
  document.getElementById("documentsPage").style.display = "none";
  document.getElementById("loginPage").style.display = "grid";
}


// ================= PERFORMANCE PREDICTION =================
function predict() {
  const att = Number(document.getElementById("att").value);
  const asg = Number(document.getElementById("asg").value);
  const test = Number(document.getElementById("test").value);
  const part = Number(document.getElementById("part").value);

  const result = document.getElementById("result");

  if (isNaN(att) || isNaN(asg) || isNaN(test) || isNaN(part)) {
    result.textContent = "⚠️ Fill all fields";
    result.style.color = "#facc15";
    return;
  }

  document.getElementById("attVal").textContent = att + "%";
  document.getElementById("asgVal").textContent = asg + "%";
  document.getElementById("testVal").textContent = test;

  fetch("http://127.0.0.1:5000/predict", {

    method: "POST",

    headers: {
      "Content-Type": "application/json"
    },

    body: JSON.stringify({
      attendance: att,
      assignment: asg,
      test: test,
      participation: part
    })

  })

  .then(response => response.json())
  .then(data => {

    result.textContent = data.result;

    if (data.result === "Needs Improvement") {
      setTimeout(() => {
        window.location.href = "improvement.html";
      }, 1500);
    }

  });
}


// ================= PDF REPORT =================
function generatePDF() {
  const { jsPDF } = window.jspdf;
  const pdf = new jsPDF();

  pdf.setFontSize(16);
  pdf.text("Student Performance Report", 20, 20);

  pdf.setFontSize(12);
  pdf.text(`Attendance: ${document.getElementById("att").value}%`, 20, 40);
  pdf.text(`Assignment: ${document.getElementById("asg").value}%`, 20, 50);
  pdf.text(`Test Score: ${document.getElementById("test").value}`, 20, 60);
  pdf.text(`Participation: ${document.getElementById("part").value}`, 20, 70);
  pdf.text(`Result: ${document.getElementById("result").textContent}`, 20, 90);

  pdf.save("Student_Performance_Report.pdf");
}


// ================= DOCUMENTS NAVIGATION =================
function openDocuments() {
  document.getElementById("analysisPage").style.display = "none";
  document.getElementById("documentsPage").style.display = "flex";
}

function backToDashboard() {
  document.getElementById("documentsPage").style.display = "none";
  document.getElementById("analysisPage").style.display = "flex";
}


// ================= AUTO LOGIN CHECK =================
window.onload = () => {
  if (sessionStorage.getItem("isLoggedIn") === "true") {
    document.getElementById("loginPage").style.display = "none";
    document.getElementById("analysisPage").style.display = "flex";
  }
};