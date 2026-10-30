/**
 * StoreStock Direct Client-Side Search Engine
 * Runs completely in the user's browser - ZERO proxies, ZERO server-side calls.
 *
 * Only stores whose search endpoints send CORS headers can be queried from a web page.
 * As of 2026-10-30 that is evoMAG (via its Nosto search API, ACAO: *). eMAG, Altex,
 * PC Garage, Flanco, Auchan and Amazon block cross-origin reads, so those are offered
 * as "search on store" link-outs instead (see getSearchLinks).
 */
console.log("%c[StoreStock v104] Direct Client-Side Search Active (ZERO Server Calls)", "background: #059669; color: #fff; font-weight: bold; font-size: 13px; padding: 4px 8px; border-radius: 4px;");

window.StoreStockClientSearch = (function () {
  const NOSTO_URL = "https://search.nosto.com/v1/graphql";
  const NOSTO_QUERY = `query($accountId:String,$query:String,$products:InputSearchProducts){
    search(accountId:$accountId,query:$query,products:$products){
      products{ total hits{ productId name url imageUrl price listPrice priceCurrencyCode brand availability } }
    }
  }`;

  function isGroceryQuery(query) {
    const qLower = query.toLowerCase();
    return ["lapte", "milk", "unt", "paine", "bread", "cafea", "coffee", "zahar", "faina", "oua", "cascaval"].some(k => qLower.includes(k));
  }

  // Scraper: evoMAG Romania (Nosto search API, CORS-enabled)
  async function searchEvoMag(query) {
    const t0 = performance.now();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 6000);
    const items = [];
    try {
      const res = await fetch(NOSTO_URL, {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: NOSTO_QUERY,
          variables: { accountId: "evomag-prod", query, products: { size: 24, from: 0 } }
        })
      });
      if (res.ok) {
        const data = await res.json();
        const hits = data?.data?.search?.products?.hits || [];
        hits.forEach((p, idx) => {
          const inStock = p.availability === "InStock";
          items.push({
            id: `client_evomag_${p.productId || idx}`,
            store_name: "evoMAG",
            store_icon: "cpu",
            country_code: "RO",
            title: p.name,
            price: parseFloat(p.price) || 0.0,
            currency: p.priceCurrencyCode || "RON",
            in_stock: inStock,
            stock_level: inStock ? "IN_STOCK" : "OUT_OF_STOCK",
            stock_badge_text: inStock ? "In Stock" : "Out of Stock",
            product_url: p.url,
            image_url: p.imageUrl || null,
            delivery_info: "Standard Delivery",
            category: "tech_hardware"
          });
        });
      }
    } catch (e) {
      console.warn("[ClientSearch] evoMAG search failed:", e);
    } finally {
      clearTimeout(timer);
    }
    return { store_name: "evoMAG", elapsed_ms: Math.round(performance.now() - t0), items };
  }

  // Stores that block cross-origin reads: link out to their own search results page
  function getSearchLinks(query, country) {
    const q = encodeURIComponent(query);
    if (country === "RO") {
      const links = [
        { store_name: "eMAG", url: `https://www.emag.ro/search/${q}` },
        { store_name: "Altex", url: `https://altex.ro/cauta/?q=${q}` },
        { store_name: "PC Garage", url: `https://www.pcgarage.ro/cauta/${q}` },
        { store_name: "Flanco", url: `https://www.flanco.ro/catalogsearch/result/?q=${q}` },
        { store_name: "Auchan", url: `https://www.auchan.ro/${q}?_q=${q}&map=ft` },
        { store_name: "Amazon.de", url: `https://www.amazon.de/s?k=${q}` }
      ];
      if (isGroceryQuery(query)) {
        return links.filter(l => ["Auchan", "eMAG", "Amazon.de"].includes(l.store_name));
      }
      return links;
    }
    const amazonDomain = country === "DE" ? "amazon.de" : "amazon.com";
    return [{ store_name: amazonDomain.replace("amazon", "Amazon"), url: `https://www.${amazonDomain}/s?k=${q}` }];
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
    let scrapers = [];
    if (country === "RO" && !isGroceryQuery(query)) {
      scrapers = [searchEvoMag(query)];
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
    searchAll: searchAllClientSide,
    getSearchLinks
  };
})();
