/* Existing endpoints enforce ownership and CSRF; this file enhances their UI. */
(() => {
  'use strict';
  document.querySelector('#category-filter select')?.addEventListener('change', event => event.target.form.requestSubmit());
  document.querySelectorAll('.gallery-thumb').forEach(button => {
    button.addEventListener('click', () => {
      const main = document.getElementById('gallery-main-img');
      main.src = button.dataset.src; main.alt = button.dataset.alt;
      document.querySelectorAll('.gallery-thumb').forEach(item => {
        item.classList.toggle('active', item === button);
        item.setAttribute('aria-pressed', String(item === button));
      });
    });
  });
  document.addEventListener('click', async event => {
    const button = event.target.closest('[data-delete], [data-status-toggle]');
    if (!button || button.disabled) return;
    const deleting = button.hasAttribute('data-delete');
    if (deleting && !await confirmDialog(`Hapus ${button.dataset.name}?`, {danger: true, confirmText: 'Hapus'})) return;
    const container = button.closest('[data-product-row], #owner-actions');
    if (container.dataset.pending) return;
    container.dataset.pending = 'true';
    const controls = [...container.querySelectorAll('button')];
    controls.forEach(control => { control.disabled = true; });
    try {
      const url = deleting ? button.dataset.url : button.dataset.status === 'active' ? button.dataset.soldUrl : button.dataset.activeUrl;
      const result = await postJSON(url);
      if (!result.success) { showToast(result.message, 'error'); return; }
      showToast(result.message);
      if (deleting && container.id === 'owner-actions') { location.assign(result.redirect_url); return; }
      if (deleting) container.remove();
      else {
        button.dataset.status = result.status;
        button.textContent = result.status === 'active' ? 'Tandai Sold' : 'Tandai Aktif';
        container.dataset.status = result.status;
        const badge = container.querySelector('[data-status-badge]') || document.querySelector('[data-status-badge]');
        if (badge) {
          badge.textContent = result.status_display;
          badge.classList.toggle('badge-sold', result.status === 'sold');
          badge.classList.toggle('badge-active', result.status === 'active');
          if (container.id === 'owner-actions') badge.hidden = result.status !== 'sold';
        }
        const selected = document.getElementById('my-listings')?.dataset.selectedStatus;
        if (selected && selected !== result.status) container.remove();
        // Availability and wishlist controls on detail depend on the new status.
        if (container.id === 'owner-actions') { location.reload(); return; }
      }
      Object.entries(result.counts || {}).forEach(([key, value]) => {
        document.querySelectorAll(`[data-count="${key}"]`).forEach(item => { item.textContent = value; });
      });
      const empty = !document.querySelector('[data-product-row]');
      const emptyBox = document.getElementById('listing-empty');
      const header = document.querySelector('.listing-row-head');
      if (emptyBox) emptyBox.hidden = !empty;
      if (header) header.hidden = empty;
    } finally {
      controls.forEach(control => { control.disabled = false; });
      delete container.dataset.pending;
    }
  });

  const slots = [...document.querySelectorAll('[data-photo-slot]')];
  const update = slot => {
    const input = slot.querySelector('input[type="file"]');
    const image = slot.querySelector('.photo-preview');
    const placeholder = slot.querySelector('.photo-slot-empty');
    const deletion = slot.querySelector('input[type="checkbox"]');
    if (slot.dataset.previewUrl) { URL.revokeObjectURL(slot.dataset.previewUrl); delete slot.dataset.previewUrl; }
    if (!slot.dataset.original) slot.dataset.original = image.getAttribute('src') || '';
    if (input.files[0] && !deletion?.checked) {
      slot.dataset.previewUrl = URL.createObjectURL(input.files[0]); image.src = slot.dataset.previewUrl;
    } else if (slot.dataset.original) image.src = slot.dataset.original;
    image.hidden = Boolean(deletion?.checked) || (!input.files.length && !slot.dataset.original);
    placeholder.hidden = !image.hidden;
    slot.classList.toggle('filled', !image.hidden);
    const clear = slot.querySelector('.photo-clear');
    if (clear) clear.hidden = !input.files.length;
  };
  slots.forEach(slot => {
    slot.querySelector('input[type="file"]').addEventListener('change', () => update(slot));
    slot.querySelector('input[type="checkbox"]')?.addEventListener('change', () => update(slot));
    slot.querySelector('.photo-clear')?.addEventListener('click', () => {
      slot.querySelector('input[type="file"]').value = ''; update(slot);
    });
    update(slot);
  });
  document.getElementById('photo-pick')?.addEventListener('click', () => {
    const slot = slots.find(item => !item.dataset.original && !item.querySelector('input[type="file"]').files.length);
    if (slot) slot.querySelector('input[type="file"]').click();
    else showToast('Maksimal lima foto. Hapus foto lama dan simpan sebelum menambah foto baru.', 'error');
  });
  const drop = document.getElementById('photo-drop');
  drop?.addEventListener('dragover', event => event.preventDefault());
  drop?.addEventListener('drop', event => {
    event.preventDefault();
    for (const file of event.dataTransfer.files) {
      const slot = slots.find(item => !item.dataset.original && !item.querySelector('input[type="file"]').files.length);
      if (!slot) { showToast('Maksimal lima foto.', 'error'); break; }
      const transfer = new DataTransfer(); transfer.items.add(file);
      slot.querySelector('input[type="file"]').files = transfer.files; update(slot);
    }
  });
  window.addEventListener('pagehide', () => slots.forEach(slot => { if (slot.dataset.previewUrl) URL.revokeObjectURL(slot.dataset.previewUrl); }));
})();
