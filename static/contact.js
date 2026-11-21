/* Contact form on the about page: sends without leaving the page. */
(function () {
  'use strict';
  var f = document.querySelector('.cform');
  if (!f) return;
  var status = f.querySelector('.status');
  var btn = f.querySelector('button[type=submit]');
  f.elements.t.value = Date.now();
  f.addEventListener('submit', function (e) {
    e.preventDefault();
    var name = f.elements.name.value.trim(), email = f.elements.email.value.trim(), msg = f.elements.message.value.trim();
    if (!name || !msg) { status.textContent = 'please fill in your name and message'; return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { status.textContent = 'please check your email address'; return; }
    btn.disabled = true; status.textContent = 'sending…';
    fetch(f.action, { method: 'POST', body: new FormData(f) })
      .then(function (r) { return r.json().catch(function () { return { ok: false, message: 'sorry, something went wrong' }; }); })
      .then(function (d) {
        status.textContent = d.message || (d.ok ? 'thank you' : 'sorry, something went wrong');
        if (d.ok) { f.reset(); f.elements.t.value = Date.now(); } else { btn.disabled = false; }
      })
      .catch(function () { status.textContent = 'sorry, sending failed, please try again later'; btn.disabled = false; });
  });
})();
