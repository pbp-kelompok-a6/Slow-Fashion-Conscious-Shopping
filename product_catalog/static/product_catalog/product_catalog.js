/* Progressive enhancement for catalog/wishlist; native GET/POST forms are the fallback. */
(() => {
  'use strict';
  if (!window.fetch || !window.DOMParser || !window.AbortController) return;
  const page = () => document.querySelector('.pc-page[data-json-url]');
  if (document.documentElement.dataset.pcAjax) return;
  document.documentElement.dataset.pcAjax = 'true';
  const writes = new Set();
  const locks = new Set();
  let controller;
  let sequence = 0;
  let revision = 0;
  let timer;

  function feedback(message, error = false) {
    let box = document.querySelector('.pc-feedback');
    if (!box) {
      box = document.createElement('div');
      box.className = 'pc-feedback';
      box.setAttribute('role', 'status');
      box.setAttribute('aria-live', 'polite');
      document.body.append(box);
    }
    box.textContent = message;
    box.classList.toggle('pc-feedback-error', error);
    box.hidden = false;
    clearTimeout(timer);
    timer = setTimeout(() => { box.hidden = true; }, error ? 8000 : 3500);
  }

  async function json(url, options = {}) {
    const response = await fetch(url, {
      credentials: 'same-origin', ...options,
      headers: {Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest', ...options.headers},
    });
    if (response.redirected) {
      // Django login_required preserves the ordinary authentication flow.
      const target = new URL(response.url);
      if (target.origin === location.origin) {
        target.searchParams.set('next', location.pathname + location.search);
        location.assign(target);
      }
      throw new Error('Silakan masuk terlebih dahulu.');
    }
    const type = response.headers.get('Content-Type') || '';
    if (!type.includes('application/json')) {
      throw new Error(response.status === 403 ? 'Akses ditolak atau sesi CSRF berakhir. Muat ulang halaman.' : 'Server gagal memproses permintaan. Coba lagi.');
    }
    const result = await response.json();
    if (!response.ok || !result.success) {
      const errors = result.errors?.note?.map(item => item.message).join(' ');
      throw new Error(errors || result.message || 'Permintaan gagal.');
    }
    return result;
  }

  function prepareNotes() {
    page()?.querySelectorAll('.pc-note-form').forEach(form => {
      if (form.dataset.enhanced) return;
      form.dataset.enhanced = 'true';
      const fields = form.querySelector('[data-note-fields]');
      const text = form.querySelector('[data-note-text]');
      const input = form.elements.note;
      const save = form.querySelector('[type="submit"]');
      if (!fields || !text || !input || !save) return;
      let saved = input.value;
      const edit = document.createElement('button');
      edit.type = 'button'; edit.className = 'pc-text-link pc-note-edit'; edit.textContent = 'Edit catatan';
      const cancel = document.createElement('button');
      cancel.type = 'button'; cancel.className = 'pc-text-link pc-note-edit'; cancel.textContent = 'Batal';
      const setEditing = editing => {
        fields.hidden = save.hidden = cancel.hidden = !editing;
        text.hidden = edit.hidden = editing;
        if (editing) input.focus();
      };
      edit.addEventListener('click', () => setEditing(true));
      cancel.addEventListener('click', () => { input.value = saved; setEditing(false); });
      form.addEventListener('pc:note-saved', event => {
        saved = event.detail; input.value = saved;
        text.textContent = saved || 'Belum ada catatan.';
        setEditing(false);
      });
      form.append(edit, cancel);
      // Keep server-side validation errors visible if the page was rendered after invalid POST.
      setEditing(Boolean(fields.querySelector('.errorlist')));
    });
  }

  function setHearts(id, active) {
    if (active) initialIds.add(String(id)); else initialIds.delete(String(id));
    document.querySelectorAll('[data-product-id]').forEach(card => {
      if (String(card.dataset.productId) !== String(id)) return;
      const heart = card.querySelector('button.pc-heart');
      if (!heart) return;
      heart.classList.toggle('pc-saved', active);
      heart.setAttribute('aria-pressed', String(active));
      heart.setAttribute('aria-label', active ? 'Hapus dari wishlist' : 'Simpan ke wishlist');
      const desired = heart.form?.elements.in_wishlist;
      if (desired) desired.value = String(!active);
    });
  }

  function removeCards(id, count) {
    const current = page();
    if (!current?.classList.contains('pc-wishlist')) return;
    current.querySelectorAll('[data-product-id]').forEach(card => {
      if (String(card.dataset.productId) === String(id)) {
        const hadFocus = card.contains(document.activeElement);
        const next = card.nextElementSibling || card.previousElementSibling;
        card.remove();
        if (hadFocus) {
          const target = next?.querySelector('a, button') || current.querySelector('h1');
          if (target) { target.tabIndex = target.matches('h1') ? -1 : target.tabIndex; target.focus(); }
        }
      }
    });
    current.querySelector('[data-wishlist-count]').textContent = `${count} barang tersimpan`;
    const grid = current.querySelector('.pc-wishlist-grid');
    if (!grid.querySelector('.pc-card') && !grid.querySelector('.pc-empty')) {
      const empty = document.createElement('p'); empty.className = 'pc-empty';
      empty.textContent = new URL(location.href).searchParams.get('category') ? 'Belum ada barang di kategori ini.' : 'Wishlist masih kosong. Simpan produk melalui katalog.';
      grid.append(empty);
    }
  }

  async function reconcile() {
    const result = await json(config.json_url);
    const ids = new Set(result.wishlist_product_ids.map(String));
    initialIds.clear(); ids.forEach(id => initialIds.add(id));
    document.querySelectorAll('[data-product-id]').forEach(card => {
      const id = card.dataset.productId;
      setHearts(id, ids.has(id));
      if (!ids.has(id)) removeCards(id, result.count);
    });
  }

  async function navigate(target, push = true) {
    const url = new URL(target, location.href);
    const current = page();
    if (!current || url.origin !== location.origin) return;
    const ticket = ++sequence;
    controller?.abort();
    controller = new AbortController();
    const signal = controller.signal;
    current.setAttribute('aria-busy', 'true');
    const status = document.createElement('p');
    status.className = 'pc-request-status'; status.setAttribute('role', 'status'); status.textContent = 'Memuat produk…';
    current.prepend(status);
    try {
      await Promise.allSettled([...writes]);
      if (ticket !== sequence) return;
      const version = revision;
      const endpoint = new URL(current.dataset.jsonUrl, location.origin);
      endpoint.search = url.search;
      const result = await json(endpoint, {signal});
      if (ticket !== sequence) return;
      if (writes.size || version !== revision) { await navigate(url, push); return; }
      const doc = new DOMParser().parseFromString(result.html, 'text/html');
      const replacement = doc.querySelector('.pc-page[data-json-url]');
      if (!replacement) throw new Error('Halaman tidak dapat diperbarui.');
      const focused = document.activeElement;
      const focusName = focused?.name;
      const focusValue = focused?.value;
      current.replaceWith(replacement);
      if (push && url.href !== location.href) history.pushState(null, '', url);
      prepareNotes();
      if (focusName) {
        [...replacement.querySelectorAll('input, select')].find(input => input.name === focusName && input.value === focusValue)?.focus({preventScroll: true});
      } else {
        const heading = replacement.querySelector('h1');
        heading?.setAttribute('tabindex', '-1'); heading?.focus({preventScroll: true});
      }
    } catch (error) {
      if (error.name !== 'AbortError' && ticket === sequence) {
        feedback(error.message || 'Gagal terhubung ke server. Coba lagi.', true);
      }
    } finally {
      status.remove();
      if (ticket === sequence) page()?.removeAttribute('aria-busy');
    }
  }

  async function mutate(form) {
    const card = form.closest('[data-product-id]');
    const key = card?.dataset.productId;
    if (!key || locks.has(key)) return;
    locks.add(key); revision++;
    const controls = [...card.querySelectorAll('button, input')];
    const previous = controls.map(control => control.disabled);
    const body = new FormData(form);
    const toggle = form.hasAttribute('data-wishlist-toggle');
    if (toggle) body.set('in_wishlist', String(form.querySelector('button.pc-heart').getAttribute('aria-pressed') !== 'true'));
    controls.forEach(control => { control.disabled = true; });
    card.setAttribute('aria-busy', 'true');
    try {
      const result = await json(form.action, {
        method: 'POST', body,
        headers: {'X-CSRFToken': form.querySelector('[name="csrfmiddlewaretoken"]').value},
      });
      if (result.in_wishlist !== undefined) {
        setHearts(result.product_id, result.in_wishlist);
        if (!result.in_wishlist) removeCards(result.product_id, result.count);
      }
      if (result.note !== undefined) form.dispatchEvent(new CustomEvent('pc:note-saved', {detail: result.note}));
      feedback(result.message);
    } catch (error) {
      feedback(error.message || 'Gagal terhubung ke server. Coba lagi.', true);
      // A POST may have reached the server even when its response was lost.
      if (!form.classList.contains('pc-note-form')) {
        try { await reconcile(); } catch { /* Keep the last confirmed UI and the visible error. */ }
      }
    } finally {
      controls.forEach((control, index) => { control.disabled = previous[index]; });
      card.removeAttribute('aria-busy');
      locks.delete(key); revision++;
    }
  }

  function filterUrl(form) {
    const url = new URL(form.action);
    const params = new URLSearchParams();
    new FormData(form).forEach((value, key) => { if (value !== '') params.append(key, value); });
    url.search = params.toString();
    return url;
  }

  document.addEventListener('submit', event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.id === 'katalog-filter') {
      event.preventDefault(); navigate(filterUrl(form));
    } else if (form.matches('[data-wishlist-toggle], .pc-note-form, .pc-remove-form')) {
      event.preventDefault();
      const task = mutate(form);
      writes.add(task);
      task.finally(() => writes.delete(task));
    }
  });
  document.addEventListener('change', event => {
    const input = event.target;
    if (page()?.contains(input) && input.form?.id === 'katalog-filter') {
      input.form.requestSubmit();
    }
  });
  document.addEventListener('click', event => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest('a');
    if (!link || !page()?.contains(link) || link.target || link.hasAttribute('download')) return;
    const url = new URL(link.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname) return;
    if (!link.closest('.pc-pagination, .pc-active-filters, .pc-sidebar, .pc-categories, .pc-empty')) return;
    event.preventDefault(); navigate(url);
  });
  window.addEventListener('popstate', () => navigate(location.href, false));
  window.addEventListener('pageshow', event => {
    if (!event.persisted) return;
    if (page()) navigate(location.href, false);
    else if (config.authenticated) reconcile().catch(error => feedback(error.message, true));
  });
  // Dynamic store cards use the same explicit-state form and delegated handler.
  const config = JSON.parse(document.getElementById('wishlist-data')?.textContent || '{}');
  const initialIds = new Set((config.ids || []).map(String));
  document.addEventListener('lapakaian:card-rendered', event => {
    const {card, product} = event.detail;
    const active = initialIds.has(String(product.id));
    if (!config.authenticated) {
      if (!product.is_available) return;
      const link = document.createElement('a');
      link.className = 'pc-heart'; link.textContent = '\u2661';
      link.href = config.login_url + '?next=' + encodeURIComponent(location.pathname + location.search);
      link.setAttribute('aria-label', 'Masuk untuk menyimpan ke wishlist');
      card.querySelector('.product-media').append(link);
      return;
    }
    if (!active && !product.is_available) return;
    const template = document.getElementById('wishlist-form-template');
    if (!template) return;
    const form = template.content.firstElementChild.cloneNode(true);
    form.action = config.toggle_url.replace('/0/', '/' + product.id + '/');
    form.dataset.productId = product.id;
    form.elements.next.value = location.pathname + location.search;
    form.elements.in_wishlist.value = String(!active);
    const button = form.querySelector('button');
    button.classList.toggle('pc-saved', active);
    button.setAttribute('aria-pressed', String(active));
    button.setAttribute('aria-label', active ? 'Hapus dari wishlist' : 'Simpan ke wishlist');
    card.querySelector('.product-media').append(form);
  });
  prepareNotes();
})();
