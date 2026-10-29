/* Shared retry state is also exercised by node --test; no browser dependency. */
((root, factory) => {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PesananCheckout = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  'use strict';
  const fields = ['recipient_name', 'phone', 'address', 'payment_method', 'idempotency_key', 'quote_token'];
  function validId(id) {
    if (typeof id === 'number') return Number.isSafeInteger(id) && id > 0;
    return typeof id === 'string' && /^[1-9][0-9]{0,18}$/.test(id) &&
      (id.length < 19 || id <= '9223372036854775807');
  }
  function valid(payload) {
    return payload && fields.every(key => typeof payload[key] === 'string') &&
      Array.isArray(payload.product_ids) && payload.product_ids.length > 0 &&
      payload.product_ids.every(validId);
  }
  function attemptStore(storage, userId) {
    const key = `lapakaian-checkout:${userId}`;
    return {
      load() {
        const text = storage.getItem(key);
        if (!text) return null;
        const value = JSON.parse(text);
        if (!valid(value)) throw new Error('Data percobaan checkout tidak valid. Periksa pesanan saya sebelum mencoba kembali.');
        return value;
      },
      save(value) {
        if (!valid(value)) throw new Error('Data checkout tidak lengkap.');
        storage.setItem(key, JSON.stringify(value));
      },
      clear() { storage.removeItem(key); },
    };
  }
  function runner(store, request) {
    let inFlight = null;
    return {
      send(payload) {
        if (inFlight) return inFlight;
        // Keep the original quote, address and idempotency key after an
        // uncertain response. Editing the form cannot alter the retry body.
        const saved = store.load() || payload;
        store.save(saved);
        inFlight = Promise.resolve().then(() => request(saved)).then(result => {
          store.clear();
          return result;
        }).catch(error => {
          // 401/403, network errors and 5xx leave the original payload intact.
          // These may require login/reload or may have committed already.
          if (error.status >= 400 && error.status < 500 && ![401, 403].includes(error.status)) store.clear();
          throw error;
        }).finally(() => { inFlight = null; });
        return inFlight;
      },
    };
  }
  return {attemptStore, runner, valid};
});
