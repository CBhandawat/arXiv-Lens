import requests
from bs4 import BeautifulSoup


HEADERS = {"User-Agent": "Mozilla/5.0 (ArXivCast/1.0)"}


def scrape_recent(category: str, max_papers: int = 5) -> list[dict]:
    """
    Scrape recent papers from arXiv for a given category.
    Returns list of dicts with arxiv_id, arxiv_url, title, authors.
    """
    url = f"https://arxiv.org/list/{category}/recent"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[scraper] Failed to fetch {category}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    dl = soup.find("dl")
    if not dl:
        return []

    papers = []
    for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
        if len(papers) >= max_papers:
            break
        try:
            link_tag = dt.find("a", title="Abstract")
            if not link_tag:
                continue
            arxiv_id = link_tag.text.strip().replace("arXiv:", "")
            arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

            title_tag = dd.find("div", class_="list-title")
            title = title_tag.text.replace("Title:", "").strip() if title_tag else "Unknown Title"

            authors_tag = dd.find("div", class_="list-authors")
            authors = authors_tag.text.replace("Authors:", "").strip() if authors_tag else ""

            papers.append({
                "arxiv_id": arxiv_id,
                "arxiv_url": arxiv_url,
                "title": title,
                "authors": authors[:300],
                "category": category,
            })
        except Exception:
            continue

    return papers


def fetch_abstract(arxiv_url: str) -> str:
    """Fetch the abstract text from an arXiv abstract page."""
    try:
        resp = requests.get(arxiv_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        block = soup.find("blockquote", class_="abstract")
        if block:
            return block.text.replace("Abstract:", "").strip()
    except Exception:
        pass
    return ""
