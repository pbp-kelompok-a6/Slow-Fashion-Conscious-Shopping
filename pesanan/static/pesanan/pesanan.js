/* One delegated handler survives DOMParser updates. Phase 4 JSON stays intact. */
(() => {
  'use strict';
  if (!window.fetch || !window.DOMParser || document.documentElement.dataset.pesanan) return;
  document.documentElement.dataset.pesanan = 'true';
  const config = document.getElementById('pesanan-config');
  if (!config) return;
  const cfg = config.dataset;
  const root = () => document.querySelector('[data-ps-page]');
  const locks = new Set();
  let cartRequest = null;
  let controller;
  let sequence = 0;
  let checkoutBusy = false;
  let checkoutStore;
  let checkoutRunner;

  function feedback(message, link, label) {
    let box = document.getElementById('ps-feedback');
    if (!box) {
      box = document.createElement('div'); box.id = 'ps-feedback'; box.className = 'ps-feedback';
      box.setAttribute('role', 'status'); box.setAttribute('aria-live', 'polite');
      document.body.append(box);
    }
    box.replaceChildren();
    const text = document.createElement('p'); text.textContent = message; box.append(text);
    if (link) {
      const anchor = document.createElement('a'); anchor.href = link; anchor.textContent = label || 'Muat ulang'; box.append(anchor);
    }
    const close = document.createElement('button'); close.type = 'button'; close.textContent = 'Tutup';
    close.addEventListener('click', () => { box.hidden = true; }); box.append(close); box.hidden = false;
  }

  function csrf() {
    const cookie = document.cookie.split('; ').find(value => value.startsWith('csrftoken='));
    return cookie ? decodeURIComponent(cookie.slice(10)) : config.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
  }

  async function request(url, options = {}) {
    let response;
    const timeout = options.signal ? null : new AbortController();
    const timer = timeout ? setTimeout(() => timeout.abort(), 20000) : null;
    try {
      response = await fetch(url, {credentials: 'same-origin', cache: 'no-store', signal: timeout?.signal, ...options,
        headers: {Accept: 'application/json', ...(options.method === 'POST' ? {'Content-Type': 'application/json', 'X-CSRFToken': csrf()} : {}), ...options.headers}});
    } catch (cause) {
      if (options.signal && cause.name === 'AbortError') throw cause;
      const error = new Error('Jaringan gagal. Coba kembali; data percobaan checkout tetap disimpan.'); error.cause = cause; throw error;
    } finally { clearTimeout(timer); }
    if (response.status === 401 || response.redirected) {
      const target = new URL(cfg.login, location.origin); target.searchParams.set('next', location.pathname + location.search);
      location.assign(target.href);
      throw Object.assign(new Error('Sesi berakhir. Silakan masuk kembali.'), {status: 401});
    }
    if (!response.headers.get('Content-Type')?.includes('application/json')) {
      throw Object.assign(new Error(response.status === 403 ? 'Akses ditolak atau token CSRF berakhir. Muat ulang halaman sebelum mencoba kembali.' : 'Respons server belum dapat dikonfirmasi. Coba kembali dengan percobaan yang sama.'), {status: response.status >= 500 || response.status === 403 ? response.status : 0});
    }
    let result;
    try { result = await response.json(); }
    catch { throw new Error('Respons server tidak lengkap. Coba kembali dengan percobaan yang sama.'); }
    if (!response.ok || !result.success) {
      throw Object.assign(new Error(result.message || (response.status === 404 ? 'Data tidak ditemukan atau Anda tidak memiliki akses.' : response.status === 403 ? 'Akses ditolak. Muat ulang halaman.' : 'Periksa kembali data yang diisi.')), {status: response.status, code: result.code, errors: result.errors});
    }
    return result;
  }

  function showError(error) {
    feedback(error.message, error.status === 403 ? location.href : undefined, 'Muat ulang halaman');
  }

  function selected() {
    const form = document.getElementById('ps-selection');
    if (!form || !form.querySelector('[data-selection-count]')) return;
    const count = form.querySelectorAll('[name=product_ids]:checked:not(:disabled)').length;
    form.querySelector('[data-selection-count]').textContent = `${count} barang dipilih`;
    form.querySelector('[data-selection-submit]').disabled = !count;
  }

  function updateSlots(result) {
    const available = result.items.filter(item => item.available).length;
    document.querySelectorAll('[data-cart-count]').forEach(badge => {
      badge.textContent = available; badge.setAttribute('aria-label', `${available} barang bisa dibeli`);
    });
    const ids = new Set(result.items.map(item => String(item.product_id)));
    document.querySelectorAll('[data-cart-slot]').forEach(slot => {
      if (slot.dataset.owner === 'true' || slot.dataset.availability !== 'Tersedia') return;
      const saved = ids.has(slot.dataset.productId);
      const link = slot.querySelector('[data-in-cart]');
      const form = slot.querySelector('[data-cart-add]');
      if (saved) {
        if (form) form.hidden = true;
        if (!link) {
          // A slot initially rendered as already-in-cart also has an ordinary
          // server link. Reuse it instead of appending duplicate controls.
          const existing = slot.querySelector('a');
          if (existing) existing.dataset.inCart = 'true';
          else {
            const anchor = document.createElement('a'); anchor.dataset.inCart = 'true';
            anchor.className = 'btn-outline'; anchor.href = cfg.cartPage; anchor.textContent = 'Di keranjang'; slot.append(anchor);
          }
        }
      } else if (link) {
        link.remove();
        if (form) form.hidden = false;
        else refreshSlots().catch(showError);
      }
    });
    return result;
  }

  function syncCart() {
    if (!cfg.userId) return Promise.resolve(null);
    if (!cartRequest) cartRequest = request(cfg.cartApi).then(updateSlots).finally(() => { cartRequest = null; });
    return cartRequest;
  }

  let slotRequest;
  function refreshSlots() {
    if (slotRequest) return slotRequest;
    slotRequest = (async () => {
      const response = await fetch(location.href, {credentials: 'same-origin', cache: 'no-store', headers: {Accept: 'text/html'}});
      if (!response.ok || response.redirected) return;
      const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
      document.querySelectorAll('[data-cart-slot]').forEach(slot => {
        const fresh = [...doc.querySelectorAll('[data-cart-slot]')].find(item => item.dataset.productId === slot.dataset.productId);
        if (fresh) slot.replaceWith(fresh.cloneNode(true));
      });
      const detail = document.querySelector('.product-detail');
      if (detail) {
        const freshDetail = doc.querySelector('.product-detail');
        const badge = detail.querySelector('[data-status-badge]');
        const freshBadge = freshDetail?.querySelector('[data-status-badge]');
        if (badge && freshBadge) badge.replaceWith(freshBadge.cloneNode(true));
        const gallery = detail.querySelector('.gallery-main');
        if (gallery) gallery.classList.toggle('is-sold', Boolean(freshDetail?.querySelector('.gallery-main.is-sold')));
        const toggle = detail.querySelector('[data-status-toggle]');
        const freshToggle = freshDetail?.querySelector('[data-status-toggle]');
        if (toggle && freshToggle) { toggle.dataset.status = freshToggle.dataset.status; toggle.textContent = freshToggle.textContent; }
      }
    })().finally(() => { slotRequest = null; });
    return slotRequest;
  }

  async function navigate(target = location.href, push = false, focus = false) {
    const current = root();
    if (!current || current.dataset.psPage === 'checkout') return;
    const url = new URL(target, location.href);
    if (url.origin !== location.origin) return;
    const ticket = ++sequence;
    controller?.abort(); controller = new AbortController();
    const checked = new Set([...current.querySelectorAll('[name=product_ids]:checked')].map(input => input.value));
    current.setAttribute('aria-busy', 'true');
    try {
      const result = await request(url, {signal: controller.signal});
      if (ticket !== sequence) return;
      const doc = new DOMParser().parseFromString(result.html, 'text/html');
      const replacement = doc.querySelector('[data-ps-page]');
      if (!replacement) throw new Error('Halaman gagal diperbarui. Muat ulang halaman.');
      if (current.dataset.psPage === 'cart') replacement.querySelectorAll('[name=product_ids]').forEach(input => { input.checked = !input.disabled && checked.has(input.value); });
      current.replaceWith(replacement);
      if (push && url.href !== location.href) history.pushState(null, '', url);
      selected();
      if (focus) { const heading = replacement.querySelector('h1'); heading.tabIndex = -1; heading.focus({preventScroll: true}); }
    } catch (error) { if (error.name !== 'AbortError' && ticket === sequence) showError(error); }
    finally { if (ticket === sequence) root()?.removeAttribute('aria-busy'); }
  }

  function recovery(saved) {
    const panel = document.querySelector('[data-checkout-recovery]');
    if (panel) panel.hidden = !saved;
    document.querySelectorAll('[data-checkout-new]').forEach(item => { item.hidden = Boolean(saved); });
  }

  function setupCheckout() {
    if (root()?.dataset.psPage !== 'checkout') return;
    try {
      checkoutStore = window.PesananCheckout.attemptStore(sessionStorage, cfg.userId);
      recovery(checkoutStore.load());
      checkoutRunner = window.PesananCheckout.runner(checkoutStore, payload => request(cfg.checkoutApi, {method: 'POST', body: JSON.stringify(payload)}));
    } catch (error) {
      // Preserve the native form fallback when sessionStorage is unavailable.
      checkoutRunner = null; feedback(error.message || 'Penyimpanan browser tidak tersedia. Gunakan form biasa.');
    }
  }

  function displayFields(errors) {
    document.querySelectorAll('[data-field-error]').forEach(box => { box.textContent = ''; });
    if (!errors) return;
    for (const [name, entries] of Object.entries(errors)) {
      const box = [...document.querySelectorAll('[data-field-error]')].find(item => item.dataset.fieldError === name);
      if (box) box.textContent = entries.map(entry => entry.message).join(' ');
    }
    document.querySelector('[data-field-error]:not(:empty)')?.closest('.ps-field')?.querySelector('input, textarea')?.focus();
  }

  async function submitCheckout(payload) {
    if (checkoutBusy) return;
    checkoutBusy = true;
    const buttons = [...document.querySelectorAll('[data-checkout-submit], [data-checkout-retry]')];
    const labels = buttons.map(button => button.textContent);
    buttons.forEach(button => { button.disabled = true; button.textContent = 'Memproses…'; });
    document.querySelector('[data-checkout-form]')?.setAttribute('aria-busy', 'true');
    displayFields(null);
    try {
      const result = await checkoutRunner.send(payload);
      // Success is not inferred from the cart becoming empty; it must be the
      // server's successful response to this exact idempotent attempt.
      const first = result.orders[0];
      location.assign(cfg.successUrl.replace('/0/', `/${first.id}/`));
    } catch (error) {
      let saved;
      try { saved = checkoutStore.load(); } catch { saved = true; }
      recovery(saved);
      displayFields(error.errors);
      if (['quote_changed', 'quote_invalid', 'product_conflict', 'unavailable', 'not_in_cart', 'idempotency_conflict'].includes(error.code)) {
        document.querySelector('[data-checkout-form]')?.querySelectorAll('button[type=submit]').forEach(button => { button.dataset.needsQuote = 'true'; });
        feedback(error.message + ' Periksa ringkasan terbaru sebelum konfirmasi lagi.', location.href, 'Perbarui ringkasan');
      } else showError(error);
    } finally {
      buttons.forEach((button, index) => { button.disabled = button.dataset.needsQuote === 'true'; button.textContent = labels[index]; });
      document.querySelector('[data-checkout-form]')?.removeAttribute('aria-busy');
      checkoutBusy = false;
    }
  }

  document.addEventListener('submit', event => {
    const form = event.target;
    if (form.matches('[data-checkout-form]') && checkoutRunner) {
      const data = new FormData(form);
      const payload = Object.fromEntries(data.entries());
      delete payload.csrfmiddlewaretoken;
      payload.product_ids = data.getAll('product_ids');
      // Persist before preventing native submit. If storage is blocked/full,
      // submit the ordinary form with its hidden idempotency key instead.
      try { if (!checkoutStore.load()) checkoutStore.save(payload); }
      catch { return; }
      event.preventDefault(); submitCheckout(payload);
    } else if (form.matches('[data-cart-add], [data-cart-remove], [data-order-action]')) {
      event.preventDefault();
      const action = form.hasAttribute('data-cart-add') ? 'add' : form.hasAttribute('data-cart-remove') ? 'remove' : 'order';
      const id = form.elements.product_id?.value;
      const key = action === 'order' ? form.dataset.api : `cart:${id}`;
      if (locks.has(key)) return;
      if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) return;
      locks.add(key);
      const controls = [...form.querySelectorAll('button'), ...document.querySelectorAll('button[form]')].filter(button => button.form === form);
      controls.forEach(button => { button.disabled = true; }); form.setAttribute('aria-busy', 'true');
      const url = action === 'order' ? form.dataset.api : action === 'add' ? cfg.addApi : cfg.removeApi;
      request(url, {method: 'POST', body: JSON.stringify(action === 'order' ? {} : {product_id: id})})
        .then(async () => {
          // Wait out any stale badge read before asking for the new state.
          await cartRequest?.catch(() => {});
          await syncCart();
          if (root()) await navigate(location.href, false, true);
          else await refreshSlots();
          feedback(action === 'add' ? 'Ditambahkan ke keranjang.' : action === 'remove' ? 'Dihapus dari keranjang.' : 'Status pesanan diperbarui.');
        }).catch(async error => {
          showError(error);
          if (error.status === 409 || error.status === 404) {
            if (root()) await navigate(); else await refreshSlots().catch(showError);
            await syncCart().catch(() => {});
          }
        }).finally(() => { controls.forEach(button => { button.disabled = false; }); form.removeAttribute('aria-busy'); locks.delete(key); });
    } else if (form.matches('[data-order-filter]')) {
      event.preventDefault(); const url = new URL(location.href); url.search = new URLSearchParams(new FormData(form)); navigate(url, true, true);
    }
  });
  document.addEventListener('change', event => {
    if (event.target.matches('#ps-selection [name=product_ids]')) selected();
    if (event.target.matches('[data-order-filter] select')) event.target.form.requestSubmit();
  });
  document.addEventListener('click', event => {
    if (event.target.closest('[data-checkout-retry]')) {
      try { submitCheckout(checkoutStore.load()); } catch (error) { showError(error); }
    }
    const link = event.target.closest('[data-ps-nav]');
    if (link && event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
      event.preventDefault(); navigate(link.href, true, true);
    }
    const thumb = event.target.closest('.gallery-thumb');
    if (thumb) {
      const main = document.getElementById('gallery-main-img');
      if (main) { main.src = thumb.dataset.src; main.alt = thumb.dataset.alt; }
    }
  });
  window.addEventListener('popstate', () => navigate());
  window.addEventListener('pageshow', event => {
    if (event.persisted) {
      setupCheckout(); syncCart().catch(showError);
      if (root()) navigate(); else if (document.querySelector('[data-cart-slot]')) refreshSlots().catch(showError);
    }
  });
  // Fragments contain markup only. Delegation is already installed; reconcile
  // cart state when the catalog module replaces its page after DOMParser.
  new MutationObserver(records => {
    if (records.some(record => [...record.addedNodes].some(node => node.nodeType === 1 && node.matches('.pc-page')))) syncCart().catch(showError);
  }).observe(document.querySelector('main'), {childList: true, subtree: true});
  selected(); setupCheckout();
})();
