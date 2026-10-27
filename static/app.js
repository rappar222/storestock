// StoreStock Client Application

let currentResults = [];
let activeFilter = 'all'; // 'all' or 'in_stock'
let activeSort = 'relevance';

const searchForm = document.getElementById('searchForm');
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const countrySelect = document.getElementById('countrySelect');
const resultsGrid = document.getElementById('resultsGrid');
const loadingIndicator = document.getElementById('loadingIndicator');
const statsBar = document.getElementById('statsBar');
const inStockStat = document.getElementById('inStockStat');
const totalFoundStat = document.getElementById('totalFoundStat');
const latencyStat = document.getElementById('latencyStat');
const storesProgress = document.getElementById('storesProgress');
const emptyState = document.getElementById('emptyState');
const filterAllBtn = document.getElementById('filterAll');
const filterInStockBtn = document.getElementById('filterInStock');
const sortSelect = document.getElementById('sortSelect');

// Populate Country Selector
async function loadCountries() {
  try {
    const res = await fetch('/api/countries');
    const data = await res.json();
    countrySelect.innerHTML = '';
    
    // Sort so RO is first, then alphabetical
    const sorted = Object.entries(data).sort((a, b) => {
      if (a[0] === 'RO') return -1;
      if (b[0] === 'RO') return 1;
      return a[1].name.localeCompare(b[1].name);
    });

    for (const [code, info] of sorted) {
      const opt = document.createElement('option');
      opt.value = code;
      opt.textContent = `${info.flag} ${info.name} (${info.currency})`;
      if (code === 'RO') opt.selected = true;
      countrySelect.appendChild(opt);
    }
  } catch (err) {
    console.error("Failed to load countries:", err);
  }
}

// Perform Live Streaming Search using Server-Sent Events (SSE)
function executeSearch(query) {
  if (!query || !query.trim()) return;

  const country = countrySelect.value || 'RO';
  currentResults = [];
  resultsGrid.innerHTML = '';
  storesProgress.innerHTML = '';
  emptyState.classList.add('hidden');
  statsBar.classList.remove('hidden');
  loadingIndicator.classList.remove('hidden');

  inStockStat.textContent = 'Checking stock...';
  totalFoundStat.textContent = 'Searching stores...';
  latencyStat.textContent = '...';

  const startTime = performance.now();
  const encodedQuery = encodeURIComponent(query.trim());
  const eventSource = new EventSource(`/api/stream?q=${encodedQuery}&country=${country}`);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'provider_result') {
        const p = data.payload;
        // Add store progress pill
        renderStorePill(p.store_name, p.items.length, p.elapsed_ms);

        if (p.items && p.items.length > 0) {
          currentResults.push(...p.items);
          renderResults();
        }
      } else if (data.type === 'done') {
        eventSource.close();
        loadingIndicator.classList.add('hidden');
        const elapsed = Math.round(performance.now() - startTime);
        latencyStat.textContent = `${elapsed}ms total`;
        updateStats();

        if (currentResults.length === 0) {
          emptyState.classList.remove('hidden');
        }
      }
    } catch (e) {
      console.error("Error parsing SSE event:", e);
    }
  };

  eventSource.onerror = (err) => {
    console.warn("EventSource stream ended or closed:", err);
    eventSource.close();
    loadingIndicator.classList.add('hidden');
    updateStats();
    if (currentResults.length === 0) {
      emptyState.classList.remove('hidden');
    }
  };
}

function renderStorePill(storeName, count, elapsedMs) {
  const pill = document.createElement('div');
  pill.className = "flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800/90 border border-slate-700 text-slate-300 shadow-sm animate-fade-in";
  pill.innerHTML = `
    <span class="w-2 h-2 rounded-full ${count > 0 ? 'bg-emerald-400' : 'bg-amber-400'}"></span>
    <span>${storeName}:</span>
    <span class="text-white font-bold">${count} found</span>
    <span class="text-slate-500 text-[10px]">(${elapsedMs}ms)</span>
  `;
  storesProgress.appendChild(pill);
}

