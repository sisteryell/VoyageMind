"""Comprehensive country knowledge base for RAG-powered resolution.

Combines pycountry's built-in data with a curated set of extended aliases
(abbreviations, informal names, native names) to produce a corpus of
(variant_text, canonical_name) pairs suitable for vector embedding.
"""

from __future__ import annotations

import pycountry


EXTENDED_ALIASES: dict[str, str] = {
    # North America
    "america": "US",
    "the states": "US",
    "united states": "US",
    "usa": "US",
    "u.s.a": "US",
    "u.s": "US",
    "us": "US",
    "murica": "US",
    "canada": "CA",
    "mexico": "MX",

    # United Kingdom & constituents
    "uk": "GB",
    "u.k": "GB",
    "britain": "GB",
    "great britain": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",

    # Europe
    "holland": "NL",
    "the netherlands": "NL",
    "czech republic": "CZ",
    "czechia": "CZ",
    "deutschland": "DE",
    "allemagne": "DE",
    "espana": "ES",
    "spain": "ES",
    "italia": "IT",
    "france": "FR",
    "la france": "FR",
    "schweiz": "CH",
    "suisse": "CH",
    "svizzera": "CH",
    "helvetia": "CH",
    "swiss": "CH",
    "switzerland": "CH",
    "osterreich": "AT",
    "austria": "AT",
    "hellas": "GR",
    "greece": "GR",
    "polska": "PL",
    "poland": "PL",
    "portugal": "PT",
    "sverige": "SE",
    "sweden": "SE",
    "norge": "NO",
    "norway": "NO",
    "suomi": "FI",
    "finland": "FI",
    "danmark": "DK",
    "denmark": "DK",
    "eire": "IE",
    "ireland": "IE",
    "magyarorszag": "HU",
    "hungary": "HU",
    "romania": "RO",
    "hrvatska": "HR",
    "croatia": "HR",
    "srbija": "RS",
    "serbia": "RS",
    "slovensko": "SK",
    "slovakia": "SK",
    "slovenija": "SI",
    "slovenia": "SI",
    "lietuva": "LT",
    "lithuania": "LT",
    "latvija": "LV",
    "latvia": "LV",
    "eesti": "EE",
    "estonia": "EE",
    "malta": "MT",
    "island": "IS",
    "iceland": "IS",
    "luksemburg": "LU",
    "luxembourg": "LU",
    "belgie": "BE",
    "belgium": "BE",

    # Middle East
    "uae": "AE",
    "emirates": "AE",
    "dubai country": "AE",
    "ksa": "SA",
    "saudi": "SA",
    "saudi arabia": "SA",
    "persia": "IR",
    "iran": "IR",
    "turkey": "TR",
    "turkiye": "TR",

    # Asia
    "south korea": "KR",
    "rok": "KR",
    "korea": "KR",
    "north korea": "KP",
    "dprk": "KP",
    "nippon": "JP",
    "nihon": "JP",
    "japan": "JP",
    "zhongguo": "CN",
    "china": "CN",
    "prc": "CN",
    "bharat": "IN",
    "hindustan": "IN",
    "india": "IN",
    "siam": "TH",
    "thailand": "TH",
    "burma": "MM",
    "myanmar": "MM",
    "ceylon": "LK",
    "sri lanka": "LK",
    "kampuchea": "KH",
    "cambodia": "KH",
    "pilipinas": "PH",
    "philippines": "PH",
    "indonesia": "ID",
    "vietnam": "VN",
    "viet nam": "VN",
    "malaysia": "MY",
    "singapore": "SG",
    "pakistan": "PK",
    "bangladesh": "BD",
    "nepal": "NP",
    "taiwan": "TW",
    "roc": "TW",
    "formosa": "TW",
    "mongolia": "MN",
    "hong kong": "HK",
    "macau": "MO",
    "macao": "MO",

    # Oceania
    "oz": "AU",
    "aussie": "AU",
    "australia": "AU",
    "nz": "NZ",
    "new zealand": "NZ",
    "aotearoa": "NZ",
    "kiwi land": "NZ",
    "fiji": "FJ",
    "papua new guinea": "PG",
    "png": "PG",

    # Africa
    "south africa": "ZA",
    "sa": "ZA",
    "rsa": "ZA",
    "ivory coast": "CI",
    "cote divoire": "CI",
    "egypt": "EG",
    "misr": "EG",
    "masr": "EG",
    "morocco": "MA",
    "maghreb": "MA",
    "ethiopia": "ET",
    "kenya": "KE",
    "nigeria": "NG",
    "naija": "NG",
    "ghana": "GH",
    "tanzania": "TZ",
    "tunisia": "TN",
    "algeria": "DZ",
    "libya": "LY",
    "sudan": "SD",
    "uganda": "UG",
    "mozambique": "MZ",
    "madagascar": "MG",
    "cameroon": "CM",
    "zimbabwe": "ZW",
    "namibia": "NA",
    "botswana": "BW",
    "rwanda": "RW",
    "senegal": "SN",
    "congo": "CD",
    "drc": "CD",

    # South & Central America
    "brasil": "BR",
    "brazil": "BR",
    "argentina": "AR",
    "colombia": "CO",
    "peru": "PE",
    "chile": "CL",
    "venezuela": "VE",
    "ecuador": "EC",
    "bolivia": "BO",
    "paraguay": "PY",
    "uruguay": "UY",
    "costa rica": "CR",
    "panama": "PA",
    "cuba": "CU",
    "dominican republic": "DO",
    "dr": "DO",
    "haiti": "HT",
    "jamaica": "JM",
    "trinidad": "TT",
    "trinidad and tobago": "TT",
    "puerto rico": "PR",
    "guatemala": "GT",
    "honduras": "HN",
    "el salvador": "SV",
    "nicaragua": "NI",

    # Central Asia & Caucasus
    "russia": "RU",
    "rossiya": "RU",
    "ukraine": "UA",
    "ukraina": "UA",
    "belarus": "BY",
    "georgia": "GE",
    "armenia": "AM",
    "azerbaijan": "AZ",
    "kazakhstan": "KZ",
    "uzbekistan": "UZ",
    "turkmenistan": "TM",
    "kyrgyzstan": "KG",
    "tajikistan": "TJ",

    # Caribbean & Islands
    "bahamas": "BS",
    "bermuda": "BM",
    "barbados": "BB",
    "cayman islands": "KY",
    "maldives": "MV",
    "mauritius": "MU",
    "seychelles": "SC",
    "cyprus": "CY",

    # Others
    "vatican": "VA",
    "holy see": "VA",
    "palestine": "PS",
    "israel": "IL",
    "lebanon": "LB",
    "jordan": "JO",
    "iraq": "IQ",
    "syria": "SY",
    "yemen": "YE",
    "oman": "OM",
    "bahrain": "BH",
    "qatar": "QA",
    "kuwait": "KW",
    "afghanistan": "AF",
}


def build_country_corpus() -> list[tuple[str, str]]:
    """Build the full corpus of (variant_text, canonical_name) pairs.

    Merges pycountry's built-in names/codes with the curated EXTENDED_ALIASES
    to produce a deduplicated list suitable for embedding.
    """
    corpus: dict[str, str] = {}

    for country in pycountry.countries:
        canonical = country.name
        for attr in ("name", "official_name", "common_name", "alpha_2", "alpha_3"):
            value = getattr(country, attr, None)
            if value:
                key = value.strip().lower()
                if key not in corpus:
                    corpus[key] = canonical

    for alias, alpha2 in EXTENDED_ALIASES.items():
        key = alias.strip().lower()
        if key in corpus:
            continue
        try:
            country = pycountry.countries.get(alpha_2=alpha2)
            if country:
                corpus[key] = country.name
        except Exception:
            pass

    return [(variant, canonical) for variant, canonical in corpus.items()]