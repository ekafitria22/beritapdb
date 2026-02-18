# utils/scraper_detik.py

import time
import requests
import pandas as pd
from bs4 import BeautifulSoup as bs

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GDPNewsStreamlit/1.0)",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

def detikcom_search_page(query, siteid, from_date, to_date, page=1, timeout=20, sleep_s=0.8):
    url = (
        "https://www.detik.com/search/searchnews"
        f"?query={query}&siteid={siteid}&sortby=time"
        f"&fromdatex={from_date}&todatex={to_date}"
        f"&page={page}&result_type=latest"
    )
    time.sleep(sleep_s)
    r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    r.raise_for_status()
    return bs(r.content, "html.parser")

def _extract_list_items(soup):
    return soup.find_all("article", class_="list-content__item")

def scrape_detik_search(
    query,
    siteid,
    from_date,  # dd/mm/yyyy
    to_date,    # dd/mm/yyyy
    max_articles=50,
    timeout=20,
    sleep_s=0.8,
    progress_cb=None
):
    results = []
    seen = set()

    page = 1
    while len(results) < max_articles:
        soup = detikcom_search_page(query, siteid, from_date, to_date, page=page, timeout=timeout, sleep_s=sleep_s)
        items = _extract_list_items(soup)
        if not items:
            break

        for it in items:
            a = it.find("a", {"class": "media__link"})
            if not a:
                continue
            title = a.get("dtr-ttl") or a.get_text(strip=True)
            url = a.get("href")
            if not title or not url:
                continue
            if url in seen:
                continue

            subtitle = it.find("h2", class_="media__subtitle")
            category = subtitle.get_text(strip=True) if subtitle else ""
            date_span = it.find("span", title=True)
            publish_date = date_span.get("title") if date_span else ""

            results.append({
                "title": title,
                "category": category,
                "publish_date": publish_date,
                "article_url": url,
            })
            seen.add(url)

            if progress_cb:
                progress_cb(len(results), max_articles)

            if len(results) >= max_articles:
                break

        page += 1
        if page > 50:  # safety stop
            break

    return pd.DataFrame(results)

