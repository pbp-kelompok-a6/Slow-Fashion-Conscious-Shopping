const test = require('node:test');
const assert = require('node:assert/strict');
const {attemptStore, runner, valid} = require('../static/pesanan/checkout_state.js');
function storage() {
  const data = new Map();
  return {getItem: key => data.get(key) || null, setItem: (key, value) => data.set(key, value), removeItem: key => data.delete(key)};
}
const payload = {product_ids: [1, 2], recipient_name: 'Buyer', phone: '081234567890', address: 'Jalan panjang 12', payment_method: 'cod', idempotency_key: 'attempt-1234', quote_token: 'signed-quote'};

test('double submit sends exactly one request and returns the same result', async () => {
  const store = attemptStore(storage(), 1);
  let calls = 0;
  let finish;
  const checkout = runner(store, () => { calls++; return new Promise(resolve => { finish = resolve; }); });
  const first = checkout.send(payload);
  const second = checkout.send({...payload, address: 'Changed during loading'});
  await Promise.resolve();
  assert.equal(calls, 1); assert.equal(first, second);
  finish({orders: [{id: 7}]});
  assert.deepEqual(await first, {orders: [{id: 7}]}); assert.equal(store.load(), null);
});

test('lost response survives reload and retries exact original quote and key', async () => {
  const memory = storage();
  const firstStore = attemptStore(memory, 1);
  await assert.rejects(runner(firstStore, async () => { throw new Error('lost response'); }).send(payload));
  const afterReload = attemptStore(memory, 1);
  let received;
  const retry = runner(afterReload, async body => { received = body; return {orders: [{id: 7}], replayed: true}; });
  await retry.send({...payload, quote_token: 'fresh-token-would-conflict', idempotency_key: 'new-key'});
  assert.deepEqual(received, payload); assert.equal(afterReload.load(), null);
});

test('uncertain 5xx, login and CSRF preserve payload for safe retry', async () => {
  for (const status of [0, 401, 403, 502, 503]) {
    const store = attemptStore(storage(), 1);
    await assert.rejects(runner(store, async () => { throw Object.assign(new Error('failed'), {status}); }).send(payload));
    assert.deepEqual(store.load(), payload);
  }
});

test('definitive validation and quote conflicts permit a new confirmation', async () => {
  for (const status of [400, 404, 409]) {
    const store = attemptStore(storage(), 1);
    await assert.rejects(runner(store, async () => { throw Object.assign(new Error('quote changed'), {status}); }).send(payload));
    assert.equal(store.load(), null);
  }
});

test('saved checkout is scoped to account and malformed storage is not submitted', () => {
  const memory = storage();
  attemptStore(memory, 1).save(payload);
  assert.equal(attemptStore(memory, 2).load(), null);
  memory.setItem('lapakaian-checkout:2', '{bad');
  assert.throws(() => attemptStore(memory, 2).load());
});

test('storage failure happens before any network request', () => {
  const broken = {getItem: () => null, setItem: () => { throw new Error('storage denied'); }};
  let calls = 0;
  assert.throws(() => runner(attemptStore(broken, 1), () => { calls++; }).send(payload));
  assert.equal(calls, 0);
});

test('large IDs stay decimal strings rather than rounded JavaScript numbers', () => {
  assert.equal(valid({...payload, product_ids: ['9223372036854775807']}), true);
  assert.equal(valid({...payload, product_ids: ['9223372036854775808']}), false);
  assert.equal(valid({...payload, product_ids: [9223372036854775807]}), false);
});
