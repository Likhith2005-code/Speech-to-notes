from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.security import generate_password_hash
from datetime import timedelta

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "change-this-secret"
app.permanent_session_lifetime = timedelta(days=2)

# Minimal in-memory user store (replace with DB as needed)
USERS = {}

def is_authed():
    return "user_email" in session

@app.route("/")
def home():
    # If integrating with existing login, keep this guard or remove as desired
    if not is_authed():
        return redirect(url_for("login"))  # Provided by your existing code
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        confirm = request.form.get("confirm","")
        if not name or not email or not password:
            flash("All fields are required.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif email in USERS:
            flash("Email already registered.", "error")
        else:
            USERS[email] = {"name": name, "password": generate_password_hash(password)}
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))  # Existing login route
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# Optional: serve static explicitly
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# Health
@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(debug=True)