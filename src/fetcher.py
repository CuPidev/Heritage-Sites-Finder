"""Fetcher that reliably obtains UNESCO World Heritage site records.

Strategy:
- Try a JSON endpoint (default: https://whc.unesco.org/en/list/json/). If the JSON
  response contains a list of site records, normalize and return them.
- Otherwise, fall back to scraping the public listing pages and individual site pages
  using BeautifulSoup. The scraper looks for links like `/en/list/<id>` and extracts
  name, description, country and coordinates with heuristics.

The returned record schema (per site):
  {
    'id': str,
    'name': str,
    'description': str,
    'country': str,
    'latitude': float|None,
    'longitude': float|None,
    'raw': original_raw_or_meta
  }
"""

from typing import List, Dict, Any, Optional
import re
import time
import logging
import os
import json
import xml.etree.ElementTree as ET
from html import unescape

try:
    import requests
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - runtime deps
    requests = None
    BeautifulSoup = None

LOGGER = logging.getLogger(__name__)

DEFAULT_JSON_URL = "https://whc.unesco.org/en/list/json/"
BASE_LIST_URL = "https://whc.unesco.org/en/list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_unesco_list(
    url: str = DEFAULT_JSON_URL, timeout: int = 10, max_sites: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Fetch and normalize UNESCO World Heritage site records.

    Args:
      url: JSON endpoint to try first (defaults to UNESCO JSON listing).
      timeout: network timeout for requests.
      max_sites: if set, limit returned sites to this number (useful for testing).

    Returns:
      A list of normalized site dicts.
    """
    # Try JSON endpoint first
    if requests is not None:
        try:
            r = requests.get(url, timeout=timeout, headers=HEADERS)
            r.raise_for_status()
            data = r.json()
            sites = _extract_sites_from_json(data)
            if sites:
                normalized = [_normalize_site_record(s) for s in sites]
                return normalized[:max_sites] if max_sites else normalized
        except Exception as e:
            LOGGER.debug("JSON fetch failed: %s", e)

    # Fallback to HTML scraping
    return _scrape_unesco_list_html(max_sites=max_sites)


def _extract_sites_from_json(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("sites", "rows", "data", "results"):
            if k in data and isinstance(data[k], list):
                return data[k]
        # otherwise return the first list-valued entry
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


def _normalize_site_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    def _get(d, keys, default=""):
        if isinstance(keys, str):
            keys = (keys,)
        for k in keys:
            if isinstance(d, dict) and k in d and d[k] is not None:
                return d[k]
        return default

    site_id = str(_get(raw, ("id", "site_id", "ref", "whc_id"), ""))
    name = _get(raw, ("name", "name_en", "title", "site_name"), "")
    description = _get(raw, ("description", "short_description", "summary", "desc"), "")
    country = _get(raw, ("state", "states", "country", "country_en"), "")

    # normalize list-valued country
    if isinstance(country, list):
        country = ", ".join(
            [str(c.get("name")) if isinstance(c, dict) else str(c) for c in country]
        )

    # coords
    lat = _get(raw, ("latitude", "lat"), None)
    lon = _get(raw, ("longitude", "lon", "lng"), None)
    try:
        lat = float(lat) if lat not in (None, "") else None
        lon = float(lon) if lon not in (None, "") else None
    except Exception:
        lat = lon = None

    return {
        "id": site_id,
        "name": str(name) if name is not None else "",
        "description": str(description) if description is not None else "",
        "country": str(country) if country is not None else "",
        "latitude": lat,
        "longitude": lon,
        "raw": raw,
    }


def _scrape_unesco_list_html(max_sites: Optional[int] = None) -> List[Dict[str, Any]]:
    if requests is None or BeautifulSoup is None:
        raise RuntimeError("requests and beautifulsoup4 are required for HTML scraping")

    r = requests.get(BASE_LIST_URL, timeout=15, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    anchors = soup.find_all("a", href=True)
    links = []
    for a in anchors:
        href = a["href"]
        m = re.search(r"/en/list/(\d+)(?:/|$)", href)
        if m:
            url = requests.compat.urljoin(BASE_LIST_URL, href)
            if url not in links:
                links.append(url)

    # loose fallback
    if not links:
        for a in anchors:
            href = a["href"]
            if "/en/list/" in href:
                url = requests.compat.urljoin(BASE_LIST_URL, href.split("?")[0])
                if url not in links:
                    links.append(url)

    results = []
    for link in links:
        if max_sites and len(results) >= max_sites:
            break
        try:
            site = _scrape_site_page(link)
            results.append(site)
        except Exception:
            LOGGER.debug("failed to scrape %s", link, exc_info=True)
            continue
        time.sleep(0.05)
    return results


def _scrape_site_page(url: str) -> Dict[str, Any]:
    r = requests.get(url, timeout=15, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    m = re.search(r"/en/list/(\d+)", url)
    site_id = m.group(1) if m else url

    name = ""
    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(strip=True)
    else:
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            name = og["content"]

    # description: try common containers then fallback to first paragraphs
    description_chunks = []
    for sel in [
        "#content",
        ".content",
        "#description",
        ".description",
        ".site-description",
    ]:
        container = soup.select_one(sel)
        if container:
            for p in container.find_all("p"):
                t = p.get_text(strip=True)
                if t:
                    description_chunks.append(t)
            if description_chunks:
                break

    if not description_chunks:
        for p in soup.find_all("p")[:6]:
            t = p.get_text(strip=True)
            if t:
                description_chunks.append(t)

    description = "\n\n".join(description_chunks)

    text = soup.get_text(separator="\n")
    country = ""

    # Try several heuristics to find the State Party / Country field
    # 1) look for table rows or definition lists where a label is followed by a value
    try:
        # common table format: <th>State Party</th><td>Country Name</td>
        for th in soup.find_all("th"):
            label = th.get_text(strip=True)
            if re.search(r"State Party|State\(s\) Party|Country", label, re.IGNORECASE):
                td = th.find_next_sibling("td")
                if td:
                    country = td.get_text(strip=True)
                    break
        # definition list: <dt>State Party</dt><dd>Country</dd>
        if not country:
            for dt in soup.find_all("dt"):
                label = dt.get_text(strip=True)
                if re.search(r"State Party|Country", label, re.IGNORECASE):
                    dd = dt.find_next_sibling("dd")
                    if dd:
                        country = dd.get_text(strip=True)
                        break
    except Exception:
        LOGGER.debug("table/dl country extraction failed for %s", url, exc_info=True)

    # 2) try common inline labels in the page text
    if not country:
        m = re.search(r"State Party[:\s]+(.+)", text, re.IGNORECASE)
        if m:
            country = m.group(1).strip()
        else:
            m = re.search(r"Country[:\s]+(.+)", text, re.IGNORECASE)
            if m:
                country = m.group(1).strip()

    # 3) try meta tags
    if not country:
        og = soup.find("meta", attrs={"name": "country"}) or soup.find(
            "meta", property="whc:state_party"
        )
        if og and og.get("content"):
            country = og["content"].strip()

    lat = lon = None
    coord_matches = re.findall(
        r"([-+]?\d{1,2}\.\d+)[,;\s]+([-+]?\d{1,3}\.\d+)", soup.text
    )
    if coord_matches:
        try:
            lat = float(coord_matches[0][0])
            lon = float(coord_matches[0][1])
        except Exception:
            lat = lon = None

    # Some pages include geo meta tags (geo.position or icbm)
    try:
        geo = soup.find("meta", attrs={"name": "geo.position"})
        if geo and geo.get("content"):
            parts = (
                geo["content"].split(";")
                if ";" in geo["content"]
                else geo["content"].split(",")
            )
            if len(parts) >= 2:
                try:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                except Exception:
                    pass
    except Exception:
        pass

    # Normalize country value (strip trailing labels, footnotes, and long text)
    if country:
        country = _normalize_country_string(country)

    # best-effort continent mapping
    continent = None
    if country:
        continent = _country_to_continent(country)

    return {
        "id": site_id,
        "name": name or "",
        "description": description or "",
        "country": country or "",
        "continent": continent,
        "latitude": lat,
        "longitude": lon,
        "raw": {"url": url},
    }


def sample_sites() -> List[Dict[str, Any]]:
    return [
        {
            "id": "1",
            "name": "Ancient Temple",
            "description": "An ancient temple complex with historic ruins.",
            "country": "Sampleland",
            "latitude": None,
            "longitude": None,
            "raw": {},
        },
        {
            "id": "2",
            "name": "Historic City",
            "description": "A city with medieval architecture.",
            "country": "Sampleland",
            "latitude": None,
            "longitude": None,
            "raw": {},
        },
    ]


def load_sites_from_rss(
    rss_path: str,
    save_raw_to: str = "data/sites.rss",
    save_json_to: str = "data/sites_from_rss.json",
    max_sites: Optional[int] = None,
    follow_links: bool = False,
) -> List[Dict[str, Any]]:
    """Load and normalize site records from a local RSS file.

    This is a fast path that does not follow each item's link by default.

    Args:
      rss_path: path to the RSS/XML file (local).
      save_raw_to: where to write a copy of the raw RSS (created dirs if needed).
      save_json_to: where to write the normalized JSON output.
      max_sites: optional limit on how many sites to return.
      follow_links: if True, will attempt to follow the item's link and
        scrape the site page for richer metadata (may be slow and may be
        blocked by the remote server).

    Returns:
      A list of normalized site dicts using the canonical schema.
    """
    # read raw RSS
    with open(rss_path, "rb") as f:
        raw_bytes = f.read()

    # ensure output directory exists and save a raw copy
    os.makedirs(os.path.dirname(save_raw_to) or ".", exist_ok=True)
    try:
        with open(save_raw_to, "wb") as f:
            f.write(raw_bytes)
    except Exception:
        LOGGER.debug("failed to write raw rss to %s", save_raw_to, exc_info=True)

    # parse RSS XML
    try:
        # some pasted RSS files may include a non-XML prefix (browser notice text).
        # Trim any leading bytes before the first '<' to be forgiving.
        first_lt = raw_bytes.find(b"<")
        if first_lt > 0:
            xml_bytes = raw_bytes[first_lt:]
        else:
            xml_bytes = raw_bytes
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        raise RuntimeError(f"failed to parse RSS file {rss_path}: {e}")

    items = []
    # RSS channel/item structure: <rss><channel><item>...</item></channel></rss>
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        link = link_el.text.strip() if link_el is not None and link_el.text else ""
        description = desc_el.text or ""
        description = _strip_html(unescape(description)).strip()

        # extract id from link if it matches /en/list/<id>
        m = re.search(r"/en/list/(\d+)", link)
        site_id = m.group(1) if m else link

        rec = {
            "id": str(site_id),
            "name": title,
            "description": description,
            "country": "",
            "latitude": None,
            "longitude": None,
            "raw": {"link": link, "rss_item": ET.tostring(item, encoding="unicode")},
        }

        # Optionally follow the link and try to scrape richer metadata
        if follow_links and link and requests is not None and BeautifulSoup is not None:
            try:
                scraped = _scrape_site_page(link)
                # merge scraped fields when present
                for k in ("name", "description", "country", "latitude", "longitude"):
                    if scraped.get(k):
                        rec[k] = scraped[k]
                rec["raw"]["scraped_url"] = link
            except Exception:
                LOGGER.debug("follow-link scrape failed for %s", link, exc_info=True)

        items.append(rec)
        if max_sites and len(items) >= max_sites:
            break

    # save normalized JSON
    try:
        with open(save_json_to, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        LOGGER.debug(
            "failed to write normalized json to %s", save_json_to, exc_info=True
        )

    return items


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string, using BeautifulSoup when available,
    else a simple fallback regex. Returns unescaped text."""
    if not text:
        return ""
    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(text, "lxml")
            return soup.get_text(separator=" ", strip=True)
        except Exception:
            pass
    # fallback: remove tags
    cleaned = re.sub(r"<[^>]+>", "", text)
    return cleaned


