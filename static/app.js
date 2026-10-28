// StoreStock Client Application with Store Map & Restock Tracker

let currentResults = [];
let activeFilter = 'all'; // 'all', 'in_stock', 'nearby'
let activeSort = 'relevance';
let activeBrand = null;
let currentView = 'grid'; // 'grid', 'map', 'alerts'
let userCoords = null; // { lat, lon }
let map = null;
let mapMarkers = [];

// DOM Elements
const searchForm = document.getElementById('searchForm');
const searchInput = document.getElementById('searchInput');
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
const filterNearbyBtn = document.getElementById('filterNearby');
const sortSelect = document.getElementById('sortSelect');
const brandFilterContainer = document.getElementById('brandFilterContainer');
const brandChips = document.getElementById('brandChips');

// View Containers
const gridSection = document.getElementById('gridSection');
const mapSection = document.getElementById('mapSection');
const alertsSection = document.getElementById('alertsSection');
const viewGridBtn = document.getElementById('viewGridBtn');
const viewMapBtn = document.getElementById('viewMapBtn');
const viewAlertsBtn = document.getElementById('viewAlertsBtn');
const alertsCountBadge = document.getElementById('alertsCountBadge');
const alertsList = document.getElementById('alertsList');

// Alert Modal Elements
const alertModal = document.getElementById('alertModal');
const closeAlertModalBtn = document.getElementById('closeAlertModalBtn');
const cancelAlertModalBtn = document.getElementById('cancelAlertModalBtn');
const createAlertForm = document.getElementById('createAlertForm');
const alertQueryInput = document.getElementById('alertQueryInput');
const alertStoreInput = document.getElementById('alertStoreInput');
const alertPriceInput = document.getElementById('alertPriceInput');
const alertEmailInput = document.getElementById('alertEmailInput');
const alertProductUrl = document.getElementById('alertProductUrl');
const openNewAlertModalBtn = document.getElementById('openNewAlertModalBtn');
const toast = document.getElementById('toast');
const toastMsg = document.getElementById('toastMsg');

// Accessory & Hardware scoring constants for Smart Recommended Ranking
const ACCESSORY_WORDS = [
  "stand", "suport", "holder", "bracket", "riser", "cablu", "cable",
  "husa", "case", "adaptor", "adapter", "pasta", "paste", "thermal",
  "pad", "ventilator", "fan", "cooler", "montare", "mount", "surub", "suruburi",
  "screws", "splitter", "extensie", "extension", "stickere", "sticker",
  "power supply", "incarcator", "alimentator", "charger", "mouse pad",
  "nvlink", "bridge", "kit", "backplate", "shroud"
];

const HARDWARE_WORDS = [
  "placa video", "placi video", "graphics card", "video card", "gpu"
];

function scoreRelevance(query, title, price, inStock) {
  const qClean = (query || "").toLowerCase().trim();
  const tClean = (title || "").toLowerCase().trim();
  const qTokens = qClean.split(/\s+/).filter(w => w.length > 1);

  if (qTokens.length === 0) return 0;

  let score = 0;

  const userAskedAccessory = ACCESSORY_WORDS.some(acc => qClean.includes(acc));
  const titleHasAccessory = ACCESSORY_WORDS.some(acc => tClean.includes(acc));
  
  // Severe accessory penalty
  if (titleHasAccessory && !userAskedAccessory) {
    score -= 500;
  }

  const PREBUILTS = [
    "desktop pc", "server supermicro", "server dell", "server asus",
    "superworkstation", "sistem desktop", "workstation tower", "tower 2u",
    "rack 2u", "rack 4u", "server poweredge", "laptop", "notebook",
    "server", "rack", "barebone"
  ];
  const userWantsPrebuilt = ["desktop", "server", "sistem", "workstation", "laptop", "pc complet"].some(k => qClean.includes(k));

  const isGpu = ["rtx", "gtx", "radeon", "a6000", "blackwell", "geforce", "gpu"].some(k => qClean.includes(k));
  if (isGpu) {
    // Dominant bonus for standalone graphics cards
    const isDiscreteCard = HARDWARE_WORDS.some(h => tClean.includes(h)) || tClean.includes("rtx a6000") || tClean.includes("rtx 6000");
    if (isDiscreteCard && !titleHasAccessory) {
      score += 350;
    }
    
    // Penalize full server racks and whole PC towers
    if (!userWantsPrebuilt && PREBUILTS.some(p => tClean.includes(p))) {
      score -= 400;
    }

    // Price sanity: an A6000 is not under 1500 RON
    if (price > 0 && price < 1500 && !userAskedAccessory) {
      score -= 300;
    }
  }

  // Token matching
  const matched = qTokens.filter(t => tClean.includes(t));
  const coverage = matched.length / qTokens.length;
  score += coverage * 100;

  if (coverage < 1.0) score -= 50 * (1.0 - coverage);

  // In-stock priority bonus (moderate, so it never causes a cable to beat a card)
  if (inStock) score += 50;

  return score;
}

