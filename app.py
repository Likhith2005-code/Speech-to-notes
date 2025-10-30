# app.py
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
import requests  # used to call OpenAI API
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
app = Flask(__name__)
app.secret_key = "your-secret-key-here"  # replace with a stronger secret in production

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

# ------------------ Helper: Transcription functions ------------------
def transcribe_wav(file_path):
    """
    Ensure WAV is 16kHz mono 16-bit; convert with ffmpeg if not.
    Uses Vosk KaldiRecognizer to produce transcription text.
    """
    wf = wave.open(file_path, "rb")
    # If audio not in expected format, convert to temporary 16kHz mono, 16-bit WAV
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE" or wf.getframerate() != 16000:
        new_path = f"temp_{int(time.time())}.wav"
        subprocess.call(["ffmpeg", "-y", "-i", file_path, "-ar", "16000", "-ac", "1", new_path])
        wf.close()
        wf = wave.open(new_path, "rb")

    rec = KaldiRecognizer(model, wf.getframerate())
    result_text = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            if res.get("text"):
                result_text.append(res.get("text"))
    res = json.loads(rec.FinalResult())
    if res.get("text"):
        result_text.append(res.get("text"))
    wf.close()
    return " ".join(result_text).strip()

def transcribe_microphone(duration=5, samplerate=16000):
    """
    Record from default microphone using sounddevice for duration seconds,
    return Vosk transcription.
    """
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()
    rec = KaldiRecognizer(model, samplerate)
    rec.AcceptWaveform(recording.tobytes())
    # Collect both intermediate and final results
    res = json.loads(rec.Result())
    res_final = json.loads(rec.FinalResult())
    parts = []
    if res.get("text"):
        parts.append(res.get("text"))
    if res_final.get("text"):
        parts.append(res_final.get("text"))
    return " ".join(parts).strip()

def transcribe_youtube(url):
    """
    Download audio from YouTube (using youtube_dl), convert to WAV, transcribe.
    """
    ydl_opts = {'format': 'bestaudio/best', 'outtmpl': 'video.%(ext)s', 'quiet': True}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        video_file = ydl.prepare_filename(info_dict)
        # Convert video to WAV at 16kHz mono
        wav_file = f"video_{int(time.time())}.wav"
        subprocess.call(["ffmpeg", "-y", "-i", video_file, "-ar", "16000", "-ac", "1", wav_file])
        # Optionally remove video_file to save space
        try:
            os.remove(video_file)
        except Exception:
            pass
        return transcribe_wav(wav_file)

# ------------------ OpenAI / GPT-mini integration ------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # We don't raise here to allow the app to start for transcription-only use,
    # but generate_notes will return a clear error if the key is missing.
    app.logger.warning("OPENAI_API_KEY not found in environment. /generate_notes will fail until it's set.")

def build_prompt(transcription, note_type):
    """
    Create a straightforward prompt for the model. Adjust as needed.
    note_type: one of 'normal', 'detailed', 'bullet', 'summary'
    """
    note_type = note_type.lower()
    if note_type == "normal":
        instruction = "Convert the following transcription into clear, readable notes. Keep structure and main ideas, use normal prose."
    elif note_type == "detailed":
        instruction = "Convert the following transcription into detailed notes. Include explanations, expand acronyms, and add short examples where helpful."
    elif note_type == "bullet":
        instruction = "Convert the following transcription into concise bullet points. Use short, informative bullets and group related bullets where appropriate."
    elif note_type == "summary":
        instruction = "Provide a short summary (2-4 sentences) capturing the main points of the transcription."
    else:
        instruction = "Convert the following transcription into readable notes."

    prompt = f"{instruction}\n\nTranscription:\n\"\"\"\n{transcription}\n\"\"\"\n\nNotes:"
    return prompt

def call_openai_gpt_minimodel(prompt, max_tokens=500, model_name="gpt-mini"):
    """
    Call OpenAI Chat/Completion API. Using a generic POST to /v1/chat/completions.
    Model name is set to gpt-mini by default per your request. If your account
    does not have that model name, change model_name to a valid model (e.g., gpt-3.5-turbo).
    """
    if not OPENAI_API_KEY:
        raise Exception("OpenAI API key is not configured in environment variable OPENAI_API_KEY.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    # We'll use the chat completions format with a single user message.
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that converts transcriptions to notes."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,  # lower temperature for more deterministic output
        "n": 1
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        # bubble up a useful error message
        raise Exception(f"OpenAI API error {resp.status_code}: {resp.text}")
    data = resp.json()
    # Navigate typical response shape to extract assistant message
    # This is resilient to minor variations in response payloads.
    try:
        content = data["choices"][0]["message"]["content"].strip()
    except Exception:
        raise Exception("Unexpected OpenAI response structure: " + json.dumps(data)[:1000])
    return content

# ------------------ Routes ------------------
@app.route('/')
def home():
    return redirect('/login')

@app.route('/index')
def index():
    if 'user_id' in session:
        return render_template("index.html", name=session.get('name'), transcription=session.get('transcription', ''))
    else:
        return render_template("index.html", name="Guest", transcription=session.get('transcription', ''))

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
    """
    Existing endpoint enhanced to store transcription in session['transcription'].
    Returns JSON: {"transcription": "<text>"}
    """
    input_type = request.form.get("input_type")
    result = ""
    try:
        if input_type == "microphone":
            duration = int(request.form.get("duration", 5))
            result = transcribe_microphone(duration)
        elif input_type == "file":
            file = request.files['file']
            # Save file to a safe temporary filename
            filename = f"upload_{int(time.time())}_{file.filename}"
            file.save(filename)
            result = transcribe_wav(filename)
            # remove uploaded file if you want
            try:
                os.remove(filename)
            except Exception:
                pass
        elif input_type == "youtube":
            url = request.form.get("youtube_url")
            result = transcribe_youtube(url)
        else:
            result = "Invalid input type"
    except Exception as e:
        result = f"Error: {str(e)}"

    # Store transcription in session for later note generation (temporary storage)
    session['transcription'] = result
    return jsonify({"transcription": result})

@app.route('/generate_notes', methods=["POST"])
def generate_notes():
    """
    Generates notes from the transcription stored in session['transcription'].
    Expects form-data or JSON with 'note_type' which can be:
      - normal
      - detailed
      - bullet
      - summary
    Returns JSON: {"notes": "..."}
    """
    note_type = request.form.get("note_type") or (request.json and request.json.get("note_type"))
    if not note_type:
        return jsonify({"error": "note_type parameter is required"}), 400

    transcription = session.get('transcription')
    if not transcription:
        # user chose option A: return an error when there is no transcription
        return jsonify({"error": "No transcription found. Please transcribe audio first."}), 400

    try:
        prompt = build_prompt(transcription, note_type)
        # Call OpenAI (gpt-mini as requested). If that model is not present in your account,
        # change model_name to a valid one (e.g., "gpt-3.5-turbo").
        notes = call_openai_gpt_minimodel(prompt, max_tokens=600, model_name="gpt-mini")
        return jsonify({"notes": notes})
    except Exception as e:
        # Return a helpful error message to the frontend
        return jsonify({"error": f"Failed to generate notes: {str(e)}"}), 500

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
    # Debug True is convenient for development; set to False in production
    app.run(debug=True, host="0.0.0.0", port=5000)