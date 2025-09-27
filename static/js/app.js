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