// Major Cities Database per Country for Dynamic Location Examples (All 49 Supported Countries)
const COUNTRY_CITIES = {
  AU: {
    country: "Australia",
    defaultCity: "Sydney",
    defaultLat: -33.8688,
    defaultLon: 151.2093,
    cities: [
      { name: "Sydney", lat: -33.8688, lon: 151.2093 },
      { name: "Melbourne", lat: -37.8136, lon: 144.9631 },
      { name: "Brisbane", lat: -27.4698, lon: 153.0251 },
      { name: "Perth", lat: -31.9505, lon: 115.8605 },
      { name: "Adelaide", lat: -34.9285, lon: 138.6007 },
      { name: "Canberra", lat: -35.2809, lon: 149.1300 },
      { name: "Gold Coast", lat: -28.0167, lon: 153.4000 },
      { name: "Hobart", lat: -42.8821, lon: 147.3272 }
    ]
  },
  RO: {
    country: "Romania",
    defaultCity: "București",
    defaultLat: 44.4323,
    defaultLon: 26.1063,
    cities: [
      { name: "București", lat: 44.4323, lon: 26.1063 },
      { name: "Cluj-Napoca", lat: 46.7712, lon: 23.6236 },
      { name: "Timișoara", lat: 45.7489, lon: 21.2087 },
      { name: "Iași", lat: 47.1585, lon: 27.6014 },
      { name: "Brașov", lat: 45.6579, lon: 25.6012 },
      { name: "Constanța", lat: 44.1792, lon: 28.6498 },
      { name: "Craiova", lat: 44.3302, lon: 23.7949 },
      { name: "Sibiu", lat: 45.7983, lon: 24.1256 },
      { name: "Oradea", lat: 47.0465, lon: 21.9189 },
      { name: "Ploiești", lat: 44.9402, lon: 26.0227 },
      { name: "Galați", lat: 45.4353, lon: 28.0080 }
    ]
  },
  US: {
    country: "United States",
    defaultCity: "New York",
    defaultLat: 40.7128,
    defaultLon: -74.0060,
    cities: [
      { name: "New York", lat: 40.7128, lon: -74.0060 },
      { name: "Los Angeles", lat: 34.0522, lon: -118.2437 },
      { name: "Chicago", lat: 41.8781, lon: -87.6298 },
      { name: "Houston", lat: 29.7604, lon: -95.3698 },
      { name: "San Francisco", lat: 37.7749, lon: -122.4194 },
      { name: "Seattle", lat: 47.6062, lon: -122.3321 },
      { name: "Austin", lat: 30.2672, lon: -97.7431 },
      { name: "Miami", lat: 25.7617, lon: -80.1918 },
      { name: "Boston", lat: 42.3601, lon: -71.0589 },
      { name: "Denver", lat: 39.7392, lon: -104.9903 }
    ]
  },
  GB: {
    country: "United Kingdom",
    defaultCity: "London",
    defaultLat: 51.5074,
    defaultLon: -0.1278,
    cities: [
      { name: "London", lat: 51.5074, lon: -0.1278 },
      { name: "Manchester", lat: 53.4808, lon: -2.2426 },
      { name: "Birmingham", lat: 52.4862, lon: -1.8904 },
      { name: "Leeds", lat: 53.8008, lon: -1.5491 },
      { name: "Glasgow", lat: 55.8642, lon: -4.2518 },
      { name: "Edinburgh", lat: 55.9533, lon: -3.1883 },
      { name: "Liverpool", lat: 53.4084, lon: -2.9916 },
      { name: "Bristol", lat: 51.4545, lon: -2.5879 }
    ]
  },
  DE: {
    country: "Germany",
    defaultCity: "Berlin",
    defaultLat: 52.5200,
    defaultLon: 13.4050,
    cities: [
      { name: "Berlin", lat: 52.5200, lon: 13.4050 },
      { name: "Munich", lat: 48.1351, lon: 11.5820 },
      { name: "Frankfurt", lat: 50.1109, lon: 8.6821 },
      { name: "Hamburg", lat: 53.5511, lon: 9.9937 },
      { name: "Cologne", lat: 50.9375, lon: 6.9603 },
      { name: "Stuttgart", lat: 48.7758, lon: 9.1829 },
      { name: "Düsseldorf", lat: 51.2277, lon: 6.7735 },
      { name: "Leipzig", lat: 51.3397, lon: 12.3731 }
    ]
  },
  CA: {
    country: "Canada",
    defaultCity: "Toronto",
    defaultLat: 43.6532,
    defaultLon: -79.3832,
    cities: [
      { name: "Toronto", lat: 43.6532, lon: -79.3832 },
      { name: "Vancouver", lat: 49.2827, lon: -123.1207 },
      { name: "Montreal", lat: 45.5017, lon: -73.5673 },
      { name: "Calgary", lat: 51.0447, lon: -114.0719 },
      { name: "Ottawa", lat: 45.4215, lon: -75.6972 },
      { name: "Edmonton", lat: 53.5461, lon: -113.4938 },
      { name: "Quebec City", lat: 46.8139, lon: -71.2080 }
    ]
  },
  FR: {
    country: "France",
    defaultCity: "Paris",
    defaultLat: 48.8566,
    defaultLon: 2.3522,
    cities: [
      { name: "Paris", lat: 48.8566, lon: 2.3522 },
      { name: "Marseille", lat: 43.2965, lon: 5.3698 },
      { name: "Lyon", lat: 45.7640, lon: 4.8357 },
      { name: "Toulouse", lat: 43.6047, lon: 1.4442 },
      { name: "Nice", lat: 43.7102, lon: 7.2620 },
      { name: "Nantes", lat: 47.2184, lon: -1.5536 },
      { name: "Strasbourg", lat: 48.5734, lon: 7.7521 },
      { name: "Bordeaux", lat: 44.8378, lon: -0.5792 }
    ]
  },
  IT: {
    country: "Italy",
    defaultCity: "Rome",
    defaultLat: 41.9028,
    defaultLon: 12.4964,
    cities: [
      { name: "Rome", lat: 41.9028, lon: 12.4964 },
      { name: "Milan", lat: 45.4642, lon: 9.1900 },
      { name: "Naples", lat: 40.8518, lon: 14.2681 },
      { name: "Turin", lat: 45.0703, lon: 7.6869 },
      { name: "Florence", lat: 43.7696, lon: 11.2558 },
      { name: "Bologna", lat: 44.4949, lon: 11.3426 },
      { name: "Venice", lat: 45.4408, lon: 12.3155 },
      { name: "Palermo", lat: 38.1157, lon: 13.3615 }
    ]
  },
  ES: {
    country: "Spain",
    defaultCity: "Madrid",
    defaultLat: 40.4168,
    defaultLon: -3.7038,
    cities: [
      { name: "Madrid", lat: 40.4168, lon: -3.7038 },
      { name: "Barcelona", lat: 41.3851, lon: 2.1734 },
      { name: "Valencia", lat: 39.4699, lon: -0.3763 },
      { name: "Seville", lat: 37.3891, lon: -5.9845 },
      { name: "Zaragoza", lat: 41.6488, lon: -0.8891 },
      { name: "Málaga", lat: 36.7213, lon: -4.4214 },
      { name: "Bilbao", lat: 43.2630, lon: -2.9350 }
    ]
  },
  NL: {
    country: "Netherlands",
    defaultCity: "Amsterdam",
    defaultLat: 52.3676,
    defaultLon: 4.9041,
    cities: [
      { name: "Amsterdam", lat: 52.3676, lon: 4.9041 },
      { name: "Rotterdam", lat: 51.9244, lon: 4.4777 },
      { name: "The Hague", lat: 52.0705, lon: 4.3007 },
      { name: "Utrecht", lat: 52.0907, lon: 5.1214 },
      { name: "Eindhoven", lat: 51.4416, lon: 5.4697 },
      { name: "Groningen", lat: 53.2194, lon: 6.5665 }
    ]
  },
  PL: {
    country: "Poland",
    defaultCity: "Warsaw",
    defaultLat: 52.2297,
    defaultLon: 21.0122,
    cities: [
      { name: "Warsaw", lat: 52.2297, lon: 21.0122 },
      { name: "Kraków", lat: 50.0647, lon: 19.9450 },
      { name: "Wrocław", lat: 51.1079, lon: 17.0385 },
      { name: "Poznań", lat: 52.4064, lon: 16.9252 },
      { name: "Gdańsk", lat: 54.3520, lon: 18.6466 },
      { name: "Łódź", lat: 51.7592, lon: 19.4560 },
      { name: "Katowice", lat: 50.2649, lon: 19.0238 }
    ]
  },
  JP: {
    country: "Japan",
    defaultCity: "Tokyo",
    defaultLat: 35.6762,
    defaultLon: 139.6503,
    cities: [
      { name: "Tokyo", lat: 35.6762, lon: 139.6503 },
      { name: "Yokohama", lat: 35.4437, lon: 139.6380 },
      { name: "Osaka", lat: 34.6937, lon: 135.5023 },
      { name: "Nagoya", lat: 35.1815, lon: 136.9066 },
      { name: "Sapporo", lat: 43.0618, lon: 141.3545 },
      { name: "Fukuoka", lat: 33.5904, lon: 130.4017 },
      { name: "Kyoto", lat: 35.0116, lon: 135.7681 }
    ]
  },
  KR: {
    country: "South Korea",
    defaultCity: "Seoul",
    defaultLat: 37.5665,
    defaultLon: 126.9780,
    cities: [
      { name: "Seoul", lat: 37.5665, lon: 126.9780 },
      { name: "Busan", lat: 35.1796, lon: 129.0756 },
      { name: "Incheon", lat: 37.4563, lon: 126.7052 },
      { name: "Daegu", lat: 35.8714, lon: 128.6014 },
      { name: "Daejeon", lat: 36.3504, lon: 127.3845 },
      { name: "Suwon", lat: 37.2636, lon: 127.0286 }
    ]
  },
  IN: {
    country: "India",
    defaultCity: "New Delhi",
    defaultLat: 28.6139,
    defaultLon: 77.2090,
    cities: [
      { name: "New Delhi", lat: 28.6139, lon: 77.2090 },
      { name: "Mumbai", lat: 19.0760, lon: 72.8777 },
      { name: "Bengaluru", lat: 12.9716, lon: 77.5946 },
      { name: "Hyderabad", lat: 17.3850, lon: 78.4867 },
      { name: "Chennai", lat: 13.0827, lon: 80.2707 },
      { name: "Kolkata", lat: 22.5726, lon: 88.3639 },
      { name: "Pune", lat: 18.5204, lon: 73.8567 },
      { name: "Ahmedabad", lat: 23.0225, lon: 72.5714 }
    ]
  },
  BR: {
    country: "Brazil",
    defaultCity: "São Paulo",
    defaultLat: -23.5505,
    defaultLon: -46.6333,
    cities: [
      { name: "São Paulo", lat: -23.5505, lon: -46.6333 },
      { name: "Rio de Janeiro", lat: -22.9068, lon: -43.1729 },
      { name: "Brasília", lat: -15.7975, lon: -47.8919 },
      { name: "Belo Horizonte", lat: -19.9167, lon: -43.9345 },
      { name: "Curitiba", lat: -25.4290, lon: -49.2671 },
      { name: "Salvador", lat: -12.9777, lon: -38.5016 },
      { name: "Porto Alegre", lat: -30.0346, lon: -51.2177 }
    ]
  },
  MX: {
    country: "Mexico",
    defaultCity: "Mexico City",
    defaultLat: 19.4326,
    defaultLon: -99.1332,
    cities: [
      { name: "Mexico City", lat: 19.4326, lon: -99.1332 },
      { name: "Guadalajara", lat: 20.6597, lon: -103.3496 },
      { name: "Monterrey", lat: 25.6866, lon: -100.3161 },
      { name: "Puebla", lat: 19.0414, lon: -98.2063 },
      { name: "Tijuana", lat: 32.5149, lon: -117.0382 },
      { name: "Cancún", lat: 21.1619, lon: -86.8515 }
    ]
  },
  SE: {
    country: "Sweden",
    defaultCity: "Stockholm",
    defaultLat: 59.3293,
    defaultLon: 18.0686,
    cities: [
      { name: "Stockholm", lat: 59.3293, lon: 18.0686 },
      { name: "Gothenburg", lat: 57.7089, lon: 11.9746 },
      { name: "Malmö", lat: 55.6050, lon: 13.0038 },
      { name: "Uppsala", lat: 59.8586, lon: 17.6389 },
      { name: "Västerås", lat: 59.6162, lon: 16.5528 }
    ]
  },
  CH: {
    country: "Switzerland",
    defaultCity: "Zurich",
    defaultLat: 47.3769,
    defaultLon: 8.5417,
    cities: [
      { name: "Zurich", lat: 47.3769, lon: 8.5417 },
      { name: "Geneva", lat: 46.2044, lon: 6.1432 },
      { name: "Basel", lat: 47.5596, lon: 7.5886 },
      { name: "Lausanne", lat: 46.5197, lon: 6.6323 },
      { name: "Bern", lat: 46.9480, lon: 7.4474 },
      { name: "Lucerne", lat: 47.0502, lon: 8.3093 }
    ]
  },
  AT: {
    country: "Austria",
    defaultCity: "Vienna",
    defaultLat: 48.2082,
    defaultLon: 16.3738,
    cities: [
      { name: "Vienna", lat: 48.2082, lon: 16.3738 },
      { name: "Graz", lat: 47.0707, lon: 15.4395 },
      { name: "Linz", lat: 48.3069, lon: 14.2858 },
      { name: "Salzburg", lat: 47.8095, lon: 13.0550 },
      { name: "Innsbruck", lat: 47.2692, lon: 11.4041 }
    ]
  },
  BE: {
    country: "Belgium",
    defaultCity: "Brussels",
    defaultLat: 50.8503,
    defaultLon: 4.3517,
    cities: [
      { name: "Brussels", lat: 50.8503, lon: 4.3517 },
      { name: "Antwerp", lat: 51.2194, lon: 4.4025 },
      { name: "Ghent", lat: 51.0543, lon: 3.7174 },
      { name: "Bruges", lat: 51.2093, lon: 3.2247 },
      { name: "Liège", lat: 50.6326, lon: 5.5797 }
    ]
  },
  NO: {
    country: "Norway",
    defaultCity: "Oslo",
    defaultLat: 59.9139,
    defaultLon: 10.7522,
    cities: [
      { name: "Oslo", lat: 59.9139, lon: 10.7522 },
      { name: "Bergen", lat: 60.3913, lon: 5.3221 },
      { name: "Trondheim", lat: 63.4305, lon: 10.3951 },
      { name: "Stavanger", lat: 58.9700, lon: 5.7331 },
      { name: "Tromsø", lat: 69.6492, lon: 18.9553 }
    ]
  },
  DK: {
    country: "Denmark",
    defaultCity: "Copenhagen",
    defaultLat: 55.6761,
    defaultLon: 12.5683,
    cities: [
      { name: "Copenhagen", lat: 55.6761, lon: 12.5683 },
      { name: "Aarhus", lat: 56.1629, lon: 10.2039 },
      { name: "Odense", lat: 55.4038, lon: 10.4024 },
      { name: "Aalborg", lat: 57.0488, lon: 9.9217 }
    ]
  },
  FI: {
    country: "Finland",
    defaultCity: "Helsinki",
    defaultLat: 60.1699,
    defaultLon: 24.9384,
    cities: [
      { name: "Helsinki", lat: 60.1699, lon: 24.9384 },
      { name: "Espoo", lat: 60.2055, lon: 24.6559 },
      { name: "Tampere", lat: 61.4978, lon: 23.7610 },
      { name: "Vantaa", lat: 60.2934, lon: 25.0378 },
      { name: "Oulu", lat: 65.0121, lon: 25.4651 },
      { name: "Turku", lat: 60.4518, lon: 22.2666 }
    ]
  },
  CZ: {
    country: "Czech Republic",
    defaultCity: "Prague",
    defaultLat: 50.0755,
    defaultLon: 14.4378,
    cities: [
      { name: "Prague", lat: 50.0755, lon: 14.4378 },
      { name: "Brno", lat: 49.1951, lon: 16.6068 },
      { name: "Ostrava", lat: 49.8209, lon: 18.2625 },
      { name: "Plzeň", lat: 49.7384, lon: 13.3736 },
      { name: "Liberec", lat: 50.7663, lon: 15.0543 }
    ]
  },
  HU: {
    country: "Hungary",
    defaultCity: "Budapest",
    defaultLat: 47.4979,
    defaultLon: 19.0402,
    cities: [
      { name: "Budapest", lat: 47.4979, lon: 19.0402 },
      { name: "Debrecen", lat: 47.5316, lon: 21.6273 },
      { name: "Szeged", lat: 46.2530, lon: 20.1414 },
      { name: "Miskolc", lat: 48.1035, lon: 20.7784 },
      { name: "Pécs", lat: 46.0727, lon: 18.2323 },
      { name: "Győr", lat: 47.6875, lon: 17.6504 }
    ]
  },
  GR: {
    country: "Greece",
    defaultCity: "Athens",
    defaultLat: 37.9838,
    defaultLon: 23.7275,
    cities: [
      { name: "Athens", lat: 37.9838, lon: 23.7275 },
      { name: "Thessaloniki", lat: 40.6401, lon: 22.9444 },
      { name: "Patras", lat: 38.2466, lon: 21.7346 },
      { name: "Heraklion", lat: 35.3387, lon: 25.1442 },
      { name: "Larissa", lat: 39.6390, lon: 22.4191 }
    ]
  },
  PT: {
    country: "Portugal",
    defaultCity: "Lisbon",
    defaultLat: 38.7223,
    defaultLon: -9.1393,
    cities: [
      { name: "Lisbon", lat: 38.7223, lon: -9.1393 },
      { name: "Porto", lat: 41.1579, lon: -8.6291 },
      { name: "Vila Nova de Gaia", lat: 41.1239, lon: -8.6118 },
      { name: "Braga", lat: 41.5454, lon: -8.4265 },
      { name: "Coimbra", lat: 40.2033, lon: -8.4103 },
      { name: "Faro", lat: 37.0194, lon: -7.9304 }
    ]
  },
  IE: {
    country: "Ireland",
    defaultCity: "Dublin",
    defaultLat: 53.3498,
    defaultLon: -6.2603,
    cities: [
      { name: "Dublin", lat: 53.3498, lon: -6.2603 },
      { name: "Cork", lat: 51.8985, lon: -8.4756 },
      { name: "Limerick", lat: 52.6638, lon: -8.6267 },
      { name: "Galway", lat: 53.2707, lon: -9.0568 },
      { name: "Waterford", lat: 52.2593, lon: -7.1101 }
    ]
  },
  NZ: {
    country: "New Zealand",
    defaultCity: "Auckland",
    defaultLat: -36.8485,
    defaultLon: 174.7633,
    cities: [
      { name: "Auckland", lat: -36.8485, lon: 174.7633 },
      { name: "Wellington", lat: -41.2865, lon: 174.7762 },
      { name: "Christchurch", lat: -43.5321, lon: 172.6362 },
      { name: "Hamilton", lat: -37.7870, lon: 175.2793 },
      { name: "Tauranga", lat: -37.6878, lon: 176.1651 }
    ]
  },
  SG: {
    country: "Singapore",
    defaultCity: "Singapore",
    defaultLat: 1.3521,
    defaultLon: 103.8198,
    cities: [
      { name: "Singapore", lat: 1.3521, lon: 103.8198 },
      { name: "Jurong East", lat: 1.3329, lon: 103.7436 },
      { name: "Tampines", lat: 1.3526, lon: 103.9447 },
      { name: "Woodlands", lat: 1.4382, lon: 103.7890 }
    ]
  },
  AE: {
    country: "United Arab Emirates",
    defaultCity: "Dubai",
    defaultLat: 25.2048,
    defaultLon: 55.2708,
    cities: [
      { name: "Dubai", lat: 25.2048, lon: 55.2708 },
      { name: "Abu Dhabi", lat: 24.4539, lon: 54.3773 },
      { name: "Sharjah", lat: 25.3463, lon: 55.4209 },
      { name: "Al Ain", lat: 24.2075, lon: 55.7447 },
      { name: "Ajman", lat: 25.4052, lon: 55.5136 }
    ]
  },
  SA: {
    country: "Saudi Arabia",
    defaultCity: "Riyadh",
    defaultLat: 24.7136,
    defaultLon: 46.6753,
    cities: [
      { name: "Riyadh", lat: 24.7136, lon: 46.6753 },
      { name: "Jeddah", lat: 21.4858, lon: 39.1925 },
      { name: "Mecca", lat: 21.3891, lon: 39.8579 },
      { name: "Medina", lat: 24.5247, lon: 39.5692 },
      { name: "Dammam", lat: 26.4207, lon: 50.0888 }
    ]
  },
  IL: {
    country: "Israel",
    defaultCity: "Tel Aviv",
    defaultLat: 32.0853,
    defaultLon: 34.7818,
    cities: [
      { name: "Tel Aviv", lat: 32.0853, lon: 34.7818 },
      { name: "Jerusalem", lat: 31.7683, lon: 35.2137 },
      { name: "Haifa", lat: 32.7940, lon: 34.9896 },
      { name: "Rishon LeZion", lat: 31.9730, lon: 34.7925 },
      { name: "Petah Tikva", lat: 32.0840, lon: 34.8878 }
    ]
  },
  TR: {
    country: "Turkey",
    defaultCity: "Istanbul",
    defaultLat: 41.0082,
    defaultLon: 28.9784,
    cities: [
      { name: "Istanbul", lat: 41.0082, lon: 28.9784 },
      { name: "Ankara", lat: 39.9334, lon: 32.8597 },
      { name: "Izmir", lat: 38.4237, lon: 27.1428 },
      { name: "Bursa", lat: 40.1885, lon: 29.0610 },
      { name: "Antalya", lat: 36.8969, lon: 30.7133 },
      { name: "Adana", lat: 36.9914, lon: 35.3308 }
    ]
  },
  ZA: {
    country: "South Africa",
    defaultCity: "Johannesburg",
    defaultLat: -26.2041,
    defaultLon: 28.0473,
    cities: [
      { name: "Johannesburg", lat: -26.2041, lon: 28.0473 },
      { name: "Cape Town", lat: -33.9249, lon: 18.4241 },
      { name: "Durban", lat: -29.8587, lon: 31.0218 },
      { name: "Pretoria", lat: -25.7479, lon: 28.2293 },
      { name: "Port Elizabeth", lat: -33.9608, lon: 25.6022 }
    ]
  },
  AR: {
    country: "Argentina",
    defaultCity: "Buenos Aires",
    defaultLat: -34.6037,
    defaultLon: -58.3816,
    cities: [
      { name: "Buenos Aires", lat: -34.6037, lon: -58.3816 },
      { name: "Córdoba", lat: -31.4201, lon: -64.1888 },
      { name: "Rosario", lat: -32.9587, lon: -60.6930 },
      { name: "Mendoza", lat: -32.8895, lon: -68.8458 },
      { name: "La Plata", lat: -34.9215, lon: -57.9545 }
    ]
  },
  CL: {
    country: "Chile",
    defaultCity: "Santiago",
    defaultLat: -33.4489,
    defaultLon: -70.6693,
    cities: [
      { name: "Santiago", lat: -33.4489, lon: -70.6693 },
      { name: "Valparaíso", lat: -33.0472, lon: -71.6127 },
      { name: "Concepción", lat: -36.8270, lon: -73.0503 },
      { name: "La Serena", lat: -29.9027, lon: -71.2519 },
      { name: "Antofagasta", lat: -23.6509, lon: -70.3975 }
    ]
  },
  CO: {
    country: "Colombia",
    defaultCity: "Bogotá",
    defaultLat: 4.7110,
    defaultLon: -74.0721,
    cities: [
      { name: "Bogotá", lat: 4.7110, lon: -74.0721 },
      { name: "Medellín", lat: 6.2442, lon: -75.5812 },
      { name: "Cali", lat: 3.4516, lon: -76.5320 },
      { name: "Barranquilla", lat: 10.9685, lon: -74.7813 },
      { name: "Cartagena", lat: 10.3910, lon: -75.4794 }
    ]
  },
  ID: {
    country: "Indonesia",
    defaultCity: "Jakarta",
    defaultLat: -6.2088,
    defaultLon: 106.8456,
    cities: [
      { name: "Jakarta", lat: -6.2088, lon: 106.8456 },
      { name: "Surabaya", lat: -7.2575, lon: 112.7521 },
      { name: "Bandung", lat: -6.9175, lon: 107.6191 },
      { name: "Medan", lat: 3.5952, lon: 98.6722 },
      { name: "Bekasi", lat: -6.2383, lon: 106.9756 }
    ]
  },
  MY: {
    country: "Malaysia",
    defaultCity: "Kuala Lumpur",
    defaultLat: 3.1390,
    defaultLon: 101.6869,
    cities: [
      { name: "Kuala Lumpur", lat: 3.1390, lon: 101.6869 },
      { name: "George Town", lat: 5.4141, lon: 100.3288 },
      { name: "Johor Bahru", lat: 1.4927, lon: 103.7414 },
      { name: "Ipoh", lat: 4.5975, lon: 101.0901 },
      { name: "Petaling Jaya", lat: 3.1073, lon: 101.6067 }
    ]
  },
  PH: {
    country: "Philippines",
    defaultCity: "Manila",
    defaultLat: 14.5995,
    defaultLon: 120.9842,
    cities: [
      { name: "Manila", lat: 14.5995, lon: 120.9842 },
      { name: "Quezon City", lat: 14.6760, lon: 121.0437 },
      { name: "Davao City", lat: 7.1907, lon: 125.4578 },
      { name: "Cebu City", lat: 10.3157, lon: 123.8854 },
      { name: "Taguig", lat: 14.5176, lon: 121.0509 }
    ]
  },
  TH: {
    country: "Thailand",
    defaultCity: "Bangkok",
    defaultLat: 13.7563,
    defaultLon: 100.5018,
    cities: [
      { name: "Bangkok", lat: 13.7563, lon: 100.5018 },
      { name: "Chiang Mai", lat: 18.7883, lon: 98.9853 },
      { name: "Pattaya", lat: 12.9236, lon: 100.8825 },
      { name: "Nonthaburi", lat: 13.8591, lon: 100.5217 },
      { name: "Hat Yai", lat: 7.0084, lon: 100.4767 }
    ]
  },
  VN: {
    country: "Vietnam",
    defaultCity: "Ho Chi Minh City",
    defaultLat: 10.8231,
    defaultLon: 106.6297,
    cities: [
      { name: "Ho Chi Minh City", lat: 10.8231, lon: 106.6297 },
      { name: "Hanoi", lat: 21.0285, lon: 105.8542 },
      { name: "Da Nang", lat: 16.0544, lon: 108.2022 },
      { name: "Hai Phong", lat: 20.8449, lon: 106.6881 },
      { name: "Can Tho", lat: 10.0452, lon: 105.7469 }
    ]
  },
  UA: {
    country: "Ukraine",
    defaultCity: "Kyiv",
    defaultLat: 50.4501,
    defaultLon: 30.5234,
    cities: [
      { name: "Kyiv", lat: 50.4501, lon: 30.5234 },
      { name: "Kharkiv", lat: 49.9935, lon: 36.2304 },
      { name: "Odesa", lat: 46.4825, lon: 30.7233 },
      { name: "Dnipro", lat: 48.4647, lon: 35.0462 },
      { name: "Lviv", lat: 49.8397, lon: 24.0297 }
    ]
  },
  KZ: {
    country: "Kazakhstan",
    defaultCity: "Almaty",
    defaultLat: 43.2220,
    defaultLon: 76.8512,
    cities: [
      { name: "Almaty", lat: 43.2220, lon: 76.8512 },
      { name: "Astana", lat: 51.1694, lon: 71.4491 },
      { name: "Shymkent", lat: 42.3417, lon: 69.5901 },
      { name: "Karaganda", lat: 49.8047, lon: 73.1094 }
    ]
  },
  EG: {
    country: "Egypt",
    defaultCity: "Cairo",
    defaultLat: 30.0444,
    defaultLon: 31.2357,
    cities: [
      { name: "Cairo", lat: 30.0444, lon: 31.2357 },
      { name: "Alexandria", lat: 31.2001, lon: 29.9187 },
      { name: "Giza", lat: 30.0131, lon: 31.2089 },
      { name: "Port Said", lat: 31.2653, lon: 32.3019 }
    ]
  },
  PE: {
    country: "Peru",
    defaultCity: "Lima",
    defaultLat: -12.0464,
    defaultLon: -77.0428,
    cities: [
      { name: "Lima", lat: -12.0464, lon: -77.0428 },
      { name: "Arequipa", lat: -16.4090, lon: -71.5375 },
      { name: "Trujillo", lat: -8.1118, lon: -79.0288 },
      { name: "Cusco", lat: -13.5319, lon: -71.9675 }
    ]
  },
  QA: {
    country: "Qatar",
    defaultCity: "Doha",
    defaultLat: 25.2854,
    defaultLon: 51.5310,
    cities: [
      { name: "Doha", lat: 25.2854, lon: 51.5310 },
      { name: "Al Rayyan", lat: 25.2919, lon: 51.4244 },
      { name: "Al Wakrah", lat: 25.1768, lon: 51.6048 },
      { name: "Al Khor", lat: 25.6839, lon: 51.5058 }
    ]
  },
  CN: {
    country: "China",
    defaultCity: "Beijing",
    defaultLat: 39.9042,
    defaultLon: 116.4074,
    cities: [
      { name: "Beijing", lat: 39.9042, lon: 116.4074 },
      { name: "Shanghai", lat: 31.2304, lon: 121.4737 },
      { name: "Guangzhou", lat: 23.1291, lon: 113.2644 },
      { name: "Shenzhen", lat: 22.5431, lon: 114.0579 },
      { name: "Chengdu", lat: 30.5728, lon: 104.0668 },
      { name: "Hangzhou", lat: 30.2741, lon: 120.1551 },
      { name: "Wuhan", lat: 30.5928, lon: 114.3055 }
    ]
  }
};

