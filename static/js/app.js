// Minimal, controlled interactions only
const bar = document.getElementById('bar');
const output = document.getElementById('output');
const clearBtn = document.getElementById('clearText');
const textarea = document.querySelector('.text-area');

function simulateProgress() {
  bar.style.width = '0%';
  output.textContent = 'Generating...';
  let p = 0;
  function step(){
    p += Math.random()*14 + 6; // steady, not flashy
    if(p >= 100){
      p = 100;
      bar.style.width = p + '%';
      output.textContent = 'Notes generated. You can edit or share them.';
      return;
    }
    bar.style.width = Math.round(p) + '%';
    setTimeout(step, 280);
  }
  step();
}

// Trigger generation when any chip is clicked
document.querySelectorAll('.chip').forEach(c=>{
  c.addEventListener('click', simulateProgress);
});

// Clear textarea
clearBtn.addEventListener('click', ()=>{
  textarea.value = '';
  textarea.focus();
});

// Optional keyboard focus class hook
document.addEventListener('keydown', (e)=>{
  if(e.key === 'Tab') document.body.classList.add('kbd');
});

const button = document.getElementById("btnYT");
    const inputBox = document.getElementById("inputBox");

    button.addEventListener("click", () => {
      button.style.display = "none";     // hide button
      inputBox.style.display = "inline"; // show input box
      inputBox.focus();                  // focus input
    });




// Record Button simulation--------
const recordBtn = document.getElementById('record-btn');
const stopBtn = document.getElementById('stop-btn');
const deleteBtn = document.getElementById('delete-btn');
const timerEl = document.getElementById('timer');

let timerInterval;
let seconds = 0;
let recording = false;

function formatTime(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2,'0')}`;
}

recordBtn.addEventListener('click', () => {
  if (!recording) {
    // Start recording
    recording = true;
    stopBtn.classList.remove('hidden');
    recordBtn.style.backgroundColor = '#f88585ff'; // slightly lighter red
    seconds = 0;
    timerEl.textContent = formatTime(seconds);

    timerInterval = setInterval(() => {
      seconds++;
      timerEl.textContent = formatTime(seconds);
    }, 1000);
  }
});

stopBtn.addEventListener('click', (e) => {
  e.stopPropagation(); // prevent triggering recordBtn click
  clearInterval(timerInterval);
  stopBtn.classList.add('hidden');
  deleteBtn.classList.remove('hidden');
  recordBtn.style.backgroundColor = '#ffffffff';
  timerEl.textContent = formatTime(seconds);
});

deleteBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  deleteBtn.classList.add('hidden');
  timerEl.textContent = '0:00';
  recording = false;
});



const btnUpload = document.getElementById('btnUpload');
const videoInput = document.getElementById('videoInput');
const videoPreview = document.getElementById('videoPreview');
const previewBtn = document.getElementById('previewBtn');

let isPreviewVisible = false;

// Trigger file input when main button is clicked
btnUpload.addEventListener('click', (e) => {
  // Prevent preview button click from triggering file input
  if (e.target === previewBtn) return;
  videoInput.click();
});

// When a video is selected
videoInput.addEventListener('change', (event) => {
  const file = event.target.files[0];
  if (file) {
    videoPreview.src = URL.createObjectURL(file);
    previewBtn.style.display = 'inline-block'; // show preview button
    //previewBtn.classList.remove('hidden');
    videoPreview.style.display = 'none'; // hide preview initially
    isPreviewVisible = false;
  }
});

// Toggle video preview on 👁️ button click
previewBtn.addEventListener('click', () => {
  isPreviewVisible = !isPreviewVisible;
  videoPreview.style.display = isPreviewVisible ? 'block' : 'none';
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



// app.js

// ------------------- Notes Generation Integration -------------------
const chips = document.querySelectorAll('.chip');
const progressBar = document.getElementById('bar');
const outputBox = document.getElementById('output');

// Function to show smooth progress bar animation while waiting for backend
function animateProgress() {
  progressBar.style.width = '0%';
  let progress = 0;
  const interval = setInterval(() => {
    progress += Math.random() * 10 + 5;
    if (progress >= 90) {
      clearInterval(interval);
      return;
    }
    progressBar.style.width = `${Math.min(90, progress)}%`;
  }, 250);
  return interval;
}

chips.forEach(chip => {
  chip.addEventListener('click', async () => {
    const type = chip.textContent.trim().toLowerCase().split(" ")[0]; // e.g. "normal", "detailed"
    outputBox.textContent = `Generating ${type} notes...`;
    const anim = animateProgress();

    const formData = new FormData();
    formData.append('note_type', type);

    try {
      const res = await fetch('/generate_notes', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      clearInterval(anim);
      progressBar.style.width = '100%';

      if (data.notes) {
        // Display generated notes
        outputBox.textContent = data.notes;
      } else if (data.error) {
        outputBox.textContent = '⚠ ' + data.error;
      } else {
        outputBox.textContent = '⚠ Unexpected response from server.';
      }
    } catch (err) {
      clearInterval(anim);
      outputBox.textContent = '❌ Failed to generate notes: ' + err.message;
      progressBar.style.width = '0%';
    }
  });
});