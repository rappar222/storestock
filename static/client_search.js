/**
 * StoreStock 100% Client-Side Search & Distributed Cache Agent
 * Runs entirely on the user's client device/browser.
 * The TrueNAS server never makes outbound scraper calls to protect your server IP.
 */

window.StoreStockClientSearch = (function () {
  // Check if a URL has an open JSON API that supports direct browser fetch
  function isDirectCorsAllowed(targetUrl) {
    try {
      const parsed = new URL(targetUrl);
      // VTEX Auchan public search API allows open CORS directly from browser
      if (parsed.hostname.includes("auchan.ro") && parsed.pathname.includes("/api/catalog_system/")) {
        return true;
      }
    } catch (e) {}
    return false;
  }

  async function fetchWithFallback(targetUrl, timeoutMs = 4500) {
    // Strategy 1: Direct fetch for endpoints with open CORS headers
    if (isDirectCorsAllowed(targetUrl)) {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 3500);
        const res = await fetch(targetUrl, {
          signal: controller.signal,
          headers: { 'Accept': 'application/json' }
        });
        clearTimeout(timer);
        if (res.ok) {
          const text = await res.text();
          if (text && text.length > 50) return text;
        }
      } catch (e) {}
    }

    // Strategy 2: Fast Parallel Race of Top Working CORS Bridges
    // Races Cloudflare Worker proxy, AllOrigins raw proxy, and CORS.lol simultaneously!
    const encoded = encodeURIComponent(targetUrl);
    const bridges = [
      `https://cors.eu.org/${targetUrl}`,
      `https://api.allorigins.win/raw?url=${encoded}`,
      `https://api.cors.lol/?url=${encoded}`
    ];

    async function tryBridge(bUrl) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const res = await fetch(bUrl, { signal: controller.signal });
        clearTimeout(timer);
        if (res.ok) {
          const text = await res.text();
          if (text && text.length > 150) return text;
        }
      } catch (e) {
        clearTimeout(timer);
      }
      throw new Error("Bridge attempt failed");
    }

    try {
      // First active bridge that responds with valid content wins!
      return await Promise.any(bridges.map(b => tryBridge(b)));
    } catch (e) {
      // Strategy 3: JSON wrapper fallback
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 3500);
        const res = await fetch(`https://api.allorigins.win/get?url=${encoded}`, { signal: controller.signal });
        clearTimeout(timer);
        if (res.ok) {
          const data = await res.json();
          if (data && data.contents && data.contents.length > 150) {
            return data.contents;
          }
        }
      } catch (err) {}
    }

    return null;
  }

  // Scraper 1: eMAG Romania
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
        stock_badge_text: "In Stock",
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

  // Scraper 3: PC Garage Romania
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

  // Scraper 4: Auchan Romania (Groceries, Dairy, Market)
  async function searchAuchan(query) {
    const t0 = performance.now();
    const url = `https://www.auchan.ro/api/catalog_system/pub/products/search?ft=${encodeURIComponent(query)}`;
    const raw = await fetchWithFallback(url, 6000);
    const elapsed = Math.round(performance.now() - t0);
    if (!raw) return { store_name: "Auchan Hypermarket", elapsed_ms: elapsed, items: [] };

    const items = [];
    try {
      const data = JSON.parse(raw);
      if (Array.isArray(data)) {
        data.slice(0, 24).forEach((p, idx) => {
          const itemArr = p.items || [];
          const bestItem = itemArr[0] || {};
          const sellers = bestItem.sellers || [];
          const bestSeller = sellers[0] || {};
          const commOffer = bestSeller.commertialOffer || {};

          const price = parseFloat(commOffer.Price || commOffer.ListPrice || 0.0);
          const available = (commOffer.AvailableQuantity || 0) > 0;
          const pUrl = p.link || `https://www.auchan.ro/${p.linkText}/p`;
          const imgUrl = bestItem.images && bestItem.images[0] ? bestItem.images[0].imageUrl : null;

          items.push({
            id: `client_auchan_${p.productId || idx}`,
            store_name: "Auchan Hypermarket",
            store_icon: "shopping-cart",
            country_code: "RO",
            title: p.productName || p.productTitle || query,
            price: price,
            currency: "RON",
            in_stock: available,
            stock_level: available ? "IN_STOCK" : "OUT_OF_STOCK",
            stock_badge_text: available ? "In Stock (Shelf)" : "Out of Stock",
            product_url: pUrl,
            image_url: imgUrl,
            category: "groceries"
          });
        });
      }
    } catch (e) {}

    return { store_name: "Auchan Hypermarket", elapsed_ms: elapsed, items };
  }

  // Scraper 5: Flanco Romania
  async function searchFlanco(query) {
    const t0 = performance.now();
    const url = `https://www.flanco.ro/catalogsearch/result/?q=${encodeURIComponent(query)}`;
    const html = await fetchWithFallback(url, 8000);
    const elapsed = Math.round(performance.now() - t0);
    if (!html) return { store_name: "Flanco", elapsed_ms: elapsed, items: [] };

    const doc = new DOMParser().parseFromString(html, "text/html");
    const cards = doc.querySelectorAll(".product-item");
    const items = [];

    cards.forEach((card, idx) => {
      if (idx >= 20) return;
      const titleEl = card.querySelector(".product-item-link");
      if (!titleEl) return;
      const title = titleEl.textContent.trim();
      const pUrl = titleEl.getAttribute("href") || url;

      const priceEl = card.querySelector(".price");
      if (!priceEl) return;
      const rawPrice = priceEl.textContent.replace(/[^\d,\.]/g, "").replace(/\./g, "").replace(",", ".");
      const price = parseFloat(rawPrice) || 0.0;

      const imgEl = card.querySelector(".product-image-photo");
      const imgUrl = imgEl ? (imgEl.getAttribute("src") || imgEl.getAttribute("data-src")) : null;

      items.push({
        id: `client_flanco_${idx}_${Math.abs(hashString(pUrl)) % 100000}`,
        store_name: "Flanco",
        store_icon: "shopping-bag",
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

    return { store_name: "Flanco", elapsed_ms: elapsed, items };
  }

  // Scraper 6: evoMAG Romania
  async function searchEvoMag(query) {
    const t0 = performance.now();
    const url = `https://www.evomag.ro/cauta/${encodeURIComponent(query)}`;
    const html = await fetchWithFallback(url, 8000);
    const elapsed = Math.round(performance.now() - t0);
    if (!html) return { store_name: "evoMAG", elapsed_ms: elapsed, items: [] };

    const doc = new DOMParser().parseFromString(html, "text/html");
    const cards = doc.querySelectorAll(".sn-product, .product_box, .npi_content");
    const items = [];

    cards.forEach((card, idx) => {
      if (idx >= 20) return;
      const titleEl = card.querySelector(".npi_name, .product_name, a[title]");
      if (!titleEl) return;
      const title = titleEl.getAttribute("title") || titleEl.textContent.trim();
      let pUrl = titleEl.getAttribute("href") || url;
      if (pUrl && pUrl.startsWith("/")) pUrl = "https://www.evomag.ro" + pUrl;

      const priceEl = card.querySelector(".real_price, .money_val, .price");
      if (!priceEl) return;
      const rawPrice = priceEl.textContent.replace(/[^\d,\.]/g, "").replace(/\./g, "").replace(",", ".");
      const price = parseFloat(rawPrice) || 0.0;

      const imgEl = card.querySelector("img");
      const imgUrl = imgEl ? (imgEl.getAttribute("src") || imgEl.getAttribute("data-src")) : null;

      items.push({
        id: `client_evomag_${idx}_${Math.abs(hashString(pUrl)) % 100000}`,
        store_name: "evoMAG",
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

    return { store_name: "evoMAG", elapsed_ms: elapsed, items };
  }

  // Scraper 7: Amazon Global
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

  // Background Sync: Persists discovered products to TrueNAS SQLite DB with user branch coords
  function syncItemsToServer(query, country, items, userCoords = null) {
    if (!items || items.length === 0) return;
    try {
      const payload = {
        query,
        country,
        items,
        lat: userCoords ? userCoords.lat : null,
        lon: userCoords ? userCoords.lon : null
      };

      fetch("/api/cache/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(r => r.json()).then(res => {
        if (res && res.saved) {
          console.log(`[ClientSearch] Synced ${res.saved} items to TrueNAS database.`);
        }
      }).catch(() => {});
    } catch (e) {}
  }

  // Master Client Search Method
  async function searchAllClientSide(query, country, onStoreResult, userCoords = null) {
    const qLower = query.toLowerCase();
    const isGrocery = ["lapte", "milk", "unt", "paine", "bread", "cafea", "coffee", "zahar", "faina", "oua", "cascaval"].some(k => qLower.includes(k));

    let scrapers = [];
    if (country === "RO") {
      if (isGrocery) {
        scrapers = [searchAuchan(query), searchEmag(query), searchAmazon(query, "RO")];
      } else {
        scrapers = [
          searchEmag(query),
          searchAltex(query),
          searchPCGarage(query),
          searchFlanco(query),
          searchEvoMag(query),
          searchAuchan(query),
          searchAmazon(query, "RO")
        ];
      }
    } else {
      scrapers = [searchAmazon(query, country), searchAltex(query)];
    }

    // Stream each store as it finishes in real-time
    const promises = scrapers.map(p =>
      p.then(res => {
        if (res && res.items) {
          onStoreResult(res);
          syncItemsToServer(query, country, res.items, userCoords);
        }
      }).catch(err => {
        console.warn("[ClientSearch] Scraper error:", err);
      })
    );

    await Promise.allSettled(promises);
  }

  return {
    searchAll: searchAllClientSide
  };
})();
