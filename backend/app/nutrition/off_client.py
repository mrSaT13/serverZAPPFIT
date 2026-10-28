"""Open Food Facts proxy client — no key, simple GET with caching via caller."""

import time

import httpx

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
OFF_PRODUCT_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"

# OFF aggressively throttles anonymous traffic (a first request often
# succeeds in <1 s, the next ones hang until they time out), so keep the
# timeout tight and serve repeat queries from an in-memory TTL cache.
TIMEOUT = 12.0
_SEARCH_CACHE_TTL = 600.0  # seconds
_search_cache: dict[tuple[str, str], tuple[float, list[dict]]] = {}


def _cache_get(key: tuple[str, str]) -> list[dict] | None:
    hit = _search_cache.get(key)
    if hit and (time.monotonic() - hit[0]) < _SEARCH_CACHE_TTL:
        return hit[1]
    if hit:
        _search_cache.pop(key, None)
    return None


async def search_off(query: str, language: str = "en", page_size: int = 20) -> list[dict]:
    # `lc` pins the locale: OFF then matches against localized names
    # (Russian product names live in the DB and are only served when lc=ru).
    locale = (language or "en").split("-")[0].lower()
    params = {
        "search_terms": query,
        "json": "1",
        "lc": locale,
        "page_size": page_size,
        "fields": f"code,product_name,product_name_{locale},brands,nutriments,image_front_small_url",
    }
    # OFF search is flaky under load (sporadic read timeouts even for
    # queries that succeed seconds later) — one retry covers the common case.
    cached = _cache_get((query.lower(), locale))
    if cached is not None:
        return cached

    last_error: Exception | None = None
    data: dict | None = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                r = await client.get(
                    OFF_SEARCH_URL,
                    params=params,
                    headers={"User-Agent": "ZAPFIT/0.26 (https://github.com/mrSaT13/serverZAPPFIT)"},
                )
                r.raise_for_status()
                data = r.json()
            break
        except Exception as e:
            last_error = e
            if attempt == 0:
                continue
            raise
    if data is None:
        # Both attempts failed — surface the last error to the caller.
        raise last_error if last_error else RuntimeError("OFF search returned no data")
    out = []
    for p in data.get("products", [])[:page_size]:
        nutr = p.get("nutriments", {})
        # Prefer the localized name when the generic one is empty.
        localized_name = p.get(f"product_name_{locale}") or p.get("product_name")
        out.append(
            {
                "barcode": p.get("code"),
                "product_name": localized_name,
                "brands": p.get("brands"),
                "calories_100g": nutr.get("energy-kcal_100g") or nutr.get("energy_100g"),
                "proteins_100g": nutr.get("proteins_100g"),
                "carbs_100g": nutr.get("carbohydrates_100g"),
                "fat_100g": nutr.get("fat_100g"),
                "image_url": p.get("image_front_small_url"),
            }
        )
    _search_cache[(query.lower(), locale)] = (time.monotonic(), out)
    return out


async def get_product(barcode: str) -> dict | None:
    url = OFF_PRODUCT_URL.format(barcode=barcode)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(url, headers={"User-Agent": "ZAPFIT/0.20"})
        r.raise_for_status()
        data = r.json()
        if data.get("status") != 1:
            return None
        p = data.get("product", {})
        nutr = p.get("nutriments", {})
        return {
            "barcode": barcode,
            "product_name": p.get("product_name") or p.get("product_name_en"),
            "brands": p.get("brands"),
            "calories_100g": nutr.get("energy-kcal_100g"),
            "proteins_100g": nutr.get("proteins_100g"),
            "carbs_100g": nutr.get("carbohydrates_100g"),
            "fat_100g": nutr.get("fat_100g"),
            "image_url": p.get("image_front_small_url"),
        }
