"""Fetcher utilities for UNESCO World Heritage sites.

This module provides a small function to fetch the World Heritage list from a configurable
JSON endpoint. Because public endpoints may change, the fetch function accepts a URL and
returns Python objects parsed from JSON. It also exposes a small sample dataset for tests
and offline use.
"""

from typing import List, Dict

try:
    import requests
except Exception:  # pragma: no cover - requests will normally be installed
    requests = None


def fetch_unesco_list(
    url: str = "https://whc.unesco.org/en/list/json/", timeout: int = 10
) -> List[Dict]:
    """Fetch UNESCO World Heritage list from a JSON endpoint.

    Args:
        url: URL that returns JSON representing the list of sites.
        timeout: network timeout in seconds.

    Returns:
        A list of site dicts. The structure depends on the source; common fields are
        'id', 'name', 'description', and 'states' or 'location'.

    Raises:
        RuntimeError on network/library issues.
    """
    if requests is None:
        raise RuntimeError("requests is not available in this environment")

    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    # The JSON structure varies; try to find a list of sites in common places.
    sites = []
    if isinstance(data, dict):
        # look for common keys
        for key in ("sites", "rows", "data", "results", "features", "siteslist"):
            if key in data and isinstance(data[key], list):
                sites = data[key]
                break
        # fallback: if dict has list values
        if not sites:
            for v in data.values():
                if isinstance(v, list):
                    sites = v
                    break
    elif isinstance(data, list):
        sites = data

    if not sites:
        raise RuntimeError(
            "Could not interpret JSON structure from the UNESCO endpoint"
        )

    # Normalize each site to a consistent dict schema
    normalized = []
    for s in sites:
        norm = normalize_site(s)
        normalized.append(norm)
    return normalized


def sample_sites() -> List[Dict]:
    """Return a tiny sample dataset for offline testing.

    Each site is represented as a dict with keys: id, name, description.
    """
    return [
        {
            "id": "1",
            "name": "Ancient Temple",
            "description": "An ancient temple complex with historic ruins.",
        },
        {
            "id": "2",
            "name": "Historic City",
            "description": "A city with medieval architecture and winding streets.",
        },
        {
            "id": "3",
            "name": "Coastal Landscape",
            "description": "Beautiful coastal cliffs and marine biodiversity.",
        },
    ]


def _get(d: Dict, keys, default=None):
    """Helper to get first existing key from dict-like object."""
    if isinstance(keys, str):
        keys = (keys,)
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def normalize_site(raw: Dict) -> Dict:
    """Try to normalize a UNESCO site record into a common structure.

    Returns keys: id, name, description, country, latitude, longitude, raw
    """
    # Common possible name fields
    name = _get(raw, ("name", "name_en", "title", "site_name"))
    if isinstance(name, dict):
        # some APIs nest localized names
        name = _get(name, ("en", "en_US", "english")) or str(name)

    # possible description fields
    description = _get(raw, ("description", "short_description", "summary", "desc"), "")
    if isinstance(description, dict):
        description = _get(description, ("en", "en_US", "english")) or str(description)

    # country/state
    country = _get(raw, ("state", "states", "country", "country_en"), "")
    if isinstance(country, list):
        country = ", ".join(
            [str(c.get("name")) if isinstance(c, dict) else str(c) for c in country]
        )

    # coordinates can appear in multiple places
    lat = None
    lon = None
    # try top-level keys
    for lat_key, lon_key in (
        ("latitude", "longitude"),
        ("lat", "lon"),
        ("lat", "lng"),
        ("latitude_wgs84", "longitude_wgs84"),
    ):
        if lat_key in raw and lon_key in raw:
            try:
                lat = float(raw[lat_key])
                lon = float(raw[lon_key])
            except Exception:
                lat = None
                lon = None
            break

    # try nested location structures
    if lat is None or lon is None:
        loc = _get(raw, ("location", "coords", "geometry"))
        if isinstance(loc, dict):
            # GeoJSON-like
            if "coordinates" in loc and isinstance(loc["coordinates"], (list, tuple)):
                try:
                    lon, lat = loc["coordinates"][0], loc["coordinates"][1]
                except Exception:
                    pass
            else:
                for lat_key, lon_key in (("lat", "lon"), ("latitude", "longitude")):
                    if lat_key in loc and lon_key in loc:
                        try:
                            lat = float(loc[lat_key])
                            lon = float(loc[lon_key])
                        except Exception:
                            pass

    site_id = str(_get(raw, ("id", "site_id", "ref", "whc_id"), ""))

    return {
        "id": site_id,
        "name": name or "",
        "description": description or "",
        "country": country or "",
        "latitude": lat,
        "longitude": lon,
        "raw": raw,
    }