function detectClientCountryFallback() {
  try {
    const tz = (Intl.DateTimeFormat().resolvedOptions().timeZone || "").toLowerCase();
    if (tz.includes("australia") || tz.includes("sydney") || tz.includes("melbourne") || tz.includes("perth") || tz.includes("brisbane") || tz.includes("adelaide")) return "AU";
    if (tz.includes("bucharest") || tz.includes("chisinau")) return "RO";
    if (tz.includes("london")) return "GB";
    if (tz.includes("berlin") || tz.includes("frankfurt")) return "DE";
    if (tz.includes("paris")) return "FR";
    if (tz.includes("new_york") || tz.includes("chicago") || tz.includes("los_angeles") || tz.includes("denver")) return "US";
    if (tz.includes("toronto") || tz.includes("vancouver") || tz.includes("montreal")) return "CA";
    if (tz.includes("madrid")) return "ES";
    if (tz.includes("rome")) return "IT";
    if (tz.includes("amsterdam")) return "NL";
    if (tz.includes("warsaw")) return "PL";
  } catch (e) {}
  return null;
}

function renderMajorCities(countryCode) {
  const code = (countryCode || 'RO').toUpperCase();
  const cData = COUNTRY_CITIES[code] || COUNTRY_CITIES['RO'];
  const container = document.getElementById('majorCitiesContainer');
  const title = document.getElementById('majorCitiesTitle');
  const skipBtn = document.getElementById('skipLocationBtn');
  const customInput = document.getElementById('customCityInput');

  if (title) {
    title.textContent = `Major Cities Examples (${cData.country}):`;
  }

  if (customInput && cData.cities && cData.cities.length >= 3) {
    customInput.placeholder = `e.g. ${cData.cities[0].name}, ${cData.cities[1].name}, ${cData.cities[2].name}...`;
  }

  if (skipBtn) {
    skipBtn.textContent = `Continue with default location (${cData.defaultCity}) →`;
    skipBtn.onclick = () => {
      if (locationModal) locationModal.classList.add('hidden');
      const def = cData.cities.find(c => c.name === cData.defaultCity) || cData.cities[0];
      setLocation(def.name, def.lat, def.lon);
      showToast(`Using default location (${def.name}). You can change it anytime in the header.`);
    };
  }

  if (container) {
    container.innerHTML = '';
    cData.cities.forEach(city => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'city-quick-btn px-2.5 py-1.5 rounded-lg bg-slate-800/90 hover:bg-emerald-500 hover:text-slate-950 border border-slate-700/80 text-slate-300 font-medium transition cursor-pointer';
      btn.textContent = `📍 ${city.name}`;
      btn.onclick = () => {
        setLocation(city.name, city.lat, city.lon);
        if (locationModal) locationModal.classList.add('hidden');
      };
      container.appendChild(btn);
    });
  }
}

