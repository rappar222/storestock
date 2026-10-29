/**
 * StoreStock Client-Side Scraper & Distributed Cache Agent
 * Runs 100% on the user's client device/browser.
 * The TrueNAS server never makes outbound scraper calls.
 */

window.StoreStockClientSearch = (function () {
  // Reliable public CORS bridges (excluding corsproxy.io which returns 401)
  async function fetchWithFallback(targetUrl, timeoutMs = 8000) {
    // Strategy 1: Direct fetch (works if remote endpoint allows CORS)
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(targetUrl, {
        signal: controller.signal,
        headers: { 'Accept': 'application/json, text/html' }
      });
      clearTimeout(timer);
      if (res.ok) {
        const text = await res.text();
        if (text && text.length > 200) return text;
      }
    } catch (e) {
      // Direct CORS blocked, proceed to CORS bridges
    }

    // Strategy 2: AllOrigins JSON API (avoids raw aborts by returning JSON wrapper)
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      const allOriginsUrl = `https://api.allorigins.win/get?url=${encodeURIComponent(targetUrl)}`;
      const res = await fetch(allOriginsUrl, { signal: controller.signal });
      clearTimeout(timer);
      if (res.ok) {
        const json = await res.json();
        if (json && json.contents && json.contents.length > 200) {
          return json.contents;
        }
      }
    } catch (e) {
      // Continue to next bridge
    }

    // Strategy 3: CodeTabs CORS Bridge
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      const codeTabsUrl = `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(targetUrl)}`;
      const res = await fetch(codeTabsUrl, { signal: controller.signal });
      clearTimeout(timer);
      if (res.ok) {
        const text = await res.text();
        if (text && text.length > 200) return text;
      }
    } catch (e) {
      // Fallback exhausted
    }

    return null;
  }

  // Scraper 1: eMAG Romania (Client-Side)
  async function searchEmag(query) {
    const t0 = performance.now();
    const url = `https://www.emag.ro/search/${encodeURIComponent(query)}`;
    const html = await fetchWithFallback(url, 8000);
    const elapsed = Math.round(performance.now() - t0);
    if (!html) return { store_name: "eMAG", elapsed_ms: elapsed, items: [] };

    const doc = new DOMParser().parseFromString(html, "text/html");
    const cards = doc.querySelectorAll(".card-item, .card-v2");
    const items = [];

    cards.forEach((card, idx) => {
      if (idx >= 24) return;
      const titleEl = card.querySelector(".card-v2-title, h2 a, a.card-v2-title");
      if (!titleEl) return;
      const title = titleEl.textContent.trim();

      const priceEl = card.querySelector(".product-new-price, .pricing-box .product-new-price");
      if (!priceEl) return;
      const rawPrice = priceEl.textContent.replace(/[^\d,\.]/g, "").replace(/\./g, "").replace(",", ".");
      const price = parseFloat(rawPrice) || 0.0;

      const linkEl = card.querySelector("a[href]");
      let pUrl = linkEl ? linkEl.getAttribute("href") : url;
      if (pUrl && pUrl.startsWith("/")) pUrl = "https://www.emag.ro" + pUrl;

      const imgEl = card.querySelector("img");
      let imgUrl = imgEl ? (imgEl.getAttribute("src") || imgEl.getAttribute("data-src")) : null;

      items.push({
        id: `client_emag_${idx}_${Math.abs(hashString(pUrl)) % 100000}`,
        store_name: "eMAG",
        store_icon: "shopping-cart",
        country_code: "RO",
        title: title,
        price: price,
        currency: "RON",
        in_stock: true,
        stock_level: "IN_STOCK",
        stock_badge_text: "In Stock (Client Scraped)",
        product_url: pUrl,
        image_url: imgUrl,
        delivery_info: "Standard Delivery",
        category: "general"
      });
    });

    return { store_name: "eMAG", elapsed_ms: elapsed, items };
  }

  // Scraper 2: Altex Romania (Client-Side)
  async function searchAltex(query) {
    const t0 = performance.now();
    const url = `https://fenrir.altex.ro/v2/catalog/search/${encodeURIComponent(query)}`;
    const raw = await fetchWithFallback(url, 6000);
    const elapsed = Math.round(performance.now() - t0);
    if (!raw) return { store_name: "Altex", elapsed_ms: elapsed, items: [] };

    const items = [];
    try {
      const data = JSON.parse(raw);
      const prods = data.products || data.data?.products || [];
      prods.slice(0, 24).forEach((p, idx) => {
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

  // Scraper 3: PC Garage Romania (Client-Side)
  async function searchPCGarage(query) {
    const t0 = performance.now();
    const url = `https://www.pcgarage.ro/cauta/${encodeURIComponent(query)}`;
    const html = await fetchWithFallback(url, 8000);
    const elapsed = Math.round(performance.now() - t0);
    if (!html) return { store_name: "PC Garage", elapsed_ms: elapsed, items: [] };

    const doc = new DOMParser().parseFromString(html, "text/html");
    const cards = doc.querySelectorAll(".product_box_container");
    const items = [];

    cards.forEach((card, idx) => {
      if (idx >= 24) return;
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
        id: `client_pcg_${idx}_${Math.abs(hashString(pUrl)) % 100000}`,
        store_name: "PC Garage",
        store_icon: "cpu",
        country_code: "RO",
        title: title,
        price: price,
        currency: "RON",
        in_stock: true,
        stock_level: "IN_STOCK",
        stock_badge_text: "In Stock (PC Garage)",
        product_url: pUrl,
        image_url: imgUrl,
        category: "tech_hardware"
      });
    });

    return { store_name: "PC Garage", elapsed_ms: elapsed, items };
  }

  // Scraper 4: Amazon (Client-Side)
  async function searchAmazon(query, country = "US") {
    const t0 = performance.now();
    const domain = country === "RO" || country === "DE" ? "amazon.de" : "amazon.com";
    const currency = country === "RO" || country === "DE" ? "EUR" : "USD";
    const url = `https://www.${domain}/s?k=${encodeURIComponent(query)}`;
    const html = await fetchWithFallback(url, 8000);
    const elapsed = Math.round(performance.now() - t0);
    if (!html) return { store_name: "Amazon", elapsed_ms: elapsed, items: [] };

    const doc = new DOMParser().parseFromString(html, "text/html");
    const cards = doc.querySelectorAll("div[data-component-type=s-search-result]");
    const items = [];

    cards.forEach((card, idx) => {
      if (idx >= 15) return;
      const titleEl = card.querySelector("h2 span, h2 a");
      if (!titleEl) return;
      const title = titleEl.textContent.trim();

      const priceEl = card.querySelector(".a-price .a-offscreen, .a-price");
      let price = 0.0;
      if (priceEl) {
        const raw = priceEl.textContent.replace(/[^\d,\.]/g, "").replace(/,/g, ".");
        price = parseFloat(raw) || 0.0;
      }

      const linkEl = card.querySelector("h2 a[href]");
      let pUrl = linkEl ? `https://www.${domain}${linkEl.getAttribute("href")}` : url;
      const imgEl = card.querySelector("img.s-image, img");
      const imgUrl = imgEl ? imgEl.getAttribute("src") : null;

      items.push({
        id: `client_amz_${idx}_${Math.abs(hashString(pUrl)) % 100000}`,
        store_name: "Amazon",
        store_icon: "package",
        country_code: country,
        title: title,
        price: price,
        currency: currency,
        in_stock: true,
        stock_level: "IN_STOCK",
        stock_badge_text: "In Stock (Amazon)",
        product_url: pUrl,
        image_url: imgUrl,
        category: "general"
      });
    });

    return { store_name: "Amazon", elapsed_ms: elapsed, items };
  }

  function hashString(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash |= 0;
    }
    return hash;
  }

  // Background Sync: Persists discovered products to TrueNAS SQLite DB
  function syncItemsToServer(query, country, items) {
    if (!items || items.length === 0) return;
    try {
      fetch("/api/cache/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, country, items })
      }).then(r => r.json()).then(res => {
        if (res && res.saved) {
          console.log(`[ClientSearch] Synced ${res.saved} items to TrueNAS database.`);
        }
      }).catch(() => {});
    } catch (e) {}
  }

  // Master Client Search Method
  async function searchAllClientSide(query, country, onStoreResult) {
    const scrapers = country === "RO"
      ? [searchEmag(query), searchAltex(query), searchPCGarage(query), searchAmazon(query, "RO")]
      : [searchAmazon(query, country), searchAltex(query)];

    // Stream each store as it finishes in real-time
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