const ACCESSORY_WORDS = [
  "stand", "suport", "holder", "bracket", "riser", "cablu", "cable",
  "husa", "case", "adaptor", "adapter", "pasta", "paste", "thermal",
  "pad", "ventilator", "fan", "cooler", "montare", "mount", "surub", "suruburi",
  "screws", "splitter", "extensie", "extension", "stickere", "sticker",
  "power supply", "incarcator", "alimentator", "charger", "mouse pad"
];

const HARDWARE_WORDS = [
  "placa video", "placi video", "graphics card", "gpu", "laptop", "procesor", "workstation"
];

function scoreRelevance(query, title, price, inStock) {
  const qClean = (query || "").toLowerCase().trim();
  const tClean = (title || "").toLowerCase().trim();
  const qTokens = qClean.split(/\s+/).filter(w => w.length > 1);

  if (qTokens.length === 0) return 0;

  let score = 0;

  // Exact phrase match
  if (tClean.includes(qClean)) {
    score += 100;
  }

  // Token coverage
  const matched = qTokens.filter(t => tClean.includes(t));
  const coverage = matched.length / qTokens.length;
  score += coverage * 120;

  if (coverage < 1.0) {
    score -= 60 * (1.0 - coverage);
  }

  // Accessory penalty if user didn't ask for one
  const userAskedAccessory = ACCESSORY_WORDS.some(acc => qClean.includes(acc));
  const titleHasAccessory = ACCESSORY_WORDS.some(acc => tClean.includes(acc));
  if (titleHasAccessory && !userAskedAccessory) {
    score -= 250;
  }

  // GPU intent detection
  const isGpu = ["rtx", "gtx", "radeon", "a6000", "blackwell", "geforce", "gpu"].some(k => qClean.includes(k));
  if (isGpu) {
    if (HARDWARE_WORDS.some(h => tClean.includes(h))) {
      score += 50;
    }
    // Cheap accessories claiming to be GPUs
    if (price > 0 && price < 250 && !userAskedAccessory) {
      score -= 150;
    }
  }

  // In stock priority bonus
  if (inStock) {
    score += 150;
  }

  return score;
}

function updateStats() {
  const inStockCount = currentResults.filter(r => r.in_stock).length;
  inStockStat.textContent = `${inStockCount} In Stock`;
  totalFoundStat.textContent = `${currentResults.length} Total Found`;
}