let currentDetectedCountry = 'RO';
let currentDetectedCityInfo = null;

// Direct Client-Side Geolocation powered by Cloudflare's Edge Identifier
async function detectVisitorLocation() {
  // SOURCE 1: Cloudflare Edge Trace (/cdn-cgi/trace on current domain)
  // This is direct from Cloudflare's edge proxy, completely unblockable, and zero CORS!
  try {
    const res = await fetch('/cdn-cgi/trace', { signal: AbortSignal.timeout(2000) });
    if (res.ok) {
      const text = await res.text();
      const locMatch = text.match(/^loc=([A-Za-z]{2})/m);
      if (locMatch) {
        const cCode = locMatch[1].toUpperCase();
        if (COUNTRY_CITIES[cCode]) {
          const cData = COUNTRY_CITIES[cCode];
          return {
            countryCode: cCode,
            countryName: cData.country,
            city: cData.defaultCity,
            lat: cData.defaultLat,
            lon: cData.defaultLon,
            source: 'cloudflare_edge'
          };
        }
      }
    }
  } catch (e) {}

  // SOURCE 2: Cloudflare Global Edge Fallbacks
  const globalCf = ['https://www.cloudflare.com/cdn-cgi/trace', 'https://1.1.1.1/cdn-cgi/trace'];
  for (const url of globalCf) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(2000) });
      if (res.ok) {
        const text = await res.text();
        const locMatch = text.match(/^loc=([A-Za-z]{2})/m);
        if (locMatch) {
          const cCode = locMatch[1].toUpperCase();
          if (COUNTRY_CITIES[cCode]) {
            const cData = COUNTRY_CITIES[cCode];
            return {
              countryCode: cCode,
              countryName: cData.country,
              city: cData.defaultCity,
              lat: cData.defaultLat,
              lon: cData.defaultLon,
              source: 'cloudflare_global'
            };
          }
        }
      }
    } catch (e) {}
  }

  // SOURCE 3: Backend API /api/detect-country
  try {
    const res = await fetch('/api/detect-country', { signal: AbortSignal.timeout(2000) });
    const data = await res.json();
    if (data && data.country && COUNTRY_CITIES[data.country]) {
      const cData = COUNTRY_CITIES[data.country];
      return {
        countryCode: data.country,
        countryName: cData.country,
        city: cData.defaultCity,
        lat: cData.defaultLat,
        lon: cData.defaultLon,
        source: 'backend_header'
      };
    }
  } catch (e) {}

  // SOURCE 4: ipwho.is IP Geolocation
  try {
    const res = await fetch('https://ipwho.is/', { signal: AbortSignal.timeout(2500) });
    const data = await res.json();
    if (data && data.success && data.country_code && COUNTRY_CITIES[data.country_code]) {
      return {
        countryCode: data.country_code.toUpperCase(),
        countryName: data.country,
        city: data.city,
        lat: data.latitude,
        lon: data.longitude,
        source: 'ipwho'
      };
    }
  } catch (e) {}

  return null;
}

