"""Open Food Facts proxy client — no key, simple GET with caching via caller."""

import httpx

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
OFF_PRODUCT_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"

TIMEOUT = 8.0


async def search_off(query: str, page_size: int = 20) -> list[dict]:
    params = {
        "search_terms": query,
        "json": "1",
        "page_size": page_size,
        "fields": "code,product_name,brands,nutriments,image_front_small_url",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(OFF_SEARCH_URL, params=params, headers={"User-Agent": "ZAPFIT/0.20"})
        r.raise_for_status()
        data = r.json()
        out = []
        for p in data.get("products", [])[:page_size]:
            nutr = p.get("nutriments", {})
            out.append({
                "barcode": p.get("code"),
                "product_name": p.get("product_name"),
                "brands": p.get("brands"),
                "calories_100g": nutr.get("energy-kcal_100g") or nutr.get("energy_100g"),
                "proteins_100g": nutr.get("proteins_100g"),
                "carbs_100g": nutr.get("carbohydrates_100g"),
                "fat_100g": nutr.get("fat_100g"),
                "image_url": p.get("image_front_small_url"),
            })
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
