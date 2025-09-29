from flask import Flask, render_template, request, redirect, session,url_for
#import mysql.connector
from flask_mysqldb import MySQL
import os
app = Flask(__name__)
app.secret_key = 'Sada@2005'  # Use a secure key in production

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'sada'
app.config['MYSQL_DB'] = 'S2T'

mysql = MySQL(app)

# Landing route (Splash)
@app.route('/')
def index():
    if 'user' in session:
        return "hello"
    return redirect('/login')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        if user:
            session['user'] = user[1]
            return redirect('/home')
        else:
            #return "Invalid login credentials"
            return redirect('/')
    return render_template('login.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        euser = cursor.fetchone()
        if euser:
            return render_template('register.html',error="username already exits")
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        mysql.connection.commit()
        cursor.close()
        return redirect('/login')
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)