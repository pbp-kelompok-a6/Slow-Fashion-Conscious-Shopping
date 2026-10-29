/* Local CDP harness, using Node's built-in WebSocket: no downloaded tooling. */
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const cfg = JSON.parse(process.argv[2]);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'lapakaian-edge-'));
const browser = spawn(cfg.edge, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--disable-background-networking', '--disable-extensions', '--window-size=1280,900', 'about:blank'], {windowsHide: true, stdio: 'ignore'});
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let ws;
let sequence = 0;
const pending = new Map();
const listeners = new Map();
const errors = [];
const badResponses = [];
const checkoutBodies = [];
function send(method, params = {}) {
  const id = ++sequence;
  return new Promise((resolve, reject) => { pending.set(id, {resolve, reject}); ws.send(JSON.stringify({id, method, params})); });
}
function on(method, handler) { listeners.set(method, handler); }
async function evaluate(expression) {
  const result = await send('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  return result.result.value;
}
async function wait(expression, label = expression) {
  const started = Date.now();
  while (Date.now() - started < 12000) {
    try { if (await evaluate(expression)) return; } catch {}
    await delay(60);
  }
  throw new Error('Timeout: ' + label + '\n' + await evaluate('document.body.innerText.slice(0,1400)'));
}
async function goto(url, allowLogin = false) {
  const target = new URL(url, cfg.base).href;
  await send('Page.navigate', {url: target});
  await wait(`(location.href === ${JSON.stringify(target)} || (${allowLogin} && location.pathname.includes('/login/'))) && document.readyState === 'complete' && document.documentElement.dataset.pesanan === 'true'`, 'navigate ' + url);
}
async function click(selector) {
  await evaluate(`(() => { const el=document.querySelector(${JSON.stringify(selector)}); if(!el) throw Error('Missing '+${JSON.stringify(selector)}); el.click(); })()`);
}
async function fill(selector, value) {
  await evaluate(`(() => {const el=document.querySelector(${JSON.stringify(selector)});el.value=${JSON.stringify(value)};el.dispatchEvent(new Event('input',{bubbles:true}));})()`);
}
async function login(username) {
  await wait("document.querySelector('.auth-box form')");
  await fill('[name=username]', username); await fill('[name=password]', 'Phase5-browser-password!');
  await click('.auth-box [type=submit]');
  await wait("!location.pathname.includes('/login/') && document.readyState === 'complete'");
}
async function logout() {
  await click('.nav-logout button');
  await wait("!document.querySelector('.nav-logout') && document.readyState === 'complete'");
}
async function screenshot(name) {
  const shot = await send('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
  fs.writeFileSync(path.join(cfg.artifacts, name + '.png'), Buffer.from(shot.data, 'base64'));
}

(async () => {
  const activePort = path.join(profile, 'DevToolsActivePort');
  for (let i=0; i<80 && !fs.existsSync(activePort); i++) await delay(100);
  if (!fs.existsSync(activePort)) throw new Error('Edge did not open a debugging port');
  const port = fs.readFileSync(activePort, 'utf8').split('\n')[0];
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve); ws.addEventListener('error', reject); });
  ws.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const item = pending.get(message.id); pending.delete(message.id);
      if (message.error) item.reject(new Error(message.error.message)); else item.resolve(message.result);
    } else listeners.get(message.method)?.(message.params);
  });
  on('Runtime.exceptionThrown', event => errors.push(event.exceptionDetails.exception?.description || event.exceptionDetails.text));
  on('Network.responseReceived', event => {
    if (event.response.url.startsWith(cfg.base) && event.response.status >= 400 && !event.response.url.endsWith('/favicon.ico')) badResponses.push([event.response.status, event.response.url]);
  });
  on('Network.requestWillBeSent', event => {
    if (event.request.url === cfg.base + '/pesanan/checkout/' && event.request.method === 'POST') checkoutBodies.push(JSON.parse(event.request.postData));
  });
  on('Page.javascriptDialogOpening', () => send('Page.handleJavaScriptDialog', {accept: true}).catch(() => {}));
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
  await send('Network.setBlockedURLs', {urls: ['*fonts.googleapis.com*', '*fonts.gstatic.com*']});
  await send('Emulation.setDeviceMetricsOverride', {width: 1280, height: 900, deviceScaleFactor: 1, mobile: false});

  await goto(`/listing/${cfg.product}/`);
  assert.match(await evaluate('document.body.innerText'), /Masuk untuk membeli/i);
  await click('[data-cart-slot] a');
  await login(cfg.buyer);
  await wait(`location.pathname === '/listing/${cfg.product}/' && document.querySelector('[data-cart-add]')`);
  await click('[data-cart-add] button');
  await wait("document.querySelector('[data-cart-count]').textContent === '1'");

  await goto('/wishlist/');
  await click('.pc-categories a[href="?category=atasan"]');
  await wait("location.search.includes('category=atasan') && !document.querySelector('.pc-page').hasAttribute('aria-busy')");
  await click(`[data-cart-slot][data-product-id="${cfg.product2}"] button`);
  await wait("document.querySelector('[data-cart-count]').textContent === '2'");
  await goto('/pesanan/keranjang/');
  assert.equal(await evaluate("document.querySelectorAll('[name=product_ids]:disabled').length"), 2);
  assert.equal(await evaluate("document.querySelectorAll('[name=product_ids]:checked').length"), 2);
  await screenshot('cart-desktop');
  await send('Emulation.setDeviceMetricsOverride', {width: 375, height: 812, deviceScaleFactor: 1, mobile: true});
  assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true, 'mobile cart should not overflow');
  await screenshot('cart-mobile');
  await click('[data-selection-submit]');
  await wait("location.pathname.includes('/checkout/konfirmasi/') && document.querySelector('[data-checkout-form]')");
  assert.match(await evaluate('document.body.innerText'), /Total 2 toko/);
  assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true, 'mobile checkout should not overflow');
  await screenshot('checkout-mobile');
  await fill('[name=recipient_name]', 'Buyer Browser'); await fill('[name=phone]', '081234567890'); await fill('[name=address]', 'Jalan browser nomor 12, Jakarta');

  // Fail the RESPONSE after the server has completed the transaction. The UI
  // must recover after a page reload and replay the exact same attempt.
  let interrupted = false;
  on('Fetch.requestPaused', event => {
    if (!interrupted) { interrupted = true; send('Fetch.failRequest', {requestId: event.requestId, errorReason: 'ConnectionClosed'}).then(() => send('Fetch.disable')).catch(error => errors.push(error.message)); }
    else send('Fetch.continueRequest', {requestId: event.requestId}).catch(() => {});
  });
  await send('Fetch.enable', {patterns: [{urlPattern: cfg.base + '/pesanan/checkout/', requestStage: 'Response'}]});
  await evaluate("document.querySelector('[data-checkout-form]').requestSubmit(); document.querySelector('[data-checkout-form]').requestSubmit()");
  await wait("!document.querySelector('[data-checkout-recovery]').hidden && !document.querySelector('[data-checkout-retry]').disabled", 'lost response recovery');
  assert.equal(checkoutBodies.length, 1, 'double submit must send one request');
  await goto(await evaluate('location.href'));
  await wait("!document.querySelector('[data-checkout-recovery]').hidden");
  await click('[data-checkout-retry]');
  await wait("location.pathname.includes('/checkout/berhasil/') && document.querySelectorAll('.ps-order-card').length === 2");
  assert.equal(checkoutBodies.length, 2);
  assert.deepEqual(checkoutBodies[0], checkoutBodies[1], 'retry must reuse the exact original body');
  const orderLinks = await evaluate("[...document.querySelectorAll('.ps-order-card h2 a')].map(a=>a.getAttribute('href'))");
  await goto(orderLinks[0]);
  assert.match(await evaluate('document.body.innerText'), /Belum dibayar/);
  await click('[data-order-action] button');
  await wait("document.querySelector('.ps-status-cancelled')");
  await goto('/katalog/');
  const publicCards = await evaluate("[...document.querySelectorAll('.pc-card')].map(c=>c.dataset.productId)");
  assert.equal(publicCards.includes(String(cfg.product)), true);
  assert.equal(publicCards.includes(String(cfg.product2)), false);
  await goto('/wishlist/');
  assert.match(await evaluate('document.querySelector("[data-cart-slot]").innerText'), /Terjual/);

  await logout(); await goto('/pesanan/penjualan/', true); await login(cfg.seller);
  await wait("document.querySelector('[data-order-filter]')");
  await fill('[name=status]', 'processing');
  await evaluate("document.querySelector('[name=status]').dispatchEvent(new Event('change',{bubbles:true}))");
  await wait("location.search.includes('processing') && !document.querySelector('[data-ps-page]').hasAttribute('aria-busy')");
  await goto(orderLinks[1]); await click('[data-order-action] button');
  await wait("document.querySelector('.ps-status-shipped')");
  await logout(); await goto('/pesanan/pembelian/', true); await login(cfg.buyer);
  await goto(orderLinks[1]); await click('[data-order-action] button');
  await wait("document.querySelector('.ps-status-completed')");
  assert.match(await evaluate('document.body.innerText'), /Dibayar \(simulasi\)/);
  await screenshot('order-mobile');
  assert.deepEqual(errors, [], 'unexpected JavaScript errors');
  assert.deepEqual(badResponses, [], 'unexpected local HTTP failures');
  console.log(JSON.stringify({passed: true, checkoutRequests: checkoutBodies.length, javascriptErrors: errors.length, localHttpFailures: badResponses.length, desktop: '1280x900', mobile: '375x812', flows: ['anonymous-login-next','wishlist-AJAX-add','unavailable-cart','two-store-checkout','double-submit','lost-response-reload-retry','buyer-cancel','seller-filter-ship','buyer-complete-COD']}));
})().catch(error => { console.error(error.stack); process.exitCode = 1; }).finally(async () => {
  try { if (ws?.readyState === WebSocket.OPEN) { await send('Browser.close'); ws.close(); } } catch {}
  browser.kill();
  // Remove only this freshly created, isolated temporary Edge profile.
  if (path.dirname(profile) === os.tmpdir() && path.basename(profile).startsWith('lapakaian-edge-')) {
    for (let i=0;i<20;i++) { try { fs.rmSync(profile, {recursive: true, force: true}); break; } catch { await delay(100); } }
  }
});
