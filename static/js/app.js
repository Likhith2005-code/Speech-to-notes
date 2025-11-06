// ----------- Elements -----------
const bar = document.getElementById('bar');
const output = document.getElementById('output');
const clearBtn = document.getElementById('clearText');
const textarea = document.querySelector('.text-area');
const chips = document.querySelectorAll('.chip');
const recordBtn = document.getElementById('record-btn');
const btnUpload = document.getElementById('btnUpload');
const videoInput = document.getElementById('videoInput');
const videoPreview = document.getElementById('videoPreview');
const btnYT = document.getElementById('btnYT');
const inputBox = document.getElementById('inputBox');
const btnPDF = document.getElementById('btnPDF');
const pdfInput = document.getElementById('pdfInput');

let recorder, audioChunks = [], lastTranscription = "";

// ----------- Utility Functions -----------
function animateProgress() {
  bar.style.width = '0%';
  let progress = 0;
  const interval = setInterval(() => {
    progress += Math.random() * 10 + 5;
    if (progress >= 90) {
      progress = 90;
      clearInterval(interval);
    }
    bar.style.width = `${progress}%`;
  }, 250);
  return interval;
}
function finishProgress() { bar.style.width = '100%'; setTimeout(() => bar.style.width = '0%', 1500); }

// ----------- Microphone Recording -----------
recordBtn.addEventListener('click', async () => {
  if (!recorder) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(stream);
    audioChunks = [];
    recorder.ondataavailable = e => audioChunks.push(e.data);
    recorder.onstop = sendMicAudio;
    recorder.start();
    output.textContent = "🎙 Recording... Click again to stop.";
  } else {
    recorder.stop();
    recorder = null;
    output.textContent = "🕓 Processing audio...";
  }
});

async function sendMicAudio() {
  const blob = new Blob(audioChunks, { type: 'audio/webm' });
  audioChunks = [];
  const formData = new FormData();
  formData.append('input_type', 'microphone');
  formData.append('file', blob, 'mic.webm');
  const anim = animateProgress();
  try {
    const res = await fetch('/transcribe', { method: 'POST', body: formData });
    const data = await res.json();
    clearInterval(anim); finishProgress();
    if (data.transcription) {
      lastTranscription = data.transcription;
      output.textContent = data.transcription;
    } else output.textContent = data.error || "Error during transcription.";
  } catch (e) {
    clearInterval(anim);
    output.textContent = "❌ " + e.message;
  }
}

// ----------- Upload Video/Audio -----------
btnUpload.addEventListener('click', () => videoInput.click());
videoInput.addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;
  if (file.type.startsWith('video/')) {
    videoPreview.src = URL.createObjectURL(file);
    videoPreview.style.display = 'block';
  }
  transcribeFile(file, 'file');
});

// ----------- Upload PDF -----------
btnPDF.addEventListener('click', () => pdfInput.click());
pdfInput.addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;
  transcribeFile(file, 'pdf');
});

// ----------- YouTube Input -----------
btnYT.addEventListener('click', () => {
  btnYT.style.display = 'none';
  inputBox.style.display = 'inline';
  inputBox.focus();
});
inputBox.addEventListener('keydown', e => {
  if (e.key === 'Enter') transcribeYoutube(inputBox.value.trim());
});

// ----------- Shared Transcription Handlers -----------
async function transcribeFile(file, type) {
  output.textContent = `🎧 Processing ${type.toUpperCase()}...`;
  const form = new FormData();
  form.append('input_type', type);
  form.append('file', file);
  const anim = animateProgress();

  try {
    const res = await fetch('/transcribe', { method: 'POST', body: form });
    const data = await res.json();
    clearInterval(anim); finishProgress();
    if (data.transcription) {
      lastTranscription = data.transcription;
      output.textContent = data.transcription;
    } else output.textContent = data.error || "Error processing file.";
  } catch (err) {
    clearInterval(anim);
    output.textContent = "❌ " + err.message;
  }
}

async function transcribeYoutube(url) {
  output.textContent = '🎬 Downloading & transcribing...';
  const form = new FormData();
  form.append('input_type', 'youtube');
  form.append('youtube_url', url);
  const anim = animateProgress();
  try {
    const res = await fetch('/transcribe', { method: 'POST', body: form });
    const data = await res.json();
    clearInterval(anim); finishProgress();
    if (data.transcription) {
      lastTranscription = data.transcription;
      output.textContent = data.transcription;
    } else output.textContent = data.error || "Error.";
  } catch (err) {
    clearInterval(anim);
    output.textContent = "❌ " + err.message;
  }
}

// ----------- Notes Generation (Now includes textarea input) -----------
chips.forEach(chip => chip.addEventListener('click', async () => {
  const noteType = chip.textContent.trim().toLowerCase().split(' ')[0];

  // ✅ New Logic: prioritize textarea input
  const textToUse = textarea.value.trim()
    ? textarea.value.trim()
    : lastTranscription.trim();

  if (!textToUse) {
    output.textContent = "⚠ Please type something in the text area or transcribe first.";
    return;
  }

  output.textContent = `🧠 Generating ${noteType} notes...`;
  const form = new FormData();
  form.append('note_type', noteType);
  form.append('transcription', textToUse);
  const anim = animateProgress();

  try {
    const res = await fetch('/generate_notes', { method: 'POST', body: form });
    const data = await res.json();
    clearInterval(anim); finishProgress();
    if (data.notes) {
      output.textContent = data.notes;
    } else output.textContent = data.error || "Error generating notes.";
  } catch (err) {
    clearInterval(anim);
    output.textContent = "❌ " + err.message;
  }
}));

// ----------- Clear ----------
clearBtn.addEventListener('click', () => {
  textarea.value = '';
  lastTranscription = '';
  output.textContent = '';
});

//hamburger Menu
const menu=document.getElementById('menu');
const menuContent=document.getElementById('menu-content');

menu.addEventListener('click',(e)=>{
  menuContent.style.display=menuContent.style.display==='block'?'none':'block';
});

window.addEventListener('click',(e)=>{
  if(!menu.contains(e.target)&&!menuContent.contains(e.target)){
    menuContent.style.display='none';
  }
})