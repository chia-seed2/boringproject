import json
import re
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (ScanGuardBot)"
}


def ensure_scheme(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def fetch_response(url: str):
    url = ensure_scheme(url)
    res = requests.get(url, headers=HEADERS, timeout=20)
    res.raise_for_status()
    return res


def fetch_html(url: str) -> str:
    return fetch_response(url).text


def fetch_text(url: str) -> str:
    return fetch_response(url).text


def clean_url(url: str) -> str:
    parsed = urlparse(url)
    cleaned = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        cleaned += f"?{parsed.query}"
    return cleaned


def get_internal_links(base_url: str, html: str):
    soup = BeautifulSoup(html, "lxml")
    links = set()
    base_netloc = urlparse(base_url).netloc

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        if parsed.scheme in {"http", "https"} and parsed.netloc == base_netloc:
            links.add(clean_url(full_url))

    return list(links)


def is_product_url(url: str):
    url_lower = url.lower()

    product_patterns = [
        "/product/",
        "/products/",
        "/products-",
        "/item/",
    ]

    bad_patterns = [
        "/collections/",
        "/pages/",
        "/blogs/",
        "/cart",
        "/account",
        "/search",
        "/policies/",
    ]

    if any(bad in url_lower for bad in bad_patterns):
        return False

    return any(pattern in url_lower for pattern in product_patterns)


def extract_price_from_text(text: str):
    patterns = [
        r"€\s?\d+(?:[.,]\d{1,2})?",
        r"£\s?\d+(?:[.,]\d{1,2})?",
        r"\$\s?\d+(?:[.,]\d{1,2})?"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)

    return None


def normalize_price_value(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return value

    s = str(value).strip()
    s = s.replace("€", "").replace("£", "").replace("$", "")
    s = s.replace(",", "")

    try:
        return float(s)
    except ValueError:
        return None


def find_product_in_jsonld(data):
    if isinstance(data, dict):
        item_type = data.get("@type")

        if item_type == "Product":
            return data

        if isinstance(item_type, list) and "Product" in item_type:
            return data

        if "@graph" in data and isinstance(data["@graph"], list):
            for item in data["@graph"]:
                found = find_product_in_jsonld(item)
                if found:
                    return found

        for value in data.values():
            found = find_product_in_jsonld(value)
            if found:
                return found

    elif isinstance(data, list):
        for item in data:
            found = find_product_in_jsonld(item)
            if found:
                return found

    return None


def extract_offer_fields(product_data):
    offers = product_data.get("offers")

    if isinstance(offers, list) and offers:
        offers = offers[0]

    if not isinstance(offers, dict):
        return {
            "price": None,
            "compare_at_price": None,
            "currency": None,
            "availability": None,
            "sku": product_data.get("sku"),
        }

    price = offers.get("price")
    currency = offers.get("priceCurrency")
    availability = offers.get("availability")

    compare_at_price = (
        offers.get("highPrice")
        or offers.get("priceSpecification", {}).get("price")
        if isinstance(offers.get("priceSpecification"), dict)
        else None
    )

    return {
        "price": normalize_price_value(price),
        "compare_at_price": normalize_price_value(compare_at_price),
        "currency": currency,
        "availability": availability,
        "sku": product_data.get("sku"),
    }


def extract_meta_price(soup: BeautifulSoup):
    selectors = [
        {"attrs": {"property": "product:price:amount"}},
        {"attrs": {"property": "og:price:amount"}},
        {"attrs": {"itemprop": "price"}},
        {"attrs": {"name": "twitter:data1"}},
    ]

    for selector in selectors:
        tag = soup.find(attrs=selector["attrs"])
        if tag:
            value = tag.get("content") or tag.get("value") or tag.get_text(strip=True)
            if value:
                return normalize_price_value(value)

    return None


def extract_product(url: str):
    try:
        html = fetch_html(url)
        soup = BeautifulSoup(html, "lxml")

        # JSON-LD first
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            raw = script.string
            if not raw:
                continue

            try:
                data = json.loads(raw)
                product_data = find_product_in_jsonld(data)

                if product_data:
                    offer_fields = extract_offer_fields(product_data)

                    title = product_data.get("name") or (soup.title.string.strip() if soup.title else "No title")

                    return {
                        "url": url,
                        "title": title,
                        "price": offer_fields["price"],
                        "compare_at_price": offer_fields["compare_at_price"],
                        "currency": offer_fields["currency"] or "EUR",
                        "availability": offer_fields["availability"],
                        "sku": offer_fields["sku"],
                        "source": "jsonld",
                    }
            except Exception:
                continue

        # Meta fallback
        title = soup.title.string.strip() if soup.title else "No title"
        meta_price = extract_meta_price(soup)

        if meta_price is not None:
            return {
                "url": url,
                "title": title,
                "price": meta_price,
                "compare_at_price": None,
                "currency": "EUR",
                "availability": None,
                "sku": None,
                "source": "meta",
            }

        # Text fallback
        text = soup.get_text(" ", strip=True)
        text_price = extract_price_from_text(text)

        return {
            "url": url,
            "title": title,
            "price": normalize_price_value(text_price),
            "compare_at_price": None,
            "currency": "EUR",
            "availability": None,
            "sku": None,
            "source": "text",
        }

    except Exception as e:
        return {
            "url": url,
            "title": None,
            "price": None,
            "compare_at_price": None,
            "currency": None,
            "availability": None,
            "sku": None,
            "source": "error",
            "error": str(e),
        }


def parse_sitemap_xml(xml_text: str):
    try:
        root = ET.fromstring(xml_text)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        sitemap_locs = root.findall(".//sm:sitemap/sm:loc", ns)
        if sitemap_locs:
            return {
                "type": "index",
                "urls": [node.text.strip() for node in sitemap_locs if node.text]
            }

        url_locs = root.findall(".//sm:url/sm:loc", ns)
        if url_locs:
            return {
                "type": "urlset",
                "urls": [node.text.strip() for node in url_locs if node.text]
            }
    except Exception:
        pass

    return {"type": "unknown", "urls": []}


def discover_product_urls_from_sitemap(base_url: str, max_sitemap_urls: int = 10000):
    candidates = [
        urljoin(base_url, "/sitemap.xml"),
        urljoin(base_url, "/sitemap_products_1.xml"),
        urljoin(base_url, "/product-sitemap.xml"),
        urljoin(base_url, "/sitemap_products.xml"),
    ]

    discovered = set()
    checked = set()

    def process_sitemap(sitemap_url: str):
        if sitemap_url in checked or len(checked) > 30:
            return

        checked.add(sitemap_url)

        try:
            xml_text = fetch_text(sitemap_url)
        except Exception:
            return

        parsed = parse_sitemap_xml(xml_text)

        if parsed["type"] == "index":
            for child in parsed["urls"]:
                child_lower = child.lower()
                if "product" in child_lower or "sitemap" in child_lower:
                    process_sitemap(child)

        elif parsed["type"] == "urlset":
            for found_url in parsed["urls"]:
                if is_product_url(found_url):
                    discovered.add(found_url)
                if len(discovered) >= max_sitemap_urls:
                    return

    for candidate in candidates:
        process_sitemap(candidate)

    return list(discovered)


def discover_product_urls_from_homepage(base_url: str, max_links: int = 300):
    homepage = fetch_html(base_url)
    links = get_internal_links(base_url, homepage)
    product_links = [link for link in links if is_product_url(link)]
    return product_links[:max_links]


def scan_site(url: str, max_pages: int = 100):
    url = ensure_scheme(url)

    product_links = discover_product_urls_from_sitemap(url)

    if not product_links:
        product_links = discover_product_urls_from_homepage(url)

    results = []
    seen = set()

    for link in product_links:
        if link in seen:
            continue
        seen.add(link)

        data = extract_product(link)

        # only keep likely real product pages
        if data and data.get("title") and data.get("price") is not None:
            results.append(data)

        if len(results) >= max_pages:
            break

    return results