/* Mechidan. Client behaviour.
   Every value comes from the JSON payload the build injects into #site-data.
   Nothing here is hardcoded. */
(function () {
  'use strict';

  var el = document.getElementById('site-data');
  if (!el) { return; }
  var DATA = JSON.parse(el.textContent);
  var LANG_KEY = 'mechidan.lang';

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function store(key, value) {
    try {
      if (value === undefined) { return window.localStorage.getItem(key); }
      window.localStorage.setItem(key, value);
    } catch (e) { return null; }
  }

  /* ------------------------------------------------------------------ *
   * 1. Language preference
   * ------------------------------------------------------------------ */
  function initLanguage() {
    var saved = store(LANG_KEY);

    $$('[data-lang-set]').forEach(function (link) {
      link.addEventListener('click', function () {
        store(LANG_KEY, link.getAttribute('data-lang-set'));
      });
    });

    if (DATA.localeDetection !== 'browser' || !DATA.isEntryPoint) { return; }
    if (saved) {
      if (saved !== DATA.locale && DATA.altLocaleUrl) { window.location.replace(DATA.altLocaleUrl); }
      return;
    }
    var prefs = navigator.languages || [navigator.language || ''];
    var wantsDefault = prefs.some(function (tag) {
      return String(tag).toLowerCase().indexOf(DATA.defaultLocale) === 0;
    });
    if (!wantsDefault && DATA.altLocaleUrl) {
      store(LANG_KEY, DATA.altLocale);
      window.location.replace(DATA.altLocaleUrl);
    }
  }

  /* ------------------------------------------------------------------ *
   * 2. Mobile navigation
   * ------------------------------------------------------------------ */
  function initNav() {
    var burger = $('#burger');
    var nav = $('#mainnav');
    if (!burger || !nav) { return; }

    function setOpen(open) {
      nav.setAttribute('data-open', open ? 'true' : 'false');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      burger.setAttribute('aria-label', open ? DATA.t.menuClose : DATA.t.menuOpen);
    }
    burger.addEventListener('click', function () {
      setOpen(nav.getAttribute('data-open') !== 'true');
    });
    nav.addEventListener('click', function (ev) {
      if (ev.target.tagName === 'A') { setOpen(false); }
    });
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') { setOpen(false); }
    });
  }

  /* ------------------------------------------------------------------ *
   * 3. Quote docket
   * ------------------------------------------------------------------ */
  function money(amount) {
    return DATA.currencySymbol + new Intl.NumberFormat(DATA.htmlLang, {
      minimumFractionDigits: 0, maximumFractionDigits: 0
    }).format(amount);
  }

  function initQuote() {
    var docket = $('#docket');
    if (!docket) { return; }

    var addonBox = $('#docket-addons');
    var lines = $('#docket-lines');
    var totalOut = $('#docket-total');
    var maintOut = $('#docket-maint');
    var noteOut = $('#docket-note');
    var refOut = $('#docket-ref');
    var sendForm = $('#docket-send');
    var sendWa = $('#docket-wa');

    if (refOut) {
      var now = new Date();
      refOut.textContent = DATA.t.docRef + ' ' +
        String(now.getFullYear()).slice(2) +
        String(now.getMonth() + 1).padStart(2, '0') +
        String(now.getDate()).padStart(2, '0') + '-' +
        String(Math.floor(Math.random() * 900) + 100);
    }

    function currentService() {
      var picked = $('input[name="docket-service"]:checked', docket);
      var id = picked ? picked.value : DATA.services[0].id;
      return DATA.services.filter(function (s) { return s.id === id; })[0];
    }

    function flash(node) {
      if (!node) { return; }
      node.classList.remove('is-ticking');
      void node.offsetWidth;
      node.classList.add('is-ticking');
    }

    function renderAddons(service) {
      addonBox.innerHTML = '';
      if (!service.addons.length) {
        var p = document.createElement('p');
        p.className = 'addon__empty';
        p.textContent = DATA.t.noAddons;
        addonBox.appendChild(p);
        return;
      }
      service.addons.forEach(function (addon) {
        var label = document.createElement('label');
        label.className = 'addon';
        var input = document.createElement('input');
        input.type = 'checkbox';
        input.value = addon.id;
        input.setAttribute('data-price', addon.price);
        input.setAttribute('data-name', addon.name);
        var name = document.createElement('span');
        name.className = 'addon__name';
        name.textContent = addon.name;
        var price = document.createElement('span');
        price.className = 'addon__price';
        price.textContent = '+' + money(addon.price);
        label.appendChild(input);
        label.appendChild(name);
        label.appendChild(price);
        addonBox.appendChild(label);
        input.addEventListener('change', recalc);
      });
    }

    function recalc() {
      var service = currentService();
      var chosen = $$('input:checked', addonBox);
      var total = service.basePrice;
      var parts = [];

      lines.innerHTML = '';

      if (service.basePrice > 0) {
        parts.push(service.name);
        addLine(DATA.t.lineBase + ' \u00b7 ' + service.name, money(service.basePrice));
      }
      chosen.forEach(function (input) {
        var price = Number(input.getAttribute('data-price'));
        total += price;
        parts.push(input.getAttribute('data-name'));
        addLine(input.getAttribute('data-name'), '+' + money(price));
      });

      if (service.basePrice > 0) {
        totalOut.classList.remove('is-text');
        totalOut.textContent = money(total);
        noteOut.textContent = DATA.t.vatNote;
      } else {
        totalOut.classList.add('is-text');
        totalOut.textContent = service.priceModel || DATA.t.priceCustom;
        noteOut.textContent = DATA.t.variableNote;
      }
      flash(totalOut);

      maintOut.textContent = service.maintenance > 0
        ? DATA.t.maintenanceLabel + ': ' + money(service.maintenance) + DATA.t.perMonth
        : '';
      maintOut.hidden = service.maintenance <= 0;

      docket.setAttribute('data-total', service.basePrice > 0 ? total : 0);
      docket.setAttribute('data-summary', buildSummary(service, parts, total));
    }

    function addLine(label, value) {
      var row = document.createElement('div');
      row.className = 'ledger__row';
      var dt = document.createElement('dt');
      dt.textContent = label;
      var dd = document.createElement('dd');
      dd.textContent = value;
      row.appendChild(dt);
      row.appendChild(dd);
      lines.appendChild(row);
    }

    function buildSummary(service, parts, total) {
      var extras = parts.slice(1);
      var out = DATA.t.messageIntro + '\n' + DATA.t.messageService + ': ' + service.name;
      if (extras.length) { out += '\n' + DATA.t.messageAddons + ': ' + extras.join(', '); }
      out += '\n' + DATA.t.messageTotal + ': ' +
        (service.basePrice > 0 ? money(total) : (service.priceModel || DATA.t.priceCustom));
      return out;
    }

    $$('input[name="docket-service"]', docket).forEach(function (radio) {
      radio.addEventListener('change', function () {
        renderAddons(currentService());
        recalc();
      });
    });

    if (sendForm) {
      sendForm.addEventListener('click', function (ev) {
        ev.preventDefault();
        var need = $('#f-need');
        if (need) {
          need.value = docket.getAttribute('data-summary') || '';
          need.dispatchEvent(new Event('input'));
        }
        var target = $('#contact');
        if (target) { target.scrollIntoView({ block: 'start' }); }
        window.setTimeout(function () { var n = $('#f-name'); if (n) { n.focus(); } }, 420);
      });
    }

    if (sendWa) {
      sendWa.addEventListener('click', function (ev) {
        ev.preventDefault();
        window.open(DATA.whatsappBase + encodeURIComponent(docket.getAttribute('data-summary') || ''), '_blank', 'noopener');
      });
    }

    renderAddons(currentService());
    recalc();
  }

  /* ------------------------------------------------------------------ *
   * 4. Contact form
   * ------------------------------------------------------------------ */
  function initForm() {
    var form = $('#contact-form');
    if (!form) { return; }

    var alertBox = $('#form-alert');
    var successBox = $('#form-success');
    var submitBtn = $('#form-submit');
    var loadedAt = Date.now();

    var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
    var PHONE = /^[+()\d][\d\s().-]{6,}$/;

    function setError(fieldId, message) {
      var field = $('[data-field="' + fieldId + '"]');
      if (!field) { return; }
      field.setAttribute('data-invalid', message ? 'true' : 'false');
      var slot = $('.err', field);
      if (slot) { slot.textContent = message || ''; }
      var input = $('input, textarea', field);
      if (input) { input.setAttribute('aria-invalid', message ? 'true' : 'false'); }
    }

    ['name', 'need', 'contact'].forEach(function (id) {
      var input = $('#f-' + id);
      if (input) { input.addEventListener('input', function () { setError(id, ''); }); }
    });

    function validate() {
      var ok = true;
      var name = $('#f-name').value.trim();
      var need = $('#f-need').value.trim();
      var contact = $('#f-contact').value.trim();
      var consent = $('#f-consent').checked;

      if (name.length < 2) { setError('name', DATA.t.errName); ok = false; }
      if (need.length < 6) { setError('need', DATA.t.errNeed); ok = false; }
      if (!contact) { setError('contact', DATA.t.errContact); ok = false; }
      else if (!EMAIL.test(contact) && !PHONE.test(contact)) { setError('contact', DATA.t.errContactFormat); ok = false; }
      if (!consent) { setError('consent', DATA.t.errConsent); ok = false; }
      return ok;
    }

    function showAlert(message) {
      if (!alertBox) { return; }
      alertBox.textContent = message;
      alertBox.setAttribute('data-show', message ? 'true' : 'false');
    }

    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      showAlert('');

      if ($('#' + DATA.honeypotField) && $('#' + DATA.honeypotField).value) { return; }
      if ((Date.now() - loadedAt) < DATA.minFillSeconds * 1000) { showAlert(DATA.t.errTooFast); return; }
      if (!validate()) { return; }

      if (!DATA.formEndpoint) {
        window.location.href = DATA.mailtoFallback + encodeURIComponent(
          $('#f-name').value + '\n\n' + $('#f-need').value + '\n\n' + $('#f-contact').value
        );
        return;
      }

      submitBtn.setAttribute('data-busy', 'true');
      submitBtn.textContent = DATA.t.submitting;

      fetch(DATA.formEndpoint, {
        method: 'POST',
        headers: { 'Accept': 'application/json' },
        body: new FormData(form)
      }).then(function (res) {
        if (!res.ok) { throw new Error('bad status'); }
        form.hidden = true;
        successBox.setAttribute('data-show', 'true');
        successBox.setAttribute('tabindex', '-1');
        successBox.focus();
      }).catch(function () {
        showAlert(DATA.t.errNetwork);
      }).finally(function () {
        submitBtn.removeAttribute('data-busy');
        submitBtn.textContent = DATA.t.submit;
      });
    });
  }

  /* ------------------------------------------------------------------ *
   * 5. Scroll reveal
   * ------------------------------------------------------------------ */
  function initReveal() {
    var targets = $$('.reveal');
    if (!targets.length) { return; }
    if (!('IntersectionObserver' in window) ||
        window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      targets.forEach(function (t) { t.classList.add('is-in'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    targets.forEach(function (t) { io.observe(t); });
  }

  initLanguage();
  initNav();
  initQuote();
  initForm();
  initReveal();
})();