function renderResults() {
  updateStats();

  let filtered = [...currentResults];
  if (activeFilter === 'in_stock') {
    filtered = filtered.filter(r => r.in_stock);
  }

  // Sort
  if (activeSort === 'price_asc') {
    filtered.sort((a, b) => {
      const pa = a.price > 0 ? a.price : 9999999;
      const pb = b.price > 0 ? b.price : 9999999;
      return pa - pb;
    });
  } else if (activeSort === 'price_desc') {
    filtered.sort((a, b) => b.price - a.price);
  } else {
    // Recommended / Smart Relevance Sort
    const query = searchInput.value || "";
    filtered.sort((a, b) => {
      const scoreA = scoreRelevance(query, a.title, a.price, a.in_stock);
      const scoreB = scoreRelevance(query, b.title, b.price, b.in_stock);
      return scoreB - scoreA;
    });
  }

  resultsGrid.innerHTML = '';

  if (filtered.length === 0) {
    emptyState.classList.remove('hidden');
    return;
  } else {
    emptyState.classList.add('hidden');
  }

  filtered.forEach(item => {
    const card = document.createElement('div');
    card.className = "glass-card rounded-2xl p-4 flex flex-col justify-between hover:border-slate-600 transition duration-200 group";

    // Stock Badge Styles
    let badgeClass = "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    let statusIcon = "check-circle";
    if (!item.in_stock) {
      badgeClass = "bg-rose-500/10 text-rose-400 border border-rose-500/20";
      statusIcon = "x-circle";
    } else if (item.stock_level === "LOW_STOCK") {
      badgeClass = "bg-amber-500/10 text-amber-400 border border-amber-500/20";
      statusIcon = "alert-triangle";
    }

    // Format price
    let formattedPrice = `${item.price.toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${item.currency}`;
    if (item.price === 0) {
      formattedPrice = "Check Store";
    }

    // Placeholder image if missing
    const imgUrl = item.image_url || 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=300&auto=format&fit=crop&q=60';

    card.innerHTML = `
      <div class="space-y-3">
        <!-- Store Name Header & Stock Status -->
        <div class="flex items-center justify-between gap-2">
          <span class="px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-800 text-slate-200 border border-slate-700/80">
            ${item.store_name}
          </span>
          <span class="store-badge ${badgeClass}">
            <i data-lucide="${statusIcon}" class="w-3.5 h-3.5"></i>
            <span>${item.stock_badge_text}</span>
          </span>
        </div>

        <!-- Product Image -->
        <div class="relative w-full h-44 rounded-xl bg-slate-900/80 overflow-hidden flex items-center justify-center p-2 group-hover:scale-[1.02] transition">
          <img src="${imgUrl}" alt="${item.title}" class="max-h-full max-w-full object-contain" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=300&auto=format&fit=crop&q=60'"/>
        </div>

        <!-- Product Title -->
        <h3 class="text-sm font-semibold text-slate-100 line-clamp-2 title-tooltip" title="${item.title}">
          ${item.title}
        </h3>
      </div>

      <!-- Price & Order CTA -->
      <div class="pt-4 mt-2 border-t border-slate-800/80 flex items-center justify-between gap-2">
        <div>
          <div class="text-xs text-slate-400">Live Price</div>
          <div class="text-lg font-extrabold text-emerald-400 font-mono">
            ${formattedPrice}
          </div>
        </div>

        <a 
          href="${item.product_url}" 
          target="_blank" 
          rel="noopener noreferrer" 
          class="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-slate-800 hover:bg-emerald-500 hover:text-slate-950 text-slate-200 border border-slate-700 hover:border-emerald-400 transition duration-150 shadow-sm"
        >
          <span>Order</span>
          <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
        </a>
      </div>
    `;

    resultsGrid.appendChild(card);
  });

  if (window.lucide) {
    lucide.createIcons();
  }
}

// Event Listeners
searchForm.addEventListener('submit', (e) => {
  e.preventDefault();
  executeSearch(searchInput.value);
});

// Quick tags click
document.querySelectorAll('.quick-tag').forEach(tag => {
  tag.addEventListener('click', () => {
    const q = tag.getAttribute('data-query');
    searchInput.value = q;
    executeSearch(q);
  });
});

// Filter buttons
filterAllBtn.addEventListener('click', () => {
  activeFilter = 'all';
  filterAllBtn.classList.add('bg-emerald-500', 'text-slate-950', 'font-bold');
  filterAllBtn.classList.remove('bg-slate-800', 'text-slate-300');
  filterInStockBtn.classList.remove('bg-emerald-500', 'text-slate-950', 'font-bold');
  filterInStockBtn.classList.add('bg-slate-800', 'text-slate-300');
  renderResults();
});

filterInStockBtn.addEventListener('click', () => {
  activeFilter = 'in_stock';
  filterInStockBtn.classList.add('bg-emerald-500', 'text-slate-950', 'font-bold');
  filterInStockBtn.classList.remove('bg-slate-800', 'text-slate-300');
  filterAllBtn.classList.remove('bg-emerald-500', 'text-slate-950', 'font-bold');
  filterAllBtn.classList.add('bg-slate-800', 'text-slate-300');
  renderResults();
});

sortSelect.addEventListener('change', () => {
  activeSort = sortSelect.value;
  renderResults();
});

// Initialize on Load
document.addEventListener('DOMContentLoaded', () => {
  loadCountries();
  if (window.lucide) lucide.createIcons();
  // Auto search on initial load
  executeSearch(searchInput.value || 'rtx');
});
