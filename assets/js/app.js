/* ==========================================================================
   Mechidan. Runtime behaviour.
   No dependencies, no tracking, no network calls except the form POST.
   Reads its strings and settings from <script id="site-data">.
   ========================================================================== */
(function () {
  'use strict';

  var node = document.getElementById('site-data');
  var data = node ? JSON.parse(node.textContent) : null;
  var t = (data && data.t) || {};
  var LANG_KEY = 'mechidan.lang';

  function $(sel, scope) { return (scope || document).querySelector(sel); }
  function $$(sel, scope) { return Array.prototype.slice.call((scope || document).querySelectorAll(sel)); }

  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- mobile menu ---------------------------------------------- */
  (function menu() {
    var burger = $('#burger');
    var nav = $('#mainnav');
    if (!burger || !nav) return;

    function setOpen(open) {
      nav.dataset.open = open ? 'true' : 'false';
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      burger.setAttribute('aria-label', open ? (t.menuClose || 'Close menu') : (t.menuOpen || 'Open menu'));
    }

    burger.addEventListener('click', function () {
      setOpen(nav.dataset.open !== 'true');
    });
    nav.addEventListener('click', function (ev) {
      if (ev.target.tagName === 'A') setOpen(false);
    });
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' && nav.dataset.open === 'true') {
        setOpen(false);
        burger.focus();
      }
    });
  }());

  /* ---------- language preference --------------------------------------
     One localStorage key, set only when the visitor clicks the switch.
     The Spanish home page redirects a first-time English browser once.    */
  (function language() {
    if (!data) return;

    function read() {
      try { return window.localStorage.getItem(LANG_KEY); } catch (err) { return null; }
    }
    function save(value) {
      try { window.localStorage.setItem(LANG_KEY, value); } catch (err) { /* private mode */ }
    }

    $$('[data-lang-set]').forEach(function (link) {
      link.addEventListener('click', function () { save(link.dataset.langSet); });
    });

    if (!data.isEntryPoint) return;

    var stored = read();
    if (stored && stored !== data.locale) {
      window.location.replace(data.altLocaleUrl);
      return;
    }
    if (!stored && data.localeDetection === 'browser') {
      var browser = (navigator.language || '').slice(0, 2).toLowerCase();
      if (browser && browser !== data.locale && browser === data.altLocale) {
        window.location.replace(data.altLocaleUrl);
      }
    }
  }());

  /* ---------- scroll reveal --------------------------------------------- */
  (function reveal() {
    var items = $$('.reveal');
    if (!items.length) return;

    if (reducedMotion || !('IntersectionObserver' in window)) {
      items.forEach(function (el) { el.classList.add('is-in'); });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        observer.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

    items.forEach(function (el) { observer.observe(el); });
  }());

  /* ---------- background tone follows the section in view --------------- */
  (function tone() {
    var sections = $$('[data-tone]');
    if (!sections.length || reducedMotion || !('IntersectionObserver' in window)) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        document.body.dataset.tone = entry.target.dataset.tone;
      });
    }, { rootMargin: '-40% 0px -40% 0px', threshold: 0 });

    sections.forEach(function (el) { observer.observe(el); });
  }());

  /* ---------- contact form: one question at a time ----------------------- */
  (function contactForm() {
    var form = $('#contact-form');
    if (!form || !data) return;

    var alertBox = $('#form-alert');
    var success = $('#form-success');
    var button = $('#form-submit');
    var replyTo = $('#f-replyto');
    var panels = $$('.wizard__panel', form);
    var openedAt = Date.now();
    var current = 0;

    var EMAIL = /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i;
    var PHONE = /^[+()\d\s.-]{7,}$/;

    /* which field each panel carries, in panel order */
    var PANEL_FIELDS = ['need', 'name', 'contact'];

    function setError(name, message) {
      var field = form.querySelector('[data-field="' + name + '"]');
      if (!field) return;
      field.dataset.invalid = message ? 'true' : 'false';
      var slot = $('.err', field);
      if (slot) slot.textContent = message || '';
    }

    function shout(message) {
      if (!alertBox) return;
      alertBox.textContent = message;
      alertBox.dataset.show = message ? 'true' : 'false';
    }

    function validateField(name) {
      var value = (form.elements[name] ? form.elements[name].value : '').trim();
      if (name === 'need') {
        var okNeed = value.length >= 5;
        setError('need', okNeed ? '' : t.errNeed);
        return okNeed;
      }
      if (name === 'name') {
        var okName = value.length >= 2;
        setError('name', okName ? '' : t.errName);
        return okName;
      }
      if (name === 'contact') {
        if (!value) { setError('contact', t.errContact); return false; }
        if (!EMAIL.test(value) && !PHONE.test(value)) {
          setError('contact', t.errContactFormat);
          return false;
        }
        setError('contact', '');
        if (replyTo && EMAIL.test(value)) replyTo.value = value;
        return true;
      }
      return true;
    }

    function validateConsent() {
      if (form.elements.consent.checked) { setError('consent', ''); return true; }
      setError('consent', t.errConsent);
      return false;
    }

    function show(index) {
      panels.forEach(function (panel, i) {
        var active = i === index;
        panel.hidden = !active;
        panel.setAttribute('aria-hidden', active ? 'false' : 'true');
      });
      current = index;
      var input = panels[index] && panels[index].querySelector('input[type="text"], textarea');
      if (input) input.focus({ preventScroll: true });
    }

    panels.forEach(function (panel, i) {
      var next = panel.querySelector('[data-wizard-next]');
      var back = panel.querySelector('[data-wizard-back]');
      if (next) {
        next.addEventListener('click', function () {
          if (validateField(PANEL_FIELDS[i])) show(i + 1);
        });
      }
      if (back) {
        back.addEventListener('click', function () { show(i - 1); });
      }
      /* Enter advances instead of submitting early */
      panel.addEventListener('keydown', function (ev) {
        if (ev.key !== 'Enter' || ev.target.tagName === 'TEXTAREA') return;
        if (i < panels.length - 1) {
          ev.preventDefault();
          if (validateField(PANEL_FIELDS[i])) show(i + 1);
        }
      });
    });

    PANEL_FIELDS.forEach(function (name) {
      var input = form.elements[name];
      if (!input) return;
      input.addEventListener('input', function () {
        var field = form.querySelector('[data-field="' + name + '"]');
        if (field && field.dataset.invalid === 'true') validateField(name);
      });
    });

    function showSuccess() {
      form.style.display = 'none';
      if (success) {
        success.dataset.show = 'true';
        success.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' });
      }
    }

    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      shout('');

      var trap = form.elements[data.honeypotField];
      if (trap && trap.value) return;

      if ((Date.now() - openedAt) / 1000 < (data.minFillSeconds || 0)) {
        shout(t.errTooFast);
        return;
      }

      var ok = true;
      PANEL_FIELDS.forEach(function (name) { if (!validateField(name)) ok = false; });
      if (!validateConsent()) ok = false;
      if (!ok) {
        /* jump back to the first panel with a problem */
        for (var i = 0; i < PANEL_FIELDS.length; i += 1) {
          var field = form.querySelector('[data-field="' + PANEL_FIELDS[i] + '"]');
          if (field && field.dataset.invalid === 'true') { show(i); return; }
        }
        return;
      }

      var payload = new FormData(form);

      if (!data.formEndpoint) {
        var lines = [
          form.elements.name.value,
          '',
          form.elements.need.value,
          '',
          form.elements.contact.value
        ].join('\n');
        window.location.href = data.mailtoFallback + encodeURIComponent(lines);
        return;
      }

      button.dataset.busy = 'true';
      button.textContent = t.submitting || 'Sending';

      fetch(data.formEndpoint, {
        method: 'POST',
        body: payload,
        headers: { Accept: 'application/json' }
      }).then(function (response) {
        if (!response.ok) throw new Error('rejected');
        showSuccess();
      }).catch(function () {
        shout(t.errNetwork);
        button.dataset.busy = 'false';
        button.textContent = t.submit || 'Send';
      });
    });
  }());
}());
