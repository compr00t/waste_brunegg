from __future__ import annotations

from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


def find_pdf_link(html: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "Entsorgungsplan" in (a.get_text() or "") and href.lower().endswith(".pdf"):
            return urljoin(base_url, href)
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().endswith(".pdf") and "entsorgungsplan" in href.lower():
            return urljoin(base_url, href)
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().endswith(".pdf"):
            return urljoin(base_url, href)
    return None


async def fetch_entsorgungsplan_pdf(
    client: httpx.AsyncClient, entsorgungsplan_url: str
) -> tuple[str, bytes]:
    page = await client.get(entsorgungsplan_url, follow_redirects=True, timeout=60.0)
    page.raise_for_status()
    pdf_url = find_pdf_link(page.text, entsorgungsplan_url)
    if not pdf_url:
        raise RuntimeError("Could not find Entsorgungsplan PDF link on page")

    pdf_response = await client.get(pdf_url, follow_redirects=True, timeout=120.0)
    pdf_response.raise_for_status()
    pdf_bytes = pdf_response.content
    if not pdf_bytes.startswith(b"%PDF"):
        raise RuntimeError("Downloaded file is not a PDF")
    return pdf_url, pdf_bytes
