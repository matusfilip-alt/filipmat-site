/* Google Analytics 4 with consent mode.
   Nothing is stored and no cookie is set until the visitor taps "ok".
   One quiet line at the bottom of the page, shown once. */
(function () {
  'use strict';
  var id = document.documentElement.getAttribute('data-ga');
  if (!id) return;
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('consent', 'default', {
    analytics_storage: 'denied', ad_storage: 'denied',
    ad_user_data: 'denied', ad_personalization: 'denied'
  });
  gtag('js', new Date());
  gtag('config', id, { anonymize_ip: true });
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
  document.head.appendChild(s);

  var choice = null;
  try { choice = localStorage.getItem('consent'); } catch (e) {}
  if (choice === 'yes') { gtag('consent', 'update', { analytics_storage: 'granted' }); return; }
  if (choice === 'no') return;

  var bar = document.createElement('div');
  bar.className = 'consent mono';
  bar.innerHTML = '<span>may I count your visit with google analytics?</span>' +
    '<button type="button" data-c="yes">ok</button><button type="button" data-c="no">no</button>';
  bar.addEventListener('click', function (e) {
    var c = e.target.getAttribute('data-c');
    if (!c) return;
    try { localStorage.setItem('consent', c); } catch (err) {}
    if (c === 'yes') gtag('consent', 'update', { analytics_storage: 'granted' });
    bar.remove();
  });
  document.body.appendChild(bar);
})();
