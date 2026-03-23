from __future__ import annotations

import calendar
import io
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

import pdfplumber

_DATE_TOKEN = re.compile(
    r"(?:(?<!\d)(\d{1,2})[.,]\s*(\d{1,2})(?:[.,]\s*(\d{2,4}))?)"
)


def _month_year(y: int, month: int, day: int) -> date:
    last = calendar.monthrange(y, month)[1]
    return date(y, month, min(day, last))


def _safe_month_year(y: int, month: int, day: int) -> date | None:
    try:
        return _month_year(y, month, day)
    except (ValueError, OverflowError):
        return None


def _parse_loose_date_tuple(
    d1: str, d2: str, ypart: str | None, default_year: int
) -> date:
    day = int(d1)
    month = int(d2.replace(",", ".").strip("."))
    if ypart:
        year = int(ypart) if len(ypart) == 4 else 2000 + int(ypart)
    else:
        year = default_year
    return _month_year(year, month, day)


def _all_weekdays(start: date, end: date, weekday: int) -> list[date]:
    out: list[date] = []
    d = start
    while d.weekday() != weekday and d <= end:
        d += timedelta(days=1)
    while d <= end:
        out.append(d)
        d += timedelta(days=7)
    return out


def _extract_dates_from_segment(text: str, default_year: int) -> list[date]:
    dates: list[date] = []
    for m in _DATE_TOKEN.finditer(text):
        try:
            dates.append(
                _parse_loose_date_tuple(m.group(1), m.group(2), m.group(3), default_year)
            )
        except (ValueError, OverflowError):
            continue
    return dates


def _segment(text: str, start_kw: str, end_kws: list[str]) -> str:
    low = text.lower()
    s = low.find(start_kw.lower())
    if s == -1:
        return ""
    rest = text[s:]
    end_idx = len(rest)
    for end_kw in end_kws:
        p = rest.lower().find(end_kw.lower())
        if p != -1:
            end_idx = min(end_idx, p)
    return rest[:end_idx]


@dataclass
class ParsedPlan:
    plan_year: int
    pdf_text_page3: str
    hauskehricht_dates: list[date] = field(default_factory=list)
    gruengut_dates: list[date] = field(default_factory=list)
    waschabo: dict[str, list[date]] = field(default_factory=dict)


def _infer_year_from_text(page3: str) -> int:
    m = re.search(r"\b(20\d{2})\b", page3)
    if m:
        return int(m.group(1))
    return date.today().year


def _parse_hauskehricht(page3: str, year: int) -> list[date]:
    block = _segment(page3, "Hauskehricht", ["Grüngut", "Grungut", "Brennbares"])
    if not block:
        return []

    m = re.search(r"ab\s*(\d{1,2})[.,']\s*(\d{1,2})", block, re.I)
    if m:
        start = _safe_month_year(year, int(m.group(2)), int(m.group(1))) or date(
            year, 1, 1
        )
    else:
        start = date(year, 1, 1)

    if "dienstag" in block.lower():
        return _all_weekdays(start, date(year, 12, 31), weekday=1)
    return []


def _parse_gruengut(page3: str, year: int) -> list[date]:
    block = _segment(
        page3, "Grüngut", ["Waschaboservice", "Waschaboseruice", "Brennbares"]
    )
    if not block:
        block = _segment(
            page3, "Grungut", ["Waschaboservice", "Waschaboseruice", "Brennbares"]
        )
    if not block:
        return []

    dates: list[date] = []
    fm = re.search(r"Freitag:\s*([^S]+?)(?=Sa\s|ab\s|Voegtlin|$)", block, re.I | re.S)
    if fm:
        dates.extend(_extract_dates_from_segment(fm.group(1), year))

    sm = re.search(r"Sa\s*(\d{1,2})[.,](\d{1,2})", block, re.I)
    if sm:
        d = _safe_month_year(year, int(sm.group(2)), int(sm.group(1)))
        if d:
            dates.append(d)

    abm = re.search(r"ab\s*(\d{1,2})[.,](\d{1,2})", block, re.I)
    bism = re.search(r"bis\s*(\d{1,2})[.-](\d{1,2})(?:[.,](\d{2,4}))?", block, re.I)
    weekly_hint = re.search(r"w.{0,3}chentlich", block, re.I)
    if abm and bism and weekly_hint:
        d_start = _safe_month_year(year, int(abm.group(2)), int(abm.group(1)))
        y_end = (
            int(bism.group(3))
            if bism.group(3) and len(bism.group(3)) == 4
            else year
        )
        d_end = _safe_month_year(y_end, int(bism.group(2)), int(bism.group(1)))
        if d_start and d_end:
            dates.extend(_all_weekdays(d_start, d_end, weekday=4))

    for m in re.finditer(
        r"Donnerstag\s*(\d{1,2})[.,](\d{1,2})(?:[.,](\d{2,4}))?", block, re.I
    ):
        y = int(m.group(3)) if m.group(3) and len(m.group(3)) == 4 else year
        d = _safe_month_year(y, int(m.group(2)), int(m.group(1)))
        if d:
            dates.append(d)

    m2 = re.search(
        r"(?:^|[^\d])(\d{1,2})[.,](\d{1,2})\s*,?\s*und\s+Donnerstag", block, re.I
    )
    if m2:
        d = _safe_month_year(year, int(m2.group(2)), int(m2.group(1)))
        if d:
            dates.append(d)

    return sorted(set(dates))


def _parse_waschabo_dates_chunk(chunk: str, year: int) -> list[date]:
    compact = re.sub(r"\s+", "", chunk)
    dates: list[date] = []
    for m in re.finditer(r"(\d{2})\.(\d{2})\.(\d{4})", compact):
        d = _safe_month_year(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if d:
            dates.append(d)
    for m in re.finditer(r"(?<!\d)(\d{2})\.(\d{2})\.(?!\d)", compact):
        d = _safe_month_year(year, int(m.group(2)), int(m.group(1)))
        if d:
            dates.append(d)
    return sorted(set(dates))


def _parse_waschabo_lines(page3: str, year: int) -> dict[str, list[date]]:
    out: dict[str, list[date]] = {"Bronze": [], "Silber": [], "Gold": []}
    for tier in ("Bronze", "Silber", "Gold"):
        m = re.search(rf"{tier}\s*\((\d+)x\)\s*([^\n]+)", page3, re.I)
        if not m:
            continue
        chunk = m.group(2)
        stop = re.search(r"(?:Brennbares|Waschabo|Bronze|Silber|Gold)", chunk, re.I)
        if stop:
            chunk = chunk[: stop.start()]
        out[tier] = _parse_waschabo_dates_chunk(chunk, year)
    return out


def parse_entsorgungsplan_pdf(pdf_bytes: bytes) -> ParsedPlan:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        if len(pdf.pages) < 3:
            raise ValueError("PDF has fewer than 3 pages")
        page3 = pdf.pages[2].extract_text() or ""

    year = _infer_year_from_text(page3)
    return ParsedPlan(
        plan_year=year,
        pdf_text_page3=page3,
        hauskehricht_dates=_parse_hauskehricht(page3, year),
        gruengut_dates=_parse_gruengut(page3, year),
        waschabo=_parse_waschabo_lines(page3, year),
    )