// Populate Country Selector & Auto-detect via VPN IP
async function loadCountries() {
  try {
    const res = await fetch('/api/countries');
    const data = await res.json();
    if (!countrySelect) return;
    countrySelect.innerHTML = '';
    
    // Auto-detect visitor's country directly through their VPN tunnel
    currentDetectedCityInfo = await detectVisitorLocation();
    if (currentDetectedCityInfo && currentDetectedCityInfo.countryCode && data[currentDetectedCityInfo.countryCode]) {
      currentDetectedCountry = currentDetectedCityInfo.countryCode;
    } else {
      const tzCountry = detectClientCountryFallback();
      if (tzCountry && data[tzCountry]) currentDetectedCountry = tzCountry;
    }

    const sorted = Object.entries(data).sort((a, b) => {
      if (a[0] === currentDetectedCountry) return -1;
      if (b[0] === currentDetectedCountry) return 1;
      return a[1].name.localeCompare(b[1].name);
    });

    for (const [code, info] of sorted) {
      const opt = document.createElement('option');
      opt.value = code;
      opt.textContent = `${info.flag} ${info.name} (${info.currency})`;
      if (code === currentDetectedCountry) opt.selected = true;
      countrySelect.appendChild(opt);
    }

    // Render city examples for the detected country!
    renderMajorCities(currentDetectedCountry);

    // Update city examples & store search whenever country selection changes
    countrySelect.addEventListener('change', () => {
      const newCountry = countrySelect.value;
      renderMajorCities(newCountry);
      const cData = COUNTRY_CITIES[newCountry] || COUNTRY_CITIES['RO'];
      setLocation(cData.defaultCity, cData.defaultLat, cData.defaultLon);
    });
  } catch (err) {
    console.error("Failed to load countries:", err);
  }
}

// Geolocation & Approximate Location Handler
const openLocationModalBtn = document.getElementById('openLocationModalBtn');
const currentLocationLabel = document.getElementById('currentLocationLabel');
const locationModal = document.getElementById('locationModal');
const closeLocationModalBtn = document.getElementById('closeLocationModalBtn');
const autoDetectLocationBtn = document.getElementById('autoDetectLocationBtn');
const locationModalNotice = document.getElementById('locationModalNotice');
const locationModalNoticeText = document.getElementById('locationModalNoticeText');
const customCityForm = document.getElementById('customCityForm');
const customCityInput = document.getElementById('customCityInput');
const skipLocationBtn = document.getElementById('skipLocationBtn');

function resetLocationButtons() {
  if (autoDetectLocationBtn) {
    autoDetectLocationBtn.innerHTML = `
      <i data-lucide="crosshair" class="w-4 h-4 font-bold"></i>
      <span>Allow Approximate Location Access</span>
    `;
  }
  safeRenderIcons();
}

