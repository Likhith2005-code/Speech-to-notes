import os
import wave
import json
import time
import tempfile
import subprocess
import fitz  # PyMuPDF
import shutil
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import mysql.connector
import requests
from vosk import Model, KaldiRecognizer

try:
    import yt_dlp as youtube_dl
except ImportError:
    raise ImportError("Please install yt_dlp via: pip install yt-dlp")

load_dotenv()
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "super-secret"

# MySQL Config
app.config.update(
    MYSQL_HOST="localhost",
    MYSQL_USER="root",
    MYSQL_PASSWORD="sada",
    MYSQL_DATABASE="speech_notes"
)

def get_db_connection():
    return mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DATABASE']
    )

# ------------------ Load Vosk Model ------------------
if not os.path.exists("vosk-model"):
    raise Exception("Please place Vosk model in 'vosk-model'.")
model = Model("vosk-model")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ------------------ Helpers ------------------
def safe_temp_filename(suffix=""):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path

def convert_to_wav(input_path):
    wav_path = safe_temp_filename(".wav")
    cmd = ["ffmpeg", "-y", "-i", input_path, "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", wav_path]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wav_path

def transcribe_wav(path):
    wf = wave.open(path, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())
    result = []
    while True:
        data = wf.readframes(4000)
        if not data:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            if res.get("text"):
                result.append(res["text"])
    res = json.loads(rec.FinalResult())
    if res.get("text"):
        result.append(res["text"])
    wf.close()
    return " ".join(result).strip()

def transcribe_any(input_path):
    wav = convert_to_wav(input_path)
    text = transcribe_wav(wav)
    os.remove(wav)
    return text

def transcribe_youtube(url):
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, "yt_audio.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out,
        "noplaylist": True,
        "quiet": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}],
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        base = ydl.prepare_filename(info)
        audio_file = os.path.splitext(base)[0] + ".m4a"
    text = transcribe_any(audio_file)
    shutil.rmtree(tmp, ignore_errors=True)
    return text

def extract_pdf_text(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text("text") + "\n"
    doc.close()
    return text.strip()

# ------------------ OpenAI ------------------
def build_prompt(transcription, note_type):
    note_type = note_type.lower()
    mapping = {
        "normal": "Convert into clear, readable notes.",
        "detailed": "Convert into detailed, structured notes with key points and examples.",
        "bullet": "Convert into short bullet points.",
        "summary": "Summarize in 2–4 sentences."
    }
    instruction = mapping.get(note_type, mapping["normal"])
    return f"{instruction}\n\nTranscription:\n\"\"\"\n{transcription}\n\"\"\"\n\nNotes:"

def call_openai(prompt):
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY not set.")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a note formatting assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 800
    }
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        raise Exception(f"OpenAI error: {res.text}")
    return res.json()["choices"][0]["message"]["content"].strip()

# ------------------ Routes ------------------
@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email, password = request.form['email'], request.form['password']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cur.fetchone()
        conn.close()
        if user:
            session['user_id'], session['name'] = user[0], user[1]
            return redirect('/index')
        flash("Invalid credentials.")
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

@app.route('/index')
def index():
    name = session.get('name', 'Guest')
    return render_template("index.html", name=name)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    input_type = request.form.get("input_type")
    result = ""
    temp_file = None
    try:
        if input_type in ["microphone", "file"]:
            file = request.files['file']
            temp_file = safe_temp_filename(os.path.splitext(file.filename)[1])
            file.save(temp_file)
            result = transcribe_any(temp_file)
        elif input_type == "youtube":
            result = transcribe_youtube(request.form.get("youtube_url"))
        elif input_type == "pdf":
            file = request.files['file']
            temp_file = safe_temp_filename(".pdf")
            file.save(temp_file)
            result = extract_pdf_text(temp_file)
        else:
            return jsonify({"error": "Invalid input type."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

    session['transcription'] = result
    return jsonify({"transcription": result})

@app.route('/generate_notes', methods=['POST'])
def generate_notes():
    note_type = request.form.get("note_type")
    text = request.form.get("transcription") or session.get("transcription", "")
    if not text:
        return jsonify({"error": "No text to process."}), 400
    try:
        prompt = build_prompt(text, note_type)
        notes = call_openai(prompt)
        return jsonify({"notes": notes})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

if __name__ == "__main__":
    app.run(debug=True)