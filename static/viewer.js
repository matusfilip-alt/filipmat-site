/* Full-screen photo viewer for story pages. Plain JS, no libraries.
   Tap a photo (or "full screen" at the top): black screen, swipe left/right,
   tap to hide the controls, phone back button or "close" to leave.
   Without JavaScript a photo simply opens as a normal image file. */
(function () {
  'use strict';
  var figs = Array.prototype.slice.call(document.querySelectorAll('article figure'));
  if (!figs.length) return;

  var items = figs.map(function (f) {
    var a = f.querySelector('a');
    var img = f.querySelector('img');
    var cap = f.querySelector('figcaption');
    return {
      src: a ? a.getAttribute('href') : (img.currentSrc || img.src),
      alt: img.getAttribute('alt') || '',
      cap: cap ? cap.textContent : ''
    };
  });

  var root, track, countEl, capEl;
  var index = 0;
  var isOpen = false;
  var pushed = false;

  function load(i) {
    var slide = track.children[i];
    if (!slide) return;
    var im = slide.firstChild;
    if (!im.getAttribute('src')) im.setAttribute('src', im.getAttribute('data-src'));
  }

  function update(i) {
    index = i;
    countEl.textContent = (i + 1) + ' / ' + items.length;
    capEl.textContent = items[i].cap;
    load(i - 1);
    load(i);
    load(i + 1);
  }

  function goTo(i, smooth) {
    i = Math.max(0, Math.min(items.length - 1, i));
    track.scrollTo({ left: i * track.clientWidth, behavior: smooth ? 'smooth' : 'auto' });
    update(i);
  }

  function build() {
    if (root) return;
    root = document.createElement('div');
    root.className = 'fsv';
    root.hidden = true;
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-label', 'photos');
    root.innerHTML =
      '<div class="fsv-track"></div>' +
      '<div class="fsv-top"><span class="fsv-count"></span>' +
      '<button class="fsv-close" type="button">close</button></div>' +
      '<div class="fsv-cap"></div>';
    track = root.querySelector('.fsv-track');
    countEl = root.querySelector('.fsv-count');
    capEl = root.querySelector('.fsv-cap');

    items.forEach(function (it) {
      var slide = document.createElement('div');
      slide.className = 'fsv-slide';
      var im = document.createElement('img');
      im.alt = it.alt;
      im.draggable = false;
      im.setAttribute('data-src', it.src);
      slide.appendChild(im);
      track.appendChild(slide);
    });

    track.addEventListener('scroll', function () {
      var i = Math.round(track.scrollLeft / track.clientWidth);
      if (i !== index) update(i);
    }, { passive: true });

    track.addEventListener('click', function (e) {
      var x = e.clientX / window.innerWidth;
      if (e.pointerType === 'mouse' && x < 0.3) goTo(index - 1, true);
      else if (e.pointerType === 'mouse' && x > 0.7) goTo(index + 1, true);
      else root.classList.toggle('quiet');
    });

    root.querySelector('.fsv-close').addEventListener('click', close);
    document.body.appendChild(root);
  }

  function openAt(i) {
    build();
    root.hidden = false;
    root.classList.remove('quiet');
    document.documentElement.classList.add('fsv-open');
    isOpen = true;
    goTo(i, false);
    try { history.pushState({ fsv: 1 }, ''); pushed = true; } catch (e) { pushed = false; }
    try {
      if (root.requestFullscreen) {
        var p = root.requestFullscreen();
        if (p && p.catch) p.catch(function () {});
      }
    } catch (e) {}
    root.querySelector('.fsv-close').focus();
  }

  function hide() {
    if (!isOpen) return;
    isOpen = false;
    root.hidden = true;
    document.documentElement.classList.remove('fsv-open');
    try {
      if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen();
    } catch (e) {}
    figs[index].scrollIntoView({ block: 'center' });
  }

  function close() {
    if (pushed) { pushed = false; history.back(); } else { hide(); }
  }

  window.addEventListener('popstate', function () {
    if (isOpen) { pushed = false; hide(); }
  });

  document.addEventListener('fullscreenchange', function () {
    if (isOpen && !document.fullscreenElement) close();
  });

  document.addEventListener('keydown', function (e) {
    if (!isOpen) return;
    if (e.key === 'ArrowRight') goTo(index + 1, true);
    else if (e.key === 'ArrowLeft') goTo(index - 1, true);
    else if (e.key === 'Escape') close();
  });

  figs.forEach(function (f, i) {
    var a = f.querySelector('a');
    if (!a) return;
    a.addEventListener('click', function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
      e.preventDefault();
      openAt(i);
    });
  });

  var top = document.querySelector('.top .right') || document.querySelector('.top');
  if (top) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'fs';
    btn.textContent = 'full screen';
    btn.addEventListener('click', function () { openAt(0); });
    top.appendChild(btn);
  }
})();
