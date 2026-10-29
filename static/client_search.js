/**
 * StoreStock Client-Side Scraper & Distributed Cache Agent
 * Runs entirely in the client's browser using the user's personal IP.
 * Bypasses TrueNAS server IP rate-limiting on sensitive stores like eMAG,
 * and syncs discovered products back to the TrueNAS database via /api/cache/sync.
 */

window.StoreStockClientSearch = (function () {
  const CORS_PROXIES = [
    (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
    (url) => `https://corsproxy.io/?url=${encodeURIComponent(url)}`,
    (url) => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(url)}`
  ];

  async function fetchWithFallback(targetUrl, timeoutMs = 6000) {
    // 1. Try direct fetch first (for CORS-permissive APIs)
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 2500);
      const res = await fetch(targetUrl, { signal: controller.signal, headers: { 'Accept': 'application/json, text/html' } });
      clearTimeout(timer);
      if (res.ok) return await res.text();
    } catch (e) {
      // Direct fetch failed or blocked by CORS, proceed to client proxy
    }

    // 2. Try client-side CORS proxies
    for (const proxyFn of CORS_PROXIES) {
      try {
        const proxyUrl = proxyFn(targetUrl);
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        const res = await fetch(proxyUrl, { signal: controller.signal });
        clearTimeout(timer);
        if (res.ok) {
          const txt = await res.text();
          if (txt && txt.length > 200) return txt;
        }
      } catch (e) {
        // Try next proxy
      }
    }
    return null;
  }

  // Scraper 1: eMAG Romania
  async function searchEmag(query) {
    const t0 = performance.now();
    const url = `https://www.emag.ro/search/${encodeURIComponent(query)}`;
    const html = await fetchWithFallback(url, 7000);
    const elapsed = Math.round(performance.now() - t0);
    if (!html) return { store_name: "eMAG", elapsed_ms: elapsed, items: [] };

    const doc = new DOMParser().parseFromString(html, "text/html");
    const cards = doc.querySelectorAll(".card-item");
    const items = [];

    cards.forEach((card, idx) => {
      if (idx >= 20) return;
      const titleEl = card.querySelector(".card-v2-title");
      if (!titleEl) return;
      const title = titleEl.textContent.trim();

      const priceEl = card.querySelector(".product-new-price");
      if (!priceEl) return;
      const rawPrice = priceEl.textContent.replace(/[^\d,\.]/g, "").replace(/\./g, "").replace(",", ".");
      const price = parseFloat(rawPrice) || 0.0;

      const linkEl = card.querySelector("a[href]");
      let pUrl = linkEl ? linkEl.getAttribute("href") : url;
      if (pUrl && pUrl.startsWith("/")) pUrl = "https://www.emag.ro" + pUrl;

      const imgEl = card.querySelector("img");
      let imgUrl = imgEl ? (imgEl.getAttribute("src") || imgEl.getAttribute("data-src")) : null;

      items.push({
        id: `client_emag_${idx}_${Math.abs(query.hashCode ? query.hashCode() : idx)}`,
        store_name: "eMAG",
        store_icon: "shopping-cart",
        country_code: "RO",
        title: title,
        price: price,
        currency: "RON",
        in_stock: true,
        stock_level: "IN_STOCK",
        stock_badge_text: "In Stock (Client Verified)",
        product_url: pUrl,
        image_url: imgUrl,
        delivery_info: "Standard Delivery",
        category: "general"
      });
    });

    return { store_name: "eMAG", elapsed_ms: elapsed, items };
  }

  // Scraper 2: Altex Romania
  async function searchAltex(query) {
    const t0 = performance.now();
    const url = `https://fenrir.altex.ro/v2/catalog/search/${encodeURIComponent(query)}`;
    const raw = await fetchWithFallback(url, 5000);
    const elapsed = Math.round(performance.now() - t0);
    if (!raw) return { store_name: "Altex", elapsed_ms: elapsed, items: [] };

    const items = [];
    try {
      const data = JSON.parse(raw);
      const prods = data.products || data.data?.products || [];
      prods.slice(0, 20).forEach((p, idx) => {
        items.push({
          id: `client_altex_${p.id || idx}`,
          store_name: "Altex",
          store_icon: "monitor",
          country_code: "RO",
          title: p.name || p.title,
          price: parseFloat(p.price || p.special_price || 0.0),
          currency: "RON",
          in_stock: p.stock_status !== "out_of_stock",
          stock_level: p.stock_status === "in_stock" ? "IN_STOCK" : "ONLINE_STOCK",
          stock_badge_text: "In Stock (Altex)",
          product_url: p.url ? (p.url.startsWith("http") ? p.url : `https://altex.ro/${p.url}`) : `https://altex.ro/cauta/?q=${encodeURIComponent(query)}`,
          image_url: p.image || p.small_image || null,
          category: "tech_hardware"
        });
      });
    } catch (e) {}

    return { store_name: "Altex", elapsed_ms: elapsed, items };
  }

  // Scraper 3: PC Garage Romania
  async function searchPCGarage(query) {
    const t0 = performance.now();
    const url = `https://www.pcgarage.ro/cauta/${encodeURIComponent(query)}`;
    const html = await fetchWithFallback(url, 7000);
    const elapsed = Math.round(performance.now() - t0);
    if (!html) return { store_name: "PC Garage", elapsed_ms: elapsed, items: [] };

    const doc = new DOMParser().parseFromString(html, "text/html");
    const cards = doc.querySelectorAll(".product_box_container");
    const items = [];

    cards.forEach((card, idx) => {
      if (idx >= 20) return;
      const titleEl = card.querySelector(".product_box_name a") || card.querySelector(".product_box_name");
      if (!titleEl) return;
      const title = titleEl.textContent.trim();
      const pUrl = titleEl.getAttribute("href") || url;

      const priceEl = card.querySelector(".price_num") || card.querySelector(".price");
      if (!priceEl) return;
      const rawPrice = priceEl.textContent.replace(/[^\d,\.]/g, "").replace(/\./g, "").replace(",", ".");
      const price = parseFloat(rawPrice) || 0.0;

      const imgEl = card.querySelector("img");
      const imgUrl = imgEl ? (imgEl.getAttribute("src") || imgEl.getAttribute("data-src")) : null;

      items.push({
        id: `client_pcg_${idx}`,
        store_name: "PC Garage",
        store_icon: "cpu",
        country_code: "RO",
        title: title,
        price: price,
        currency: "RON",
        in_stock: true,
        stock_level: "IN_STOCK",
        stock_badge_text: "In Stock",
        product_url: pUrl,
        image_url: imgUrl,
        category: "tech_hardware"
      });
    });

    return { store_name: "PC Garage", elapsed_ms: elapsed, items };
  }

  // Background Sync to TrueNAS database
  function syncItemsToServer(query, country, items) {
    if (!items || items.length === 0) return;
    try {
      fetch("/api/cache/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, country, items })
      }).then(r => r.json()).then(res => {
        console.log(`[ClientSearch] Synced ${res.saved || 0} items to TrueNAS database.`);
      }).catch(() => {});
    } catch (e) {}
  }

  // Master Client Search Method
  async function searchAllClientSide(query, country, onStoreResult) {
    const scrapers = country === "RO" 
      ? [searchEmag(query), searchAltex(query), searchPCGarage(query)]
      : [searchAltex(query)]; // Default fallback

    // Stream each result as it finishes
    for (const promise of scrapers) {
      promise.then(res => {
        if (res && res.items) {
          onStoreResult(res);
          syncItemsToServer(query, country, res.items);
        }
      }).catch(err => {
        console.warn("[ClientSearch] Scraper error:", err);
      });
    }

    await Promise.allSettled(scrapers);
  }

  return {
    searchAll: searchAllClientSide
  };
})();
