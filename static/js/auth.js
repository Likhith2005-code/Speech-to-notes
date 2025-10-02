(function(){
  function togglePeek(btn, input){
    btn.addEventListener('click', ()=>{
      const isText = input.type === 'text';
      input.type = isText ? 'password' : 'text';
      btn.classList.toggle('peeked', !isText);
      input.focus();
    });
  }

  const signin = document.getElementById('signin-form');
  const signup = document.getElementById('signup-form');

  const pwd = document.getElementById('password');
  const peek1 = pwd && pwd.parentElement.querySelector('.peek');
  if (pwd && peek1) togglePeek(peek1, pwd);

  const regPwd = document.getElementById('reg-password');
  const peek2 = regPwd && regPwd.parentElement.querySelector('.peek');
  if (regPwd && peek2) togglePeek(peek2, regPwd);

  if (signup){
    signup.addEventListener('submit', (e)=>{
      const pass = signup.password.value;
      const confirm = signup.confirm.value;
      if (pass !== confirm){
        e.preventDefault();
        alert('Passwords do not match');
      }
    });
  }

  document.querySelectorAll('.oauth-btn').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const provider = btn.dataset.provider;
      // Redirect paths ready for backend routing (Flask/Django/FastAPI)
      window.location.href = `/auth/oauth/${provider}`;
    });
  });
})();


// Close popup when user chooses "Login"
function closeModal() {
  document.getElementById("popupModal").style.display = "none";
}