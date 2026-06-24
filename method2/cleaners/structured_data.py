import json
import re

from config.logging_config import get_logger

logger = get_logger(__name__)


ARTICLE_TYPES = {
    "Article", "NewsArticle", "ReportageNewsArticle", "BlogPosting",
    "LiveBlogPosting", "OpinionNewsArticle", "AnalysisNewsArticle",
    "BackgroundNewsArticle", "ReviewNewsArticle",
}


_PARAGRAPH_RE = re.compile(r'\{"content":"((?:[^"\\]|\\.)*)","type":"paragraph"\}')


def _script_text(tag):

    return tag.string or tag.get_text()


def _author_names(author):

    if not author:
        return []
    if isinstance(author, (str, dict)):
        author = [author]
    names = []
    for entry in author:
        if isinstance(entry, dict) and entry.get("name"):
            names.append(str(entry["name"]).strip())
        elif isinstance(entry, str) and entry.strip():
            names.append(entry.strip())
    return names


def _iter_jsonld_objects(soup):

    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = _script_text(tag)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        stack = [data]
        while stack:
            current = stack.pop()
            if isinstance(current, list):
                stack.extend(current)
            elif isinstance(current, dict):
                yield current
                graph = current.get("@graph")
                if isinstance(graph, list):
                    stack.extend(graph)


def _find_article_jsonld(soup):

    for obj in _iter_jsonld_objects(soup):
        types = obj.get("@type")
        types = types if isinstance(types, list) else [types]
        if any(t in ARTICLE_TYPES for t in types if t):
            return obj
    return None


def _collapse_ws(text):

    return " ".join(text.split()) if text else ""


def _extract_quote_data(soup):


    title_el = soup.find(attrs={"data-testid": "quote-title"})
    price_el = soup.find(attrs={"data-testid": "quote-price"})
    if not title_el and not price_el:
        return []

    lines = []
    if title_el:
        lines.append(f"Name: {_collapse_ws(title_el.get_text(' ', strip=True))}")
    if price_el:


        lines.append(
            f"Price / change: {_collapse_ws(price_el.get_text(' ', strip=True))}"
        )

    stats_el = soup.find(attrs={"data-testid": "quote-statistics"})
    if stats_el:
        stat_lines = []
        for li in stats_el.find_all("li"):
            text = _collapse_ws(li.get_text(" ", strip=True))
            if text:
                stat_lines.append(f"- {text}")
        if stat_lines:
            lines += ["", "Key statistics:"] + stat_lines

    return lines


def _main_quote_symbol(soup):
    title_el = soup.find(attrs={"data-testid": "quote-title"})
    if not title_el:
        return None
    match = re.search(r'\(([^)]+)\)', title_el.get_text(" ", strip=True))
    return match.group(1).strip() if match else None


def _main_symbol_streamers(soup):
    symbol = _main_quote_symbol(soup)
    out = {}
    for el in soup.find_all("fin-streamer"):
        if symbol and el.get("data-symbol") != symbol:
            continue
        field = el.get("data-field")
        val = el.get_text(strip=True)
        if field and val:
            out[field] = val
    return out


def _stat_value(stats_el, pattern):
    if not stats_el:
        return None
    for li in stats_el.find_all("li"):
        text = _collapse_ws(li.get_text(" ", strip=True))
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


_MARKET_CAP_RE = re.compile(r"Market Cap(?:\s*\([^)]*\))?\s*(.+)", re.I)
_WEEK_RANGE_RE = re.compile(r"52 Week Range\s*(.+)", re.I)


def extract_yahoo_finance_data(soup):
    title_el = soup.find(attrs={"data-testid": "quote-title"})
    price_el = soup.find(attrs={"data-testid": "quote-price"})
    if not title_el and not price_el:
        return ""

    lines = []
    if title_el:
        lines.append(
            f"company_name: {_collapse_ws(title_el.get_text(' ', strip=True))}"
        )

    streamers = _main_symbol_streamers(soup)
    price = streamers.get("regularMarketPrice")
    change = streamers.get("regularMarketChange")
    pct = streamers.get("regularMarketChangePercent")

    if not price and price_el:
        match = re.search(r"([\d,.]+)", price_el.get_text(" ", strip=True))
        if match:
            price = match.group(1)

    if not change and price_el:
        match = re.search(r"([\d,.]+)\s+(-?[\d,.]+)\s+\((-?[\d,.]+%)\)", price_el.get_text(" ", strip=True))
        if match:
            price = price or match.group(1)
            change = match.group(2)
            pct = match.group(3)

    if price:
        lines.append(f"current_stock_price: {price}")
    if change:
        lines.append(f"price_change: {change}")
    if pct:
        lines.append(f"percentage_change: {pct}")

    stats_el = soup.find(attrs={"data-testid": "quote-statistics"})
    market_cap = _stat_value(stats_el, _MARKET_CAP_RE)
    week_range = _stat_value(stats_el, _WEEK_RANGE_RE)
    if market_cap:
        lines.append(f"market_capitalization: {market_cap}")
    if week_range:
        lines.append(f"fifty_two_week_price_range: {week_range}")

    if stats_el:
        stat_lines = []
        for li in stats_el.find_all("li"):
            text = _collapse_ws(li.get_text(" ", strip=True))
            if text:
                stat_lines.append(f"- {text}")
        if stat_lines:
            lines += ["", "Key statistics:"] + stat_lines

    if lines:
        logger.info("Extracted Yahoo Finance quote data")
    return "\n".join(lines)


def _extract_other_quotes_on_page(soup, max_tickers=10):


    main_symbol = _main_quote_symbol(soup)
    by_symbol = {}
    for el in soup.find_all("fin-streamer"):
        sym = el.get("data-symbol")
        if not sym or sym == main_symbol:
            continue
        field = el.get("data-field")
        if field not in (
            "regularMarketPrice", "regularMarketChange", "regularMarketChangePercent"
        ):
            continue
        val = el.get_text(strip=True)
        if val:
            by_symbol.setdefault(sym, {})[field] = val

    lines = []
    for sym in list(by_symbol.keys())[:max_tickers]:
        data = by_symbol[sym]
        price = data.get("regularMarketPrice", "")
        change = data.get("regularMarketChange", "")
        pct = data.get("regularMarketChangePercent", "")
        parts = [sym, price]
        if change:
            parts.append(change)
        if pct:
            parts.append(f"({pct})")
        lines.append("- " + " ".join(p for p in parts if p))

    if not lines:
        return []
    return ["", "Other quotes on this page:"] + lines


def _extract_embedded_paragraphs(soup, max_chars=12000):

    paragraphs = []
    seen = set()
    total = 0
    for tag in soup.find_all("script"):
        raw = _script_text(tag)
        if not raw or '"type":"paragraph"' not in raw:
            continue
        for match in _PARAGRAPH_RE.finditer(raw):
            try:

                text = json.loads('"' + match.group(1) + '"').strip()
            except (ValueError, TypeError):
                continue
            if len(text) < 2 or text in seen:
                continue
            seen.add(text)
            paragraphs.append(text)
            total += len(text)
        if paragraphs and total >= max_chars:
            break
    return paragraphs


def extract_structured_data(soup):


    try:


        quote_lines = _extract_quote_data(soup)
        if quote_lines:
            quote_lines += _extract_other_quotes_on_page(soup)
            logger.info("Extracted structured quote data (finance page)")
            return "\n".join(quote_lines)

        lines = []
        article = _find_article_jsonld(soup)

        if article:
            if article.get("headline"):
                lines.append(f"Headline: {str(article['headline']).strip()}")
            names = _author_names(article.get("author"))
            if names:
                lines.append("Author: " + ", ".join(names))
            if article.get("datePublished"):
                lines.append(f"Published: {str(article['datePublished']).strip()}")
            if article.get("dateModified"):
                lines.append(f"Modified: {str(article['dateModified']).strip()}")
            if article.get("description"):
                lines.append(f"Description: {str(article['description']).strip()}")


        body = article.get("articleBody") if article else None
        if body and str(body).strip():
            lines += ["", "Article body:", str(body).strip()]
        else:
            paragraphs = _extract_embedded_paragraphs(soup)
            if paragraphs:
                lines += ["", "Article body:"] + paragraphs

        if not lines:
            return ""

        logger.info("Extracted structured article data (JSON-LD / embedded state)")
        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Structured-data extraction failed, skipping: {e}")
        return ""
