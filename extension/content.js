// StoreStock Companion Content Script
// Communicates with StoreStock web app to signal active client-side scraping
try {
  document.documentElement.setAttribute('data-storestock-companion-active', 'true');
  window.STORESTOCK_COMPANION_ACTIVE = true;
  window.postMessage({ type: 'STORESTOCK_COMPANION_READY', version: '1.0.0' }, '*');
  console.log("%c[StoreStock Companion] Active & Ready (Direct Client Scraping Enabled)", "background: #059669; color: #fff; font-weight: bold; padding: 3px 6px; border-radius: 3px;");
} catch (e) {}
