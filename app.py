from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import os
import wave
import subprocess
import youtube_dl
from vosk import Model, KaldiRecognizer
import json
import sounddevice as sd
import numpy as np

app = Flask(__name__)
app.secret_key = "your"

# ------------------ Config ------------------
app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = "sada"  # change to your MySQL password
app.config['MYSQL_DATABASE'] = "speech_notes"

# ------------------ DB Connection ------------------
def get_db_connection():
    return mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DATABASE']
    )

# ------------------ Vosk Model ------------------
if not os.path.exists("vosk-model"):
    raise Exception("Please download the Vosk English model and place it in the folder 'vosk-model'")
model = Model("vosk-model")

def transcribe_wav(file_path):
    wf = wave.open(file_path, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        # Convert to correct format using ffmpeg
        new_path = "temp.wav"
        subprocess.call(["ffmpeg", "-y", "-i", file_path, "-ar", "16000", "-ac", "1", new_path])
        wf = wave.open(new_path, "rb")

    rec = KaldiRecognizer(model, wf.getframerate())
    result_text = ""
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            result_text += res.get("text", "") + " "
    res = json.loads(rec.FinalResult())
    result_text += res.get("text", "")
    return result_text.strip()

def transcribe_microphone(duration=5, samplerate=16000):
    print("Recording...")
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()
    rec = KaldiRecognizer(model, samplerate)
    rec.AcceptWaveform(recording.tobytes())
    res = json.loads(rec.Result())
    res_final = json.loads(rec.FinalResult())
    return (res.get("text", "") + " " + res_final.get("text", "")).strip()

def transcribe_youtube(url):
    ydl_opts = {'format': 'bestaudio/best', 'outtmpl': 'video.%(ext)s', 'quiet': True}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        video_file = ydl.prepare_filename(info_dict)
        # Convert video to WAV
        wav_file = "video.wav"
        subprocess.call(["ffmpeg", "-y", "-i", video_file, "-ar", "16000", "-ac", "1", wav_file])
        return transcribe_wav(wav_file)

# ------------------ Routes ------------------
@app.route('/')
def home():
    return redirect('/login')

@app.route('/index')
def index():
    if 'user_id' in session:
        return render_template("index.html", name=session['name'])
    else:
        return render_template("index.html", name="Guest")

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

@app.route('/transcribe', methods=["POST"])
def transcribe():
    input_type = request.form.get("input_type")
    result = ""
    try:
        if input_type == "microphone":
            duration = int(request.form.get("duration", 5))
            result = transcribe_microphone(duration)
        elif input_type == "file":
            file = request.files['file']
            file.save(file.filename)
            result = transcribe_wav(file.filename)
        elif input_type == "youtube":
            url = request.form.get("youtube_url")
            result = transcribe_youtube(url)
        else:
            result = "Invalid input type"
    except Exception as e:
        result = f"Error: {str(e)}"
    return jsonify({"transcription": result})

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
if __name__== "__main__":
    app.run(debug=True)