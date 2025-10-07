from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = "your"   # secret for session management

# ------------------ Config ------------------
app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = "sada"          # change to your MySQL password
app.config['MYSQL_DATABASE'] = "speech_notes"

# ------------------ DB Connection ------------------
def get_db_connection():
    return mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DATABASE']
    )

# ------------------ Routes ------------------
@app.route('/')
def home():
    return redirect('/login')



@app.route('/index')
def index():
    if 'user_id' in session:
        return render_template("index.html", name=session['name'])
    else:
        return render_template("index.html",name="Guest")

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['name'] = user[1]
            flash("Login Successful!", "success")
            return redirect('/index')
        else:
            flash("Invalid Email or Password", "danger")
            return redirect('/login')

    return render_template("login.html")

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("Email already registered!", "warning")
        else:
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, password)
            )
            conn.commit()
            flash("Registration Successful! Please Login.", "success")

        cursor.close()
        conn.close()
        return redirect(url_for('login'))

    return render_template("register.html")

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect('/login')

# ------------------ Run ------------------
if __name__ == "__main__":
    app.run(debug=True)