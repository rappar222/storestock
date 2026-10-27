from typing import Dict, List, Any

# Top 49 Countries Registry for StoreStock
COUNTRIES_REGISTRY: Dict[str, Dict[str, Any]] = {
    "RO": {
        "name": "Romania",
        "flag": "🇷🇴",
        "currency": "RON",
        "locale": "ro_RO",
        "stores": ["eMAG", "Altex", "Media Galaxy", "PC Garage", "Flanco", "Auchan", "evoMAG", "Autovit.ro", "Amazon EU"]
    },
    "US": {
        "name": "United States",
        "flag": "🇺🇸",
        "currency": "USD",
        "locale": "en_US",
        "stores": ["Micro Center", "Best Buy", "Walmart", "Amazon US", "AutoTrader US"]
    },
    "DE": {
        "name": "Germany",
        "flag": "🇩🇪",
        "currency": "EUR",
        "locale": "de_DE",
        "stores": ["Amazon.de", "MediaMarkt", "Saturn", "Mindfactory", "Cyberport", "Wolt", "Flink"]
    },
    "GB": {
        "name": "United Kingdom",
        "flag": "🇬🇧",
        "currency": "GBP",
        "locale": "en_GB",
        "stores": ["Amazon.co.uk", "Currys", "Scan", "Argos", "Deliveroo", "Uber Eats"]
    },
    "FR": {
        "name": "France",
        "flag": "🇫🇷",
        "currency": "EUR",
        "locale": "fr_FR",
        "stores": ["Amazon.fr", "Fnac", "Darty", "LDLC", "Cdiscount", "Deliveroo"]
    },
    "IT": {
        "name": "Italy",
        "flag": "🇮🇹",
        "currency": "EUR",
        "locale": "it_IT",
        "stores": ["Amazon.it", "MediaWorld", "Unieuro", "ePRICE", "Glovo"]
    },
    "ES": {
        "name": "Spain",
        "flag": "🇪🇸",
        "currency": "EUR",
        "locale": "es_ES",
        "stores": ["Amazon.es", "PCComponentes", "MediaMarkt ES", "El Corte Inglés", "Glovo"]
    },
    "PL": {
        "name": "Poland",
        "flag": "🇵🇱",
        "currency": "PLN",
        "locale": "pl_PL",
        "stores": ["Allegro", "x-kom", "Media Expert", "Amazon.pl", "Glovo", "Wolt"]
    },
    "NL": {
        "name": "Netherlands",
        "flag": "🇳🇱",
        "currency": "EUR",
        "locale": "nl_NL",
        "stores": ["Bol.com", "Coolblue", "Megekko", "Amazon.nl", "Uber Eats"]
    },
    "CA": {
        "name": "Canada",
        "flag": "🇨🇦",
        "currency": "CAD",
        "locale": "en_CA",
        "stores": ["Amazon.ca", "Canada Computers", "Best Buy CA", "Memory Express", "DoorDash"]
    },
    "AU": {
        "name": "Australia",
        "flag": "🇦🇺",
        "currency": "AUD",
        "locale": "en_AU",
        "stores": ["Scorptec Computers", "JB Hi-Fi", "Amazon Australia", "CarSales Australia"]
    },
    "JP": {
        "name": "Japan",
        "flag": "🇯🇵",
        "currency": "JPY",
        "locale": "ja_JP",
        "stores": ["Amazon.co.jp", "Yodobashi", "Bic Camera", "Rakuten"]
    },
    "KR": {
        "name": "South Korea",
        "flag": "🇰🇷",
        "currency": "KRW",
        "locale": "ko_KR",
        "stores": ["Coupang", "Danawa", "Compuzone", "Naver Shopping"]
    },
    "IN": {
        "name": "India",
        "flag": "🇮🇳",
        "currency": "INR",
        "locale": "en_IN",
        "stores": ["Amazon.in", "Flipkart", "Croma", "Blinkit", "Zepto"]
    },
    "BR": {
        "name": "Brazil",
        "flag": "🇧🇷",
        "currency": "BRL",
        "locale": "pt_BR",
        "stores": ["Mercado Livre BR", "KaBuM!", "Amazon.com.br", "iFood"]
    },
    "MX": {
        "name": "Mexico",
        "flag": "🇲🇽",
        "currency": "MXN",
        "locale": "es_MX",
        "stores": ["Mercado Libre MX", "Amazon.com.mx", "Cyberpuerta", "Rappi"]
    },
    "SE": {
        "name": "Sweden",
        "flag": "🇸🇪",
        "currency": "SEK",
        "locale": "sv_SE",
        "stores": ["Inet", "Webhallen", "Amazon.se", "Elgiganten", "Wolt"]
    },
    "CH": {
        "name": "Switzerland",
        "flag": "🇨🇭",
        "currency": "CHF",
        "locale": "de_CH",
        "stores": ["Digitec Galaxus", "Brack.ch", "Microspot"]
    },
    "AT": {
        "name": "Austria",
        "flag": "🇦🇹",
        "currency": "EUR",
        "locale": "de_AT",
        "stores": ["Amazon.de", "MediaMarkt AT", "Cyberport AT", "Lieferando"]
    },
    "BE": {
        "name": "Belgium",
        "flag": "🇧🇪",
        "currency": "EUR",
        "locale": "nl_BE",
        "stores": ["Bol.com", "Coolblue BE", "MediaMarkt BE"]
    },
    "NO": {
        "name": "Norway",
        "flag": "🇳🇴",
        "currency": "NOK",
        "locale": "no_NO",
        "stores": ["Komplett.no", "Elkjøp", "NetOnNet", "Wolt"]
    },
    "DK": {
        "name": "Denmark",
        "flag": "🇩🇰",
        "currency": "DKK",
        "locale": "da_DK",
        "stores": ["Proshop.dk", "Elgiganten DK", "Komplett.dk", "Wolt"]
    },
    "FI": {
        "name": "Finland",
        "flag": "🇫🇮",
        "currency": "EUR",
        "locale": "fi_FI",
        "stores": ["Verkkokauppa", "Jimms.fi", "Gigantti", "Wolt"]
    },
    "CZ": {
        "name": "Czech Republic",
        "flag": "🇨🇿",
        "currency": "CZK",
        "locale": "cs_CZ",
        "stores": ["Alza.cz", "CZC.cz", "Datart", "Wolt"]
    },
    "HU": {
        "name": "Hungary",
        "flag": "🇭🇺",
        "currency": "HUF",
        "locale": "hu_HU",
        "stores": ["eMAG.hu", "Alza.hu", "iPon", "Wolt"]
    },
    "GR": {
        "name": "Greece",
        "flag": "🇬🇷",
        "currency": "EUR",
        "locale": "el_GR",
        "stores": ["Skroutz", "Plaisio", "Public.gr", "Wolt"]
    },
    "PT": {
        "name": "Portugal",
        "flag": "🇵🇹",
        "currency": "EUR",
        "locale": "pt_PT",
        "stores": ["Worten", "PCDIGA", "Fnac PT", "Glovo"]
    },
    "IE": {
        "name": "Ireland",
        "flag": "🇮🇪",
        "currency": "EUR",
        "locale": "en_IE",
        "stores": ["Amazon.co.uk (IE)", "Currys IE", "Komplett.ie", "Deliveroo"]
    },
    "NZ": {
        "name": "New Zealand",
        "flag": "🇳🇿",
        "currency": "NZD",
        "locale": "en_NZ",
        "stores": ["PB Tech", "Computer Lounge", "Mighty Ape", "DoorDash"]
    },
    "SG": {
        "name": "Singapore",
        "flag": "🇸🇬",
        "currency": "SGD",
        "locale": "en_SG",
        "stores": ["Shopee SG", "Lazada SG", "Amazon.sg", "GrabFood"]
    },
    "AE": {
        "name": "United Arab Emirates",
        "flag": "🇦🇪",
        "currency": "AED",
        "locale": "en_AE",
        "stores": ["Amazon.ae", "Noon", "Sharaf DG", "Microless", "Talabat"]
    },
    "SA": {
        "name": "Saudi Arabia",
        "flag": "🇸🇦",
        "currency": "SAR",
        "locale": "ar_SA",
        "stores": ["Amazon.sa", "Noon SA", "Jarir Bookstore", "Hungerstation"]
    },
    "IL": {
        "name": "Israel",
        "flag": "🇮🇱",
        "currency": "ILS",
        "locale": "he_IL",
        "stores": ["KSP", "Ivory", "Bug", "Wolt"]
    },
    "TR": {
        "name": "Turkey",
        "flag": "🇹🇷",
        "currency": "TRY",
        "locale": "tr_TR",
        "stores": ["Hepsiburada", "Trendyol", "Amazon.com.tr", "Itopya", "Getir"]
    },
    "ZA": {
        "name": "South Africa",
        "flag": "🇿🇦",
        "currency": "ZAR",
        "locale": "en_ZA",
        "stores": ["Takealot", "Wootware", "Evetech", "Checkers Sixty60"]
    },
    "AR": {
        "name": "Argentina",
        "flag": "🇦🇷",
        "currency": "ARS",
        "locale": "es_AR",
        "stores": ["Mercado Libre AR", "Compragamer", "PedidosYa"]
    },
    "CL": {
        "name": "Chile",
        "flag": "🇨🇱",
        "currency": "CLP",
        "locale": "es_CL",
        "stores": ["Falabella", "PC Factory", "Mercado Libre CL", "PedidosYa"]
    },
    "CO": {
        "name": "Colombia",
        "flag": "🇨🇴",
        "currency": "COP",
        "locale": "es_CO",
        "stores": ["Mercado Libre CO", "Alkosto", "Exito", "Rappi"]
    },
    "ID": {
        "name": "Indonesia",
        "flag": "🇮🇩",
        "currency": "IDR",
        "locale": "id_ID",
        "stores": ["Tokopedia", "Shopee ID", "EnterKomputer", "GoFood"]
    },
    "MY": {
        "name": "Malaysia",
        "flag": "🇲🇾",
        "currency": "MYR",
        "locale": "en_MY",
        "stores": ["Shopee MY", "Lazada MY", "All IT", "GrabFood"]
    },
    "PH": {
        "name": "Philippines",
        "flag": "🇵🇭",
        "currency": "PHP",
        "locale": "en_PH",
        "stores": ["Shopee PH", "Lazada PH", "Dynaquest", "GrabFood"]
    },
    "TH": {
        "name": "Thailand",
        "flag": "🇹🇭",
        "currency": "THB",
        "locale": "th_TH",
        "stores": ["Shopee TH", "Lazada TH", "JIB", "Advice", "Grab"]
    },
    "VN": {
        "name": "Vietnam",
        "flag": "🇻🇳",
        "currency": "VND",
        "locale": "vi_VN",
        "stores": ["Shopee VN", "Tiki", "GearVN", "Phong Vu", "Grab"]
    },
    "UA": {
        "name": "Ukraine",
        "flag": "🇺🇦",
        "currency": "UAH",
        "locale": "uk_UA",
        "stores": ["Rozetka", "Telemart", "Comfy", "Glovo"]
    },
    "KZ": {
        "name": "Kazakhstan",
        "flag": "🇰🇿",
        "currency": "KZT",
        "locale": "ru_KZ",
        "stores": ["Kaspi.kz", "Sulpak", "Technodom", "Wolt"]
    },
    "EG": {
        "name": "Egypt",
        "flag": "🇪🇬",
        "currency": "EGP",
        "locale": "ar_EG",
        "stores": ["Amazon.eg", "Noon EG", "B.Tech", "Talabat"]
    },
    "PE": {
        "name": "Peru",
        "flag": "🇵🇪",
        "currency": "PEN",
        "locale": "es_PE",
        "stores": ["Falabella PE", "Ripley", "Impacto", "PedidosYa"]
    },
    "QA": {
        "name": "Qatar",
        "flag": "🇶🇦",
        "currency": "QAR",
        "locale": "en_QA",
        "stores": ["Lulu Hypermarket", "Jarir QA", "Virgin Megastore", "Talabat"]
    },
    "CN": {
        "name": "China",
        "flag": "🇨🇳",
        "currency": "CNY",
        "locale": "zh_CN",
        "stores": ["JD.com", "Taobao", "Suning", "Meituan"]
    }
}