def _normalize_country_string(s: str) -> str:
    """Clean up a raw country/state party string.

    Removes extraneous labels, shortens long sequences, and returns a concise name.
    """
    if not s:
        return ""
    s = re.sub(r"\(.*?\)", "", s)  # remove parenthetical notes
    s = re.sub(r"State Party[:\s]*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"Country[:\s]*", "", s, flags=re.IGNORECASE)
    s = s.strip()
    # often the field contains multiple countries separated by ';' or ',' - keep the first
    if ";" in s:
        s = s.split(";")[0].strip()
    if "," in s and len(s.split(",")[0]) > 1:
        s = s.split(",")[0].strip()
    # clamp length
    if len(s) > 120:
        s = s[:120].rsplit(" ", 1)[0]
    return s


# Minimal country->continent mapping to cover the majority of cases we expect.
# This is intentionally small and extendable; unmapped countries will yield None.
_COUNTRY_CONTINENT = {
    # Asia
    "China": "Asia",
    "India": "Asia",
    "Cambodia": "Asia",
    "Japan": "Asia",
    "Republic of Korea": "Asia",
    "Korea, Republic of": "Asia",
    "Korea": "Asia",
    "Nepal": "Asia",
    "Thailand": "Asia",
    "Malaysia": "Asia",
    "Indonesia": "Asia",
    "Vietnam": "Asia",
    "Pakistan": "Asia",
    "Sri Lanka": "Asia",
    "Bangladesh": "Asia",
    "Myanmar": "Asia",
    "Philippines": "Asia",
    "India, Nepal": "Asia",
    # Europe
    "France": "Europe",
    "Germany": "Europe",
    "United Kingdom": "Europe",
    "Italy": "Europe",
    "Spain": "Europe",
    "Poland": "Europe",
    "Russian Federation": "Europe",
    "Ukraine": "Europe",
    "Switzerland": "Europe",
    "Belgium": "Europe",
    # Africa
    "Egypt": "Africa",
    "Morocco": "Africa",
    "South Africa": "Africa",
    "Ethiopia": "Africa",
    "Kenya": "Africa",
    # North America
    "United States of America": "North America",
    "United States": "North America",
    "Canada": "North America",
    "Mexico": "North America",
    # South America
    "Brazil": "South America",
    "Argentina": "South America",
    "Peru": "South America",
    # Oceania
    "Australia": "Oceania",
    "New Zealand": "Oceania",
    # Middle East / western Asia common names
    "Iran (Islamic Republic of)": "Asia",
    "Iran": "Asia",
    "Saudi Arabia": "Asia",
}


def _country_to_continent(country_name: str) -> Optional[str]:
    if not country_name:
        return None
    # direct lookup
    if country_name in _COUNTRY_CONTINENT:
        return _COUNTRY_CONTINENT[country_name]
    # try normalized capitalization and known aliases
    key = country_name.strip()
    # remove trailing punctuation
    key = key.rstrip(".;")
    # common alias fixes
    if key.lower().endswith(", people's republic of china"):
        return "Asia"
    # contain checks (e.g., "China (People's Rep.)")
    for k, v in _COUNTRY_CONTINENT.items():
        if k.lower() in key.lower() or key.lower() in k.lower():
            return v
    # check for continent words inside the country text
    if re.search(
        r"\b(Asia|European|Africa|Americ|Oceania|Pacific)\b", key, re.IGNORECASE
    ):
        m = re.search(
            r"\b(Asia|Africa|Europe|Oceania|Pacific|America|Americas)\b",
            key,
            re.IGNORECASE,
        )
        if m:
            found = m.group(1)
            # normalize common variants
            if found.lower().startswith("amer"):
                # ambiguous: America -> North or South; default to North America when 'United' appears
                if "United" in key or "USA" in key or "United States" in key:
                    return "North America"
                return "South America"
            if found.lower().startswith("pacif"):
                return "Oceania"
            return found.capitalize()
    return None


def enrich_sites(
    sites: List[Dict[str, Any]],
    concurrency: int = 6,
    save_every: int = 50,
    out_path: str = "data/sites_enriched.json",
):
    """Enrich a list of site records by following links for missing metadata.

    This function mutates the input list in-place and also writes incremental
    progress to `out_path` every `save_every` updated records. It will call
    `_scrape_site_page` to attempt richer metadata.
    """
    if requests is None or BeautifulSoup is None:
        raise RuntimeError("requests and beautifulsoup4 are required for enrichment")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    updated = 0
    for i, s in enumerate(sites):
        link = None
        try:
            raw = s.get("raw") or {}
            link = raw.get("link") or (
                raw.get("url") if isinstance(raw, dict) else None
            )
            needs = (
                not s.get("country") or not s.get("latitude") or not s.get("longitude")
            )
            if link and needs:
                scraped = _scrape_site_page(link)
                for k in (
                    "name",
                    "description",
                    "country",
                    "latitude",
                    "longitude",
                    "continent",
                ):
                    if scraped.get(k):
                        s[k] = scraped[k]
                s.setdefault("raw", {})
                s["raw"]["scraped_url"] = link
                updated += 1
        except Exception:
            LOGGER.debug("enrich failed for %s", link or s.get("id"), exc_info=True)

        if updated and updated % save_every == 0:
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(sites, f, ensure_ascii=False, indent=2)
            except Exception:
                LOGGER.debug("failed to write progress to %s", out_path, exc_info=True)
    # final save
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(sites, f, ensure_ascii=False, indent=2)
    except Exception:
        LOGGER.debug(
            "failed to write final enriched sites to %s", out_path, exc_info=True
        )
    return sites