function setupGeolocation() {
  // Load saved location from localStorage
  const savedName = localStorage.getItem('storestock_loc_name');
  const savedLat = localStorage.getItem('storestock_loc_lat');
  const savedLon = localStorage.getItem('storestock_loc_lon');
  const savedCountry = localStorage.getItem('storestock_loc_country');
  const isExplicitlySet = localStorage.getItem('storestock_loc_set');

  // Check if VPN country has changed from previously saved country
  const countryHasChanged = savedCountry && savedCountry !== currentDetectedCountry;

  if (currentDetectedCityInfo && (!isExplicitlySet || countryHasChanged)) {
    // Automatically set location to detected VPN city (e.g. Sydney, Melbourne)
    const cData = COUNTRY_CITIES[currentDetectedCountry] || COUNTRY_CITIES['RO'];
    const cityName = currentDetectedCityInfo.city || cData.defaultCity;
    const lat = currentDetectedCityInfo.lat || cData.defaultLat;
    const lon = currentDetectedCityInfo.lon || cData.defaultLon;
    setLocation(cityName, lat, lon);
  } else if (savedName && savedLat && savedLon && !countryHasChanged) {
    userCoords = { lat: parseFloat(savedLat), lon: parseFloat(savedLon) };
    if (currentLocationLabel) currentLocationLabel.textContent = savedName;
  } else {
    // Dynamic default coordinates based on detected country
    const cData = COUNTRY_CITIES[currentDetectedCountry] || COUNTRY_CITIES['RO'];
    userCoords = { lat: cData.defaultLat, lon: cData.defaultLon };
    if (currentLocationLabel) currentLocationLabel.textContent = cData.defaultCity;
  }

  // Render major cities for current country
  renderMajorCities(currentDetectedCountry);

  // If user hasn't explicitly configured location or country changed, actively open the modal!
  if (!isExplicitlySet || countryHasChanged) {
    if (locationModal) locationModal.classList.remove('hidden');
  }

  // Open modal from header button
  if (openLocationModalBtn) {
    openLocationModalBtn.onclick = () => {
      const activeCode = countrySelect ? countrySelect.value : currentDetectedCountry;
      renderMajorCities(activeCode);
      if (locationModalNotice) locationModalNotice.classList.add('hidden');
      if (locationModal) locationModal.classList.remove('hidden');
    };
  }

  // Close modal button (X)
  if (closeLocationModalBtn) {
    closeLocationModalBtn.onclick = () => {
      if (locationModal) locationModal.classList.add('hidden');
    };
  }

  // Request Approximate Browser Location button inside modal
  if (autoDetectLocationBtn) {
    autoDetectLocationBtn.onclick = () => {
      autoDetectLocationBtn.innerHTML = `
        <span class="inline-block w-4 h-4 rounded-full border-2 border-slate-950 border-t-transparent animate-spin mr-2"></span>
        <span>Detecting current location...</span>
      `;

      // Clear stale cached coordinates from previous VPN sessions
      localStorage.removeItem('storestock_loc_name');
      localStorage.removeItem('storestock_loc_lat');
      localStorage.removeItem('storestock_loc_lon');
      localStorage.removeItem('storestock_loc_set');

      // Function to apply IP-detected location if browser geolocation fails or is denied
      const fallbackToIpLocation = async () => {
        const ipLoc = await detectVisitorLocation();
        if (ipLoc && ipLoc.city) {
          if (countrySelect && ipLoc.countryCode) {
            countrySelect.value = ipLoc.countryCode;
            currentDetectedCountry = ipLoc.countryCode;
            renderMajorCities(ipLoc.countryCode);
          }
          setLocation(ipLoc.city, ipLoc.lat, ipLoc.lon);
          if (locationModal) locationModal.classList.add('hidden');
          resetLocationButtons();
          showToast(`📍 Detected area: ${ipLoc.city} (${ipLoc.countryName || ipLoc.countryCode}).`);
          return true;
        }
        return false;
      };

      if (!navigator.geolocation) {
        fallbackToIpLocation().then(ok => {
          if (!ok) showToast("Geolocation is not supported by your browser", 'warning');
        });
        return;
      }

      // Request fresh live location (maximumAge: 0 ensures NO stale VPN cache is returned by browser)
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          resetLocationButtons();
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          
          let locName = "Approximate Location";
          let detectedCountryCode = null;
          try {
            const revRes = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&addressdetails=1`);
            const revData = await revRes.json();
            locName = revData.address.city || revData.address.town || revData.address.municipality || revData.address.county || revData.address.state || "Your Area";
            if (revData.address && revData.address.country_code) {
              detectedCountryCode = revData.address.country_code.toUpperCase();
            }
          } catch (e) {
            locName = "Your Area";
          }

          // Sync country dropdown and city examples with the real physical country!
          if (detectedCountryCode && COUNTRY_CITIES[detectedCountryCode]) {
            currentDetectedCountry = detectedCountryCode;
            if (countrySelect) countrySelect.value = detectedCountryCode;
            renderMajorCities(detectedCountryCode);
          }

          setLocation(locName, lat, lon);
          if (locationModal) locationModal.classList.add('hidden');
        },
        async (err) => {
          console.warn("Browser GPS permission error, falling back to IP:", err.message);
          const ok = await fallbackToIpLocation();
          if (!ok) {
            resetLocationButtons();
            if (locationModalNotice) {
              locationModalNotice.classList.remove('hidden');
              if (locationModalNoticeText) {
                locationModalNoticeText.textContent = "Location permission was not granted. Please enter your city below or select from the examples:";
              }
            }
            if (customCityInput) customCityInput.focus();
          }
        },
        { enableHighAccuracy: true, timeout: 7000, maximumAge: 0 }
      );
    };
  }

  // Custom city search form
  if (customCityForm) {
    customCityForm.onsubmit = async (e) => {
      e.preventDefault();
      const val = customCityInput.value.trim();
      if (!val) return;

      const normVal = val.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

      // 1. FAST LOCAL MATCH: Search active country's cities first
      const activeCode = (countrySelect ? countrySelect.value : currentDetectedCountry || 'RO').toUpperCase();
      const activeCountryData = COUNTRY_CITIES[activeCode];
      if (activeCountryData && activeCountryData.cities) {
        const match = activeCountryData.cities.find(c => {
          const norm = c.name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
          return norm === normVal || norm.startsWith(normVal) || normVal.startsWith(norm);
        });
        if (match) {
          setLocation(match.name, match.lat, match.lon);
          if (locationModal) locationModal.classList.add('hidden');
          showToast(`📍 Location set to ${match.name}`);
          return;
        }
      }

      // 2. GLOBAL LOCAL MATCH: Search across ALL 49 countries in our registry
      for (const [code, cData] of Object.entries(COUNTRY_CITIES)) {
        if (!cData.cities) continue;
        const match = cData.cities.find(c => {
          const norm = c.name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
          return norm === normVal || norm.startsWith(normVal) || normVal.startsWith(norm);
        });
        if (match) {
          if (countrySelect && countrySelect.value !== code) {
            countrySelect.value = code;
            currentDetectedCountry = code;
            renderMajorCities(code);
          }
          setLocation(match.name, match.lat, match.lon);
          if (locationModal) locationModal.classList.add('hidden');
          showToast(`📍 Location set to ${match.name} (${cData.country})`);
          return;
        }
      }

      // 3. NOMINATIM OPENSTREETMAP LOOKUP (Fallback for smaller towns & districts)
      try {
        let res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(val)}&countrycodes=${activeCode.toLowerCase()}&limit=1`);
        let data = await res.json();

        // If not found in active country, search worldwide without country boundary
        if (!data || data.length === 0) {
          res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(val)}&limit=1&addressdetails=1`);
          data = await res.json();
        }

        if (data && data.length > 0) {
          const lat = parseFloat(data[0].lat);
          const lon = parseFloat(data[0].lon);
          const displayName = (data[0].name || data[0].display_name.split(',')[0]).trim();
          
          const osmCountry = (data[0].address && data[0].address.country_code ? data[0].address.country_code.toUpperCase() : null);
          if (osmCountry && countrySelect && COUNTRY_CITIES[osmCountry]) {
            countrySelect.value = osmCountry;
            currentDetectedCountry = osmCountry;
            renderMajorCities(osmCountry);
          }

          setLocation(displayName, lat, lon);
          if (locationModal) locationModal.classList.add('hidden');
          showToast(`📍 Location set to ${displayName}`);
        } else {
          showToast(`Could not find "${val}". Please try another name or pick from the examples below.`, 'warning');
        }
      } catch (err) {
        showToast("Error searching city. Please pick from the list below.", 'error');
      }
    };
  }
}

function setLocation(name, lat, lon) {
  userCoords = { lat, lon };
  if (currentLocationLabel) currentLocationLabel.textContent = name;
  const activeCountry = countrySelect ? countrySelect.value : currentDetectedCountry;
  localStorage.setItem('storestock_loc_name', name);
  localStorage.setItem('storestock_loc_lat', lat);
  localStorage.setItem('storestock_loc_lon', lon);
  localStorage.setItem('storestock_loc_country', activeCountry);
  localStorage.setItem('storestock_loc_set', 'true');

  if (locationModal) locationModal.classList.add('hidden');
  showToast(`📍 Location set to ${name} (${activeCountry}). Distances recalculated.`);

  if (map) {
    map.setView([lat, lon], 12);
  }

  // Re-search to recompute distances with new coords and country!
  const query = searchInput ? (searchInput.value || '') : '';
  if (query.trim()) {
    executeSearch(query.trim());
  }
}

// AI Intent Banner Elements
const aiIntentBanner = document.getElementById('aiIntentBanner');
const aiCanonicalName = document.getElementById('aiCanonicalName');
const aiDescription = document.getElementById('aiDescription');
const aiSynonyms = document.getElementById('aiSynonyms');

function renderAiIntent(intent) {
  if (!intent || !intent.canonical_name) {
    if (aiIntentBanner) aiIntentBanner.classList.add('hidden');
    return;
  }
  if (!aiIntentBanner) return;
  aiIntentBanner.classList.remove('hidden');
  if (aiCanonicalName) aiCanonicalName.textContent = intent.canonical_name;
  if (aiDescription) {
    aiDescription.textContent = intent.description 
      ? `${intent.description} • Demoting full desktop towers & server racks to find the standalone card.` 
      : "Filtered out full desktop towers and server racks. Prioritizing standalone GPU cards.";
  }

  if (aiSynonyms && intent.synonyms && intent.synonyms.length > 1) {
    aiSynonyms.innerHTML = '';
    aiSynonyms.classList.remove('hidden');
    intent.synonyms.slice(0, 3).forEach(syn => {
      if (syn.toLowerCase() === searchInput.value.toLowerCase().trim()) return;
      const btn = document.createElement('button');
      btn.className = "px-2 py-0.5 rounded-md bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-[10px] font-semibold transition";
      btn.textContent = `Try: ${syn}`;
      btn.onclick = () => {
        searchInput.value = syn;
        executeSearch(syn);
      };
      aiSynonyms.appendChild(btn);
    });
  } else if (aiSynonyms) {
    aiSynonyms.classList.add('hidden');
  }

  if (window.lucide) safeRenderIcons();
}

function renderInitialWelcomeState() {
  if (!resultsGrid) return;
  resultsGrid.innerHTML = `
    <div class="col-span-full flex flex-col items-center justify-center py-24 px-4 text-center space-y-4">
      <div class="h-16 w-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-emerald-400 shadow-xl shadow-emerald-500/10">
        <i data-lucide="search" class="w-8 h-8"></i>
      </div>
      <div class="space-y-1.5">
        <h3 class="text-lg font-bold text-slate-200">Search Across Stores Worldwide</h3>
        <p class="text-xs text-slate-400 max-w-md mx-auto">
          Type any product name, hardware, groceries, or vehicle above to check live stock, physical shelf availability, and prices in real-time.
        </p>
      </div>
    </div>
  `;
  safeRenderIcons();
}

// Live Streaming Search via SSE
function executeSearch(query) {
  if (!query || !query.trim()) {
    renderInitialWelcomeState();
    if (statsBar) statsBar.classList.add('hidden');
    const pCont = document.getElementById('storesProgressContainer');
    if (pCont) pCont.classList.add('hidden');
    return;
  }

  const pCont = document.getElementById('storesProgressContainer');
  if (pCont) pCont.classList.remove('hidden');

  const country = countrySelect.value || 'RO';
  currentResults = [];
  activeBrand = null;
  if (aiIntentBanner) aiIntentBanner.classList.add('hidden');
  resultsGrid.innerHTML = '';
  storesProgress.innerHTML = '';
  emptyState.classList.add('hidden');
  statsBar.classList.remove('hidden');
  safeRenderIcons();
  loadingIndicator.classList.remove('hidden');

  inStockStat.textContent = 'Checking stock...';
  totalFoundStat.textContent = 'Searching stores...';
  latencyStat.textContent = '...';

  const startTime = performance.now();
  let url = `/api/stream?q=${encodeURIComponent(query.trim())}&country=${country}`;
  if (userCoords) {
    url += `&lat=${userCoords.lat}&lon=${userCoords.lon}`;
  }

  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'ai_intent') {
        renderAiIntent(data.payload);
      } else if (data.type === 'provider_result') {
        const p = data.payload;
        renderStorePill(p.store_name, p.items.length, p.elapsed_ms);

        if (p.items && p.items.length > 0) {
          currentResults.push(...p.items);
          renderResults();
          renderBrandChips();
          updateMapMarkers();
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
    eventSource.close();
    loadingIndicator.classList.add('hidden');
    updateStats();
    if (currentResults.length === 0) {
      emptyState.classList.remove('hidden');
    }
  };
}

function renderStorePill(storeName, count, elapsedMs) {
  const pill = document.createElement('button');
  pill.type = 'button';
  pill.setAttribute('data-store', storeName);
  pill.setAttribute('data-count', count);
  pill.title = count > 0 ? `Click to filter by ${storeName} only` : `0 results found in ${storeName}`;

  const isSelected = activeBrand === storeName;
  let baseClass = "store-pill flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold border shadow-sm transition-all duration-150 cursor-pointer hover:scale-105 active:scale-95 select-none ";
  
  if (isSelected) {
    baseClass += "bg-emerald-500/20 border-emerald-400 text-white ring-2 ring-emerald-500/30 scale-105";
  } else if (activeBrand && activeBrand !== storeName) {
    baseClass += "bg-slate-900/60 border-slate-800 text-slate-500 opacity-60 hover:opacity-100 hover:border-slate-600";
  } else {
    baseClass += "bg-slate-800/90 border-slate-700 text-slate-300 hover:border-slate-500";
  }

  pill.className = baseClass;
  pill.innerHTML = `
    <span class="w-2 h-2 rounded-full ${count > 0 ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400/80'}"></span>
    <span>${storeName}:</span>
    <span class="text-white font-bold">${count} found</span>
    <span class="text-slate-500 text-[10px]">(${elapsedMs}ms)</span>
  `;

  pill.onclick = () => {
    if (activeBrand === storeName) {
      activeBrand = null; // Toggle off filter
      showToast(`Showing all stores`);
    } else {
      activeBrand = storeName;
      showToast(`Filtered by ${storeName} (${count} found)`);
    }
    updateStorePillsUI();
    renderResults();
    renderBrandChips();
    updateMapMarkers();
  };

  storesProgress.appendChild(pill);
}

function updateStorePillsUI() {
  const pills = document.querySelectorAll('.store-pill');
  pills.forEach(pill => {
    const sName = pill.getAttribute('data-store');
    const isSelected = activeBrand === sName;
    
    let baseClass = "store-pill flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold border shadow-sm transition-all duration-150 cursor-pointer hover:scale-105 active:scale-95 select-none ";
    if (isSelected) {
      baseClass += "bg-emerald-500/20 border-emerald-400 text-white ring-2 ring-emerald-500/30 scale-105 shadow-md shadow-emerald-500/20";
    } else if (activeBrand && activeBrand !== sName) {
      baseClass += "bg-slate-900/60 border-slate-800 text-slate-500 opacity-50 hover:opacity-100 hover:border-slate-600";
    } else {
      baseClass += "bg-slate-800/90 border-slate-700 text-slate-300 hover:border-slate-500";
    }
    pill.className = baseClass;
  });
}

function updateStats() {
  const inStockCount = currentResults.filter(r => r.in_stock).length;
  inStockStat.textContent = `${inStockCount} In Stock`;
  totalFoundStat.textContent = `${currentResults.length} Total Found`;
}

function renderBrandChips() {
  const stores = [...new Set(currentResults.map(r => r.store_name))];
  if (stores.length <= 1) {
    brandFilterContainer.classList.add('hidden');
    return;
  }
  brandFilterContainer.classList.remove('hidden');
  brandChips.innerHTML = '';

  const allChip = document.createElement('button');
  allChip.className = `px-2.5 py-0.5 rounded-lg border text-xs font-semibold transition ${!activeBrand ? 'bg-emerald-500 text-slate-950 border-emerald-400 font-bold' : 'bg-slate-800 text-slate-300 border-slate-700'}`;
  allChip.textContent = 'All Stores';
  allChip.onclick = () => { 
    activeBrand = null; 
    renderBrandChips(); 
    updateStorePillsUI();
    renderResults(); 
    updateMapMarkers(); 
  };
  brandChips.appendChild(allChip);

  stores.forEach(store => {
    const chip = document.createElement('button');
    const isSelected = activeBrand === store;
    chip.className = `px-2.5 py-0.5 rounded-lg border text-xs font-semibold transition ${isSelected ? 'bg-emerald-500 text-slate-950 border-emerald-400 font-bold' : 'bg-slate-800 text-slate-300 border-slate-700 hover:border-slate-500'}`;
    chip.textContent = store;
    chip.onclick = () => {
      activeBrand = isSelected ? null : store;
      renderBrandChips();
      updateStorePillsUI();
      renderResults();
      updateMapMarkers();
    };
    brandChips.appendChild(chip);
  });
}

function renderResults() {
  updateStats();

  const currentQuery = (searchInput ? searchInput.value : "") || "";
  const currentQueryLower = currentQuery.toLowerCase();

  let filtered = [...currentResults];
  if (activeFilter === 'in_stock') {
    filtered = filtered.filter(r => r.in_stock);
  } else if (activeFilter === 'nearby') {
    filtered = filtered.filter(r => r.store_branch);
  }

  if (activeBrand) {
    filtered = filtered.filter(r => r.store_name === activeBrand);
  }

  // Sort
  if (activeSort === 'price_asc') {
    filtered.sort((a, b) => (a.price > 0 ? a.price : 9999999) - (b.price > 0 ? b.price : 9999999));
  } else if (activeSort === 'price_desc') {
    filtered.sort((a, b) => b.price - a.price);
  } else if (activeSort === 'distance_asc') {
    filtered.sort((a, b) => (a.distance_km || 9999) - (b.distance_km || 9999));
  } else {
    filtered.sort((a, b) => scoreRelevance(currentQuery, b.title, b.price, b.in_stock) - scoreRelevance(currentQuery, a.title, a.price, a.in_stock));
  }

  resultsGrid.innerHTML = '';

  if (filtered.length === 0) {
    emptyState.classList.remove('hidden');
    return;
  } else {
    emptyState.classList.add('hidden');
  }

  // Stock Reality Check: If user searched for A6000 or high-end workstation GPU, verify if any standalone card actually exists in stock
  const isWorkstationGpuQuery = currentQueryLower.includes("a6000") || currentQueryLower.includes("rtx 6000");
  const hasDiscreteCard = filtered.some(r => {
    const t = r.title.toLowerCase();
    const isDiscrete = HARDWARE_WORDS.some(h => t.includes(h)) || t.includes("rtx a6000") || t.includes("rtx 6000");
    const isAcc = ACCESSORY_WORDS.some(acc => t.includes(acc));
    const isPrebuilt = ["desktop pc", "server", "superworkstation", "tower", "laptop"].some(p => t.includes(p));
    return isDiscrete && !isAcc && !isPrebuilt;
  });

  if (isWorkstationGpuQuery && !hasDiscreteCard) {
    const stockAlertNotice = document.createElement('div');
    stockAlertNotice.className = "col-span-full p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs mb-2 shadow-lg";
    stockAlertNotice.innerHTML = `
      <div class="flex items-center space-x-3">
        <div class="h-9 w-9 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0 border border-amber-500/30">
          <i data-lucide="alert-triangle" class="w-5 h-5 text-amber-400"></i>
        </div>
        <div>
          <div class="font-bold text-white text-sm">Standalone NVIDIA RTX A6000 / RTX 6000 is Currently Out of Stock Across Retailers</div>
          <p class="text-slate-300 text-[11px] mt-0.5">
            The standalone 48GB GPU is an enterprise B2B card not currently in stock at consumer retailers (eMAG, Altex, PC Garage). Search engines returned related accessories (NVLink bridges, power cables) or 200,000+ RON server racks.
          </p>
        </div>
      </div>
      <button onclick="openAlertModal('NVIDIA RTX A6000', 'All Stores')" class="shrink-0 flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold transition shadow-md shadow-amber-500/20">
        <i data-lucide="bell" class="w-4 h-4"></i>
        <span>Track Restock</span>
      </button>
    `;
    resultsGrid.appendChild(stockAlertNotice);
  }

  filtered.forEach(item => {
    const card = document.createElement('div');
    card.className = "glass-card rounded-2xl p-4 flex flex-col justify-between hover:border-slate-600 transition duration-200 group";

    let badgeClass = "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    let statusIcon = "check-circle";
    let cleanStockText = "In Stock";
    if (!item.in_stock) {
      badgeClass = "bg-rose-500/10 text-rose-400 border border-rose-500/20";
      statusIcon = "x-circle";
      cleanStockText = "Out of Stock";
    } else if (item.stock_level === "LOW_STOCK") {
      badgeClass = "bg-amber-500/10 text-amber-400 border border-amber-500/20";
      statusIcon = "alert-triangle";
      cleanStockText = "Low Stock";
    }

    let formattedPrice = `${item.price.toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${item.currency}`;
    if (item.price === 0) formattedPrice = "Check Store";

    const imgUrl = item.image_url || 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=300&auto=format&fit=crop&q=60';

    // Store Branch & Distance Info
    let branchBadge = '';
    if (item.store_branch) {
      const dist = item.distance_km ? `• <span class="text-emerald-400 font-bold">${item.distance_km} km</span>` : '';
      branchBadge = `
        <div class="flex items-center space-x-1 text-[11px] text-slate-400 pt-1">
          <i data-lucide="map-pin" class="w-3 h-3 text-emerald-400 shrink-0"></i>
          <span class="truncate" title="${item.store_address || ''}">${item.store_branch} ${dist}</span>
        </div>
      `;
    }

    // Vehicle specifications pill (for cars / automotive)
    let carSpecsBadge = '';
    if (item.category === 'automotive' || item.year || item.mileage_km) {
      const specs = [];
      if (item.year) specs.push(`📅 ${item.year}`);
      if (item.mileage_km) specs.push(`🛣️ ${item.mileage_km.toLocaleString()} km`);
      if (item.fuel_type) specs.push(`⛽ ${item.fuel_type}`);
      if (item.transmission) specs.push(`⚙️ ${item.transmission}`);
      if (specs.length > 0) {
        carSpecsBadge = `
          <div class="flex flex-wrap gap-1 text-[10px] pt-1.5">
            ${specs.map(s => `<span class="px-1.5 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30 font-medium">${s}</span>`).join('')}
          </div>
        `;
      }
    }

    // Alert CTA if out of stock
    let alertActionBtn = '';
    if (!item.in_stock) {
      alertActionBtn = `
        <button 
          class="alert-me-btn flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 transition mt-2"
          data-title="${item.title.replace(/"/g, '&quot;')}"
          data-store="${item.store_name}"
          data-url="${item.product_url}"
        >
          <i data-lucide="bell" class="w-3 h-3"></i>
          <span>Alert Me</span>
        </button>
      `;
    }

    card.innerHTML = `
      <div class="space-y-2.5">
        <div class="flex items-center justify-between gap-2">
          <span class="px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-800 text-slate-200 border border-slate-700/80 truncate max-w-[130px]" title="${item.store_name}">
            ${item.store_name}
          </span>
          <span class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold tracking-wide whitespace-nowrap shrink-0 ${badgeClass}" title="${item.stock_badge_text || cleanStockText}">
            <i data-lucide="${statusIcon}" class="w-3.5 h-3.5 shrink-0"></i>
            <span>${cleanStockText}</span>
          </span>
        </div>

        <div class="relative w-full h-40 rounded-xl bg-slate-900/80 overflow-hidden flex items-center justify-center p-2 group-hover:scale-[1.02] transition">
          <img src="${imgUrl}" alt="${item.title}" class="max-h-full max-w-full object-contain" loading="lazy" onerror="this.onerror=null;this.src='data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'100\' height=\'100\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'%23475569\' stroke-width=\'1.5\'><rect width=\'18\' height=\'18\' x=\'3\' y=\'3\' rx=\'2\'/><circle cx=\'9\' cy=\'9\' r=\'2\'/><path d=\'m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21\'/></svg>'"/>
        </div>

        <h3 class="text-xs sm:text-sm font-semibold text-slate-100 line-clamp-2" title="${item.title}">
          ${item.title}
        </h3>

        ${carSpecsBadge}
        ${branchBadge}
        ${alertActionBtn}
      </div>

      <div class="pt-3 mt-2 border-t border-slate-800/80 flex items-center justify-between gap-2">
        <div>
          <div class="text-[10px] text-slate-400">Live Price</div>
          <div class="text-base sm:text-lg font-extrabold text-emerald-400 font-mono">
            ${formattedPrice}
          </div>
        </div>

        <a 
          href="${item.product_url}" 
          target="_blank" 
          rel="noopener noreferrer" 
          class="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-emerald-500 hover:text-slate-950 text-slate-200 border border-slate-700 hover:border-emerald-400 transition shadow-sm"
        >
          <span>View</span>
          <i data-lucide="external-link" class="w-3 h-3"></i>
        </a>
      </div>
    `;

    resultsGrid.appendChild(card);
  });

  // Attach Alert Me listeners
  document.querySelectorAll('.alert-me-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const title = btn.getAttribute('data-title');
      const store = btn.getAttribute('data-store');
      const url = btn.getAttribute('data-url');
      openAlertModal(title, store, url);
    });
  });

  safeRenderIcons();
}

// Leaflet Map Logic (100% Free OpenStreetMap - Zero API Key Required)
function initMap() {
  if (map) return;
  const initialCenter = userCoords ? [userCoords.lat, userCoords.lon] : [44.4323, 26.1063];
  map = L.map('mapContainer').setView(initialCenter, 12);
  
  // Official standard OpenStreetMap tile layer (Free, no API key needed)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);
}

function safeRenderIcons() {
  try {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  } catch (e) {
    console.warn("Lucide render error:", e);
  }
}

function updateMapMarkers() {
  if (!map) return;
  mapMarkers.forEach(m => map.removeLayer(m));
  mapMarkers = [];

  const bounds = [];

  // Add User's Location Marker (Blue Pulse)
  if (userCoords) {
    const userIcon = L.divIcon({
      className: 'user-pin',
      html: `
        <div style="background-color: #38bdf8; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 14px #38bdf8;"></div>
      `,
      iconSize: [16, 16],
      iconAnchor: [8, 8]
    });
    const locName = localStorage.getItem('storestock_loc_name') || 'Your Location';
    const userMarker = L.marker([userCoords.lat, userCoords.lon], { icon: userIcon }).addTo(map);
    userMarker.bindPopup(`<div style="font-weight: bold; color: #38bdf8; font-size: 12px;">📍 ${locName} (Your Location)</div>`);
    mapMarkers.push(userMarker);
    bounds.push([userCoords.lat, userCoords.lon]);
  }

  const itemsWithCoords = currentResults.filter(r => r.latitude && r.longitude);
  if (itemsWithCoords.length === 0) {
    if (bounds.length > 0) {
      map.fitBounds(bounds, { maxZoom: 13 });
    }
    return;
  }

  itemsWithCoords.forEach(item => {
    const isAvailable = item.in_stock;
    const pinColor = isAvailable ? '#22c55e' : '#f43f5e';

    const customIcon = L.divIcon({
      className: 'custom-pin',
      html: `
        <div style="background-color: ${pinColor}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 10px ${pinColor};"></div>
      `,
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    });

    const marker = L.marker([item.latitude, item.longitude], { icon: customIcon }).addTo(map);
    const popupContent = `
      <div style="min-width: 180px; font-family: sans-serif;">
        <div style="font-weight: bold; color: ${pinColor}; font-size: 11px; text-transform: uppercase;">
          ${item.stock_badge_text}
        </div>
        <div style="font-size: 13px; font-weight: bold; margin-top: 2px; color: #f8fafc;">
          ${item.store_branch || item.store_name}
        </div>
        <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
          ${item.store_address || ''}
        </div>
        <div style="font-size: 12px; font-weight: bold; color: #34d399; margin-top: 4px;">
          ${item.price > 0 ? item.price + ' ' + item.currency : ''}
        </div>
        <div style="font-size: 11px; color: #cbd5e1; margin-top: 4px; line-height: 1.2;">
          ${item.title.substring(0, 50)}...
        </div>
        <a href="${item.product_url}" target="_blank" style="display: inline-block; margin-top: 8px; padding: 4px 8px; background: #22c55e; color: #020617; border-radius: 6px; font-size: 11px; font-weight: bold; text-decoration: none;">
          View / Reserve
        </a>
      </div>
    `;
    marker.bindPopup(popupContent);
    mapMarkers.push(marker);
    bounds.push([item.latitude, item.longitude]);
  });

  if (bounds.length > 0) {
    map.fitBounds(bounds, { padding: [30, 30] });
  }
}

// Restock Alerts API & UI
async function loadAlerts() {
  try {
    const res = await fetch('/api/alerts');
    const alerts = await res.json();
    alertsList.innerHTML = '';

    if (alerts.length > 0) {
      alertsCountBadge.textContent = alerts.length;
      alertsCountBadge.classList.remove('hidden');
    } else {
      alertsCountBadge.classList.add('hidden');
    }

    if (alerts.length === 0) {
      alertsList.innerHTML = `
        <div class="text-center py-12 text-slate-500">
          <i data-lucide="bell-off" class="w-8 h-8 mx-auto mb-2 opacity-50"></i>
          <p class="text-sm font-semibold">No active restock alerts</p>
          <p class="text-xs">Click "Alert Me" on any out-of-stock product card or track a new keyword.</p>
        </div>
      `;
      if (window.lucide) lucide.createIcons();
      return;
    }

    alerts.forEach(alert => {
      const row = document.createElement('div');
      row.className = "glass-card rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border border-slate-800";
      
      const isTrig = alert.is_triggered;
      const statusBadge = isTrig 
        ? `<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse">🔥 RESTOCKED!</span>`
        : `<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">👀 Monitoring</span>`;

      row.innerHTML = `
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            ${statusBadge}
            <span class="text-xs font-bold text-slate-300">[${alert.store_name}]</span>
            <span class="text-xs text-slate-500">Created: ${alert.created_at}</span>
          </div>
          <h4 class="text-sm font-semibold text-white">${alert.product_title || alert.query}</h4>
          <div class="text-xs text-slate-400">Target Ceiling: ${alert.target_price ? alert.target_price + ' RON' : 'Any Price'} • Notifying: ${alert.email}</div>
        </div>

        <div class="flex items-center space-x-2 shrink-0">
          ${alert.product_url ? `<a href="${alert.product_url}" target="_blank" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition">View Store</a>` : ''}
          <button class="delete-alert-btn p-2 rounded-lg text-rose-400 hover:bg-rose-500/10 border border-rose-500/20 transition" data-id="${alert.id}">
            <i data-lucide="trash-2" class="w-4 h-4"></i>
          </button>
        </div>
      `;
      alertsList.appendChild(row);
    });

    document.querySelectorAll('.delete-alert-btn').forEach(b => {
      b.onclick = async () => {
        const id = b.getAttribute('data-id');
        await fetch(`/api/alerts/${id}`, { method: 'DELETE' });
        showToast("Alert removed");
        loadAlerts();
      };
    });

    safeRenderIcons();
  } catch (err) {
    console.error("Failed to load alerts:", err);
  }
}

function openAlertModal(title, store, url) {
  alertQueryInput.value = title || searchInput.value || '';
  alertStoreInput.value = store || '';
  alertProductUrl.value = url || '';
  alertModal.classList.remove('hidden');
}

function closeAlertModal() {
  alertModal.classList.add('hidden');
}

createAlertForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    query: alertQueryInput.value,
    store_name: alertStoreInput.value || "All Stores",
    target_price: alertPriceInput.value ? parseFloat(alertPriceInput.value) : null,
    email: alertEmailInput.value,
    product_title: alertQueryInput.value,
    product_url: alertProductUrl.value
  };

  try {
    const res = await fetch('/api/alerts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      closeAlertModal();
      showToast("Restock alert registered! We'll track it in the background.");
      loadAlerts();
    }
  } catch (err) {
    console.error("Failed to save alert:", err);
  }
});

function showToast(msg, type = 'success') {
  if (!toast || !toastMsg) return;
  toastMsg.textContent = msg;
  const icon = toast.querySelector('i');
  if (type === 'error') {
    toast.className = "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-rose-600 text-white font-bold shadow-2xl flex items-center space-x-2 text-xs transition duration-300";
    if (icon) icon.setAttribute('data-lucide', 'alert-circle');
  } else if (type === 'warning') {
    toast.className = "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-amber-500 text-slate-950 font-bold shadow-2xl flex items-center space-x-2 text-xs transition duration-300";
    if (icon) icon.setAttribute('data-lucide', 'alert-triangle');
  } else {
    toast.className = "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-emerald-500 text-slate-950 font-bold shadow-2xl flex items-center space-x-2 text-xs transition duration-300";
    if (icon) icon.setAttribute('data-lucide', 'check');
  }
  safeRenderIcons();
  toast.classList.remove('hidden');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.add('hidden'), 3500);
}

// View Switching
function switchView(view) {
  currentView = view;
  gridSection.classList.add('hidden');
  mapSection.classList.add('hidden');
  alertsSection.classList.add('hidden');

  viewGridBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition";
  viewMapBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition";
  viewAlertsBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition";

  if (view === 'grid') {
    gridSection.classList.remove('hidden');
    viewGridBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-500 text-slate-950 transition";
  } else if (view === 'map') {
    mapSection.classList.remove('hidden');
    viewMapBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-500 text-slate-950 transition";
    initMap();
    setTimeout(() => {
      map.invalidateSize();
      updateMapMarkers();
    }, 100);
  } else if (view === 'alerts') {
    alertsSection.classList.remove('hidden');
    viewAlertsBtn.className = "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-500 text-slate-950 transition";
    loadAlerts();
  }
  safeRenderIcons();
}

viewGridBtn.onclick = () => switchView('grid');
viewMapBtn.onclick = () => switchView('map');
viewAlertsBtn.onclick = () => switchView('alerts');
openNewAlertModalBtn.onclick = () => openAlertModal();
closeAlertModalBtn.onclick = closeAlertModal;
cancelAlertModalBtn.onclick = closeAlertModal;

// Search Form submit
searchForm.addEventListener('submit', (e) => {
  e.preventDefault();
  if (currentView === 'alerts') switchView('grid');
  executeSearch(searchInput.value);
});

// Filters
filterAllBtn.addEventListener('click', () => {
  activeFilter = 'all';
  updateFilterButtons();
  renderResults();
});

filterInStockBtn.addEventListener('click', () => {
  activeFilter = 'in_stock';
  updateFilterButtons();
  renderResults();
});

filterNearbyBtn.addEventListener('click', () => {
  activeFilter = 'nearby';
  updateFilterButtons();
  renderResults();
});

function updateFilterButtons() {
  [filterAllBtn, filterInStockBtn, filterNearbyBtn].forEach(b => {
    b.className = "filter-btn px-3 py-1.5 rounded-lg text-slate-400 hover:text-slate-200 font-medium transition text-xs";
  });
  if (activeFilter === 'all') filterAllBtn.className = "filter-btn active px-3 py-1.5 rounded-lg bg-emerald-500 text-slate-950 font-bold transition shadow-sm text-xs";
  if (activeFilter === 'in_stock') filterInStockBtn.className = "filter-btn active px-3 py-1.5 rounded-lg bg-emerald-500 text-slate-950 font-bold transition shadow-sm text-xs";
  if (activeFilter === 'nearby') filterNearbyBtn.className = "filter-btn active px-3 py-1.5 rounded-lg bg-emerald-500 text-slate-950 font-bold transition shadow-sm text-xs";
}

sortSelect.addEventListener('change', () => {
  activeSort = sortSelect.value;
  renderResults();
});

// Robust Initialization
async function initApp() {
  try {
    await loadCountries();
    setupGeolocation();
    loadAlerts();
    if (searchInput) {
      searchInput.value = '';
    }
    renderInitialWelcomeState();
    safeRenderIcons();
  } catch (err) {
    console.error("Initialization error:", err);
  }
}

// Global error banner in case of any unhandled issue
window.addEventListener('error', (e) => {
  console.error("StoreStock Global JS Error:", e);
  const banner = document.getElementById('jsErrorBanner');
  if (banner) {
    banner.textContent = `JS Error: ${e.message} (${e.filename}:${e.lineno})`;
    banner.classList.remove('hidden');
  }
});

// Check if DOM is already parsed (since script is at bottom of body)
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  // DOM already loaded, run immediately!
  initApp();
}

// Fallback to re-render Lucide icons if CDN script arrived after execution
window.addEventListener('load', () => {
  safeRenderIcons();
});
