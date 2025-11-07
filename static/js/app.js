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
const stopBtn = document.getElementById('stop-btn');
const deleteBtn = document.getElementById('delete-btn');
const timerEl = document.getElementById('timer');
const editBtn = document.getElementById('editBtn');

let recorder, audioChunks = [], lastTranscription = "";
let timerInterval;
let seconds = 0;
let recording = false;
let isEditing = false;

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

// ----------- Microphone Recording (UI + Real Recording) -----------
// Format timer (MM:SS)
function formatTime(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// Start Recording
recordBtn.addEventListener('click', async () => {
  if (recording) return; // already recording
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(stream);
    audioChunks = [];

    recorder.ondataavailable = e => audioChunks.push(e.data);
    recorder.onstop = async () => {
      await sendMicAudio();
      // stop stream tracks
      stream.getTracks().forEach(track => track.stop());
    };

    recorder.start();
    recording = true;
    stopBtn.classList.remove('hidden');
    recordBtn.style.backgroundColor = '#f88585ff';
    seconds = 0;
    timerEl.textContent = formatTime(seconds);

    timerInterval = setInterval(() => {
      seconds++;
      timerEl.textContent = formatTime(seconds);
    }, 1000);

    output.textContent = "🎙 Recording started...";
  } catch (err) {
    output.textContent = "❌ Microphone access denied or error: " + err.message;
  }
});

// Stop Recording
stopBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  if (!recording || !recorder) return;
  recorder.stop();

  clearInterval(timerInterval);
  stopBtn.classList.add('hidden');
  deleteBtn.classList.remove('hidden');
  recordBtn.style.backgroundColor = '#ffffffff';
  timerEl.textContent = formatTime(seconds);
  output.textContent = "🕓 Processing audio...";
  recording = false;
});

// Delete/Reset Button
deleteBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  deleteBtn.classList.add('hidden');
  timerEl.textContent = '0:00';
  recording = false;
  output.textContent = "";
});

// Send Recorded Audio to Flask Backend
async function sendMicAudio() {
  if (!audioChunks.length) {
    output.textContent = "⚠ No audio recorded.";
    return;
  }

  const blob = new Blob(audioChunks, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append('input_type', 'microphone');
  formData.append('file', blob, 'mic_recording.webm');

  const anim = animateProgress(); // optional: your existing progress bar
  try {
    const res = await fetch('/transcribe', { method: 'POST', body: formData });
    const data = await res.json();
    clearInterval(anim);
    finishProgress();

    if (data.transcription) {
      output.textContent = data.transcription;
    } else {
      output.textContent = '⚠ ' + (data.error || 'Transcription failed.');
    }
  } catch (err) {
    clearInterval(anim);
    output.textContent = '❌ ' + err.message;
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


// ----------- Download as PDF (Multi-page) -----------
document.getElementById('downloadPdfBtn').addEventListener('click', () => {
  const outputBox = document.getElementById('output');
  const text = outputBox.textContent.trim();

  if (!text || text === 'Output will appear here...') {
    alert("⚠ No notes available to download.");
    return;
  }

  const script = document.createElement('script');
  script.src = "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js";
  script.onload = () => {
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({ orientation: 'p', unit: 'mm', format: 'a4' });

    const margin = 15;
    const pageHeight = pdf.internal.pageSize.getHeight();
    const pageWidth = pdf.internal.pageSize.getWidth();
    const usableWidth = pageWidth - margin * 2;
    const lineHeight = 8;

    pdf.setFont("times", "normal");
    pdf.setFontSize(12);

    // Split text into lines that fit page width
    const lines = pdf.splitTextToSize(text, usableWidth);

    let cursorY = 20; // Start position on the first page

    // Add small header
    pdf.setFontSize(14);
    pdf.text("S2N Notes", margin, 10);
    pdf.setFontSize(12);

    for (let i = 0; i < lines.length; i++) {
      // If next line goes beyond the page height, add a new page
      if (cursorY + lineHeight > pageHeight - margin) {
        pdf.addPage();
        cursorY = 20;

        // Repeat header on new page
        pdf.setFontSize(14);
        pdf.text("S2N Notes", margin, 10);
        pdf.setFontSize(12);
      }
      pdf.text(lines[i], margin, cursorY);
      cursorY += lineHeight;
    }

    const filename = `Notes_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.pdf`;
    pdf.save(filename);
  };

  document.body.appendChild(script);
});


// ----------- Edit Notes Feature -----------

editBtn.addEventListener('click', () => {
  if (!isEditing) {
    // Start editing: move content from output → textarea
    const text = output.textContent.trim();
    if (!text || text === "Output will appear here...") {
      alert("⚠ No notes available to edit.");
      return;
    }

    textarea.value = text;
    textarea.focus();

    editBtn.textContent = "Save"; // change button label
    isEditing = true;
    output.textContent = "✏ Editing mode — make changes in the text area.";
  } else {
    // Save changes: move content back to output
    const editedText = textarea.value.trim();
    if (!editedText) {
      alert("⚠ Cannot save empty text.");
      return;
    }

    output.textContent = editedText;
    editBtn.textContent = "Edit Notes"; // revert label
    isEditing = false;
    textarea.value = ""; // optional — clear textarea after saving
  }
});


// ----------- Save Draft Feature (Persistent Notes) -----------
const saveBtn = document.querySelector('.ghost'); // Save Draft button

// Load saved draft when page opens
window.addEventListener('DOMContentLoaded', () => {
  const savedNotes = localStorage.getItem('savedNotes');
  if (savedNotes) {
    output.textContent = savedNotes;
  }
});

// Save current output text as draft
saveBtn.addEventListener('click', () => {
  const currentNotes = output.textContent.trim();

  if (!currentNotes || currentNotes === "Your summarized notes will appear here...") {
    alert("⚠ No notes available to save.");
    return;
  }

  localStorage.setItem('savedNotes', currentNotes);
  alert("✅ Draft saved successfully!");
});

// Clear button — also clear local storage
clearBtn.addEventListener('click', () => {
  textarea.value = "";
  output.textContent = "";
  localStorage.removeItem('savedNotes');
  alert("🗑 Draft cleared.");
});