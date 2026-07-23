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

    var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced || !('IntersectionObserver' in window)) {
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

  /* ---------- contact form ---------------------------------------------- */
  (function contactForm() {
    var form = $('#contact-form');
    if (!form || !data) return;

    var alertBox = $('#form-alert');
    var success = $('#form-success');
    var button = $('#form-submit');
    var replyTo = $('#f-replyto');
    var openedAt = Date.now();

    var EMAIL = /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i;
    var PHONE = /^[+()\d\s.-]{7,}$/;

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

    function validate() {
      var values = {
        name: form.elements.name.value.trim(),
        need: form.elements.need.value.trim(),
        contact: form.elements.contact.value.trim()
      };
      var ok = true;

      setError('name', values.name.length >= 2 ? '' : (ok = false, t.errName));
      setError('need', values.need.length >= 5 ? '' : (ok = false, t.errNeed));

      if (!values.contact) {
        setError('contact', t.errContact);
        ok = false;
      } else if (!EMAIL.test(values.contact) && !PHONE.test(values.contact)) {
        setError('contact', t.errContactFormat);
        ok = false;
      } else {
        setError('contact', '');
      }

      if (form.elements.consent.checked) {
        setError('consent', '');
      } else {
        setError('consent', t.errConsent);
        ok = false;
      }

      if (ok && replyTo && EMAIL.test(values.contact)) replyTo.value = values.contact;
      return ok;
    }

    ['name', 'need', 'contact'].forEach(function (name) {
      var input = form.elements[name];
      if (!input) return;
      input.addEventListener('input', function () {
        var field = form.querySelector('[data-field="' + name + '"]');
        if (field && field.dataset.invalid === 'true') validate();
      });
    });

    function showSuccess() {
      form.style.display = 'none';
      if (success) {
        success.dataset.show = 'true';
        success.scrollIntoView({ behavior: 'smooth', block: 'center' });
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
      if (!validate()) {
        var broken = form.querySelector('[data-invalid="true"] input, [data-invalid="true"] textarea');
        if (broken) broken.focus();
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
