import re

from utils.html_utils import (
    parse_html, remove_unwanted_tags, remove_comments,
    clean_attributes, is_empty_element
)
from utils.text_utils import convert_html_to_markdown, clean_markdown_text
from utils.file_utils import extract_url_from_html
from cleaners.content_analyzer import calculate_content_score
from cleaners.boilerplate_detector import is_likely_boilerplate
from cleaners.structured_data import extract_structured_data
from config.settings import (
    MIN_CONTENT_SCORE,
    MAX_CONTENT_CHARS,
    REUTERS_MAX_CONTENT_CHARS,
    REUTERS_MIN_CONTENT_SCORE,
)
from config.logging_config import get_logger

logger = get_logger(__name__)


def _truncate_output(text, max_chars):
    if max_chars and len(text) > max_chars:
        logger.info(f"Truncating cleaned content from {len(text)} to {max_chars} characters")
        return text[:max_chars] + "\n\n[content truncated]"
    return text


def _html_fragment_to_markdown(fragment, max_chars=None, plain_links=False):
    if fragment is None:
        return ""
    clean_attributes(fragment)
    markdown_output = convert_html_to_markdown(fragment.decode_contents())
    final_output = clean_markdown_text(markdown_output)
    if plain_links:
        final_output = re.sub(r"\[([^\]]+)\]\(<[^>]+>\)", r"\1", final_output)
        final_output = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", final_output)
    return _truncate_output(final_output, max_chars)


def _build_article_from_parts(soup, parts, max_chars=None):
    container = soup.new_tag("article")
    seen = set()
    for part in parts:
        if part is None or id(part) in seen:
            continue
        seen.add(id(part))
        container.append(part.extract() if part.parent else part)
    if not container.contents:
        return ""
    return _html_fragment_to_markdown(container, max_chars)


def _materialize_fin_streamers(root):
    for el in root.find_all("fin-streamer"):
        val = (el.get("value") or el.get_text(strip=True) or "").strip()
        if val:
            el.replace_with(val)
        else:
            el.decompose()


def _select_root(soup, selectors):
    for selector in selectors:
        el = soup.select_one(selector)
        if el and el.get_text(strip=True):
            return el
    return None


def _decompose_selectors(root, selectors):
    for selector in selectors:
        for el in root.select(selector):
            el.decompose()


def _prepare_content_fragment(soup, root, noise_selectors=(), preprocess=None):
    if root is None:
        return None
    fragment = soup.new_tag("article")
    fragment.append(root.extract() if root.parent else root)
    remove_unwanted_tags(fragment)
    remove_comments(fragment)
    if preprocess:
        preprocess(fragment)
    _decompose_selectors(fragment, noise_selectors)
    return fragment


def _clean_from_root(soup, root_selectors, noise_selectors=(), preprocess=None,
                      max_chars=None, min_chars=400, fallback_fn=None):
    root = _select_root(soup, root_selectors)
    fragment = _prepare_content_fragment(soup, root, noise_selectors, preprocess)
    if fragment and fragment.get_text(strip=True):
        result = _html_fragment_to_markdown(fragment, max_chars)
        if len(result) >= min_chars:
            return result
    if fallback_fn:
        return fallback_fn(soup)
    return ""


_AMAZON_NOISE = (
    "[id^='CardInstance']",
    "#purchase-sims-feature_div",
    "#sponsoredProducts2_feature_div",
    "#reviewsMedley",
    "#ask-dp-search_feature_div",
    "#comparison_feature_div",
    "#sp_instrumentation_wrapper",
    "#rhf",
    "#similarities_feature_div",
    "#sims-consolidated-1_feature_div",
    "#sims-consolidated-2_feature_div",
    "#sims-consolidated-3_feature_div",
    "#sims-consolidated-4_feature_div",
    "#sims-consolidated-5_feature_div",
    "#sims-consolidated-6_feature_div",
)

_CARS_NOISE = (
    "[data-qa='similar-vehicles']",
    ".similar-vehicles",
    "[id^='lead-form-']",
    ".phx-connected.phx-modal",
    "#sticky-header",
    ".global-footer",
    ".site-header",
    "div.all_features-section",
)

_YAHOO_NOISE = (
    "canvas",
    "[data-testid='ad-container']",
    ".footer",
    ".partner-panel",
)

_REUTERS_NOISE = (
    '[data-testid="promo-box"]',
    '[data-testid="NativeAd"]',
)


def _reuters_utc_from_iso(iso):
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S UTC")
    except ValueError:
        return None, None


def _reuters_clone_text(soup, text):
    p = soup.new_tag("p")
    p.string = text
    return p


def _reuters_inject_times(fragment, soup):
    insert_at = 0

    author = soup.find(attrs={"data-testid": "AuthorName"})
    if author:
        author_text = author.get_text(" ", strip=True)
        if author_text:
            fragment.insert(insert_at, _reuters_clone_text(soup, author_text))
            insert_at += 1

    pub_meta = soup.find("meta", attrs={"name": "article:published_time"})
    if pub_meta and pub_meta.get("content"):
        iso = pub_meta["content"]
        pub_date, pub_time = _reuters_utc_from_iso(iso)
        time_el = soup.new_tag("time")
        time_el["datetime"] = iso
        if pub_date and pub_time:
            time_el.string = f"{pub_date} {pub_time}"
        else:
            time_el.string = iso
        pub_p = soup.new_tag("p")
        pub_p.append(time_el)
        fragment.insert(insert_at, pub_p)
        insert_at += 1

    mod_meta = soup.find("meta", attrs={"name": "article:modified_time"})
    if mod_meta and mod_meta.get("content"):
        iso = mod_meta["content"]
        _, mod_time = _reuters_utc_from_iso(iso)
        time_el = soup.new_tag("time")
        time_el["datetime"] = iso
        time_el.string = mod_time or iso
        mod_p = soup.new_tag("p")
        mod_p.append(time_el)
        fragment.insert(insert_at, mod_p)


def _reuters_preprocess(fragment, soup):
    _reuters_inject_times(fragment, soup)
    for el in fragment.find_all(attrs={"data-testid": "Body"}):
        if "Trust Principles" in el.get_text(" ", strip=True):
            el.decompose()


def _is_reuters_source(filename):
    if "reuters" in str(filename).lower():
        return True
    url = extract_url_from_html(filename)
    return "reuters" in (url or "").lower()


def _reuters_tail_tags(soup):
    article = soup.find(attrs={"data-testid": "ArticleBody"})
    if not article:
        return set()
    return set(article.find_all_next(True))


def _is_wikipedia_source(filename):
    if "wikipedia" in str(filename).lower():
        return True
    url = extract_url_from_html(filename)
    return "wikipedia.org" in (url or "").lower()


def _wikipedia_clean_text(text):
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _wikipedia_first_substantial_paragraph(content):
    for paragraph in content.find_all("p", recursive=True):
        text = _wikipedia_clean_text(paragraph.get_text(" ", strip=True))
        if len(text) < 40:
            continue
        if text.lower().startswith("coordinates:"):
            continue
        if text.startswith("This article"):
            continue
        return paragraph
    return None


def _wikipedia_reorder_content(content):
    infobox = content.select_one("table.infobox")
    first_p = _wikipedia_first_substantial_paragraph(content)
    if not infobox or not first_p:
        return

    for tag in content.find_all(["p", "table"], recursive=True):
        if tag is first_p:
            return
        if tag is infobox:
            first_p.extract()
            infobox.insert_before(first_p)
            return


def _wikipedia_unwrap_links(content):
    for anchor in content.find_all("a"):
        anchor.replace_with(anchor.get_text(" ", strip=True))


def _wikipedia_remove_noise(content):
    for selector in (
        ".mw-jump-link",
        ".mw-editsection",
        ".shortdescription",
        ".mw-subjectpageheader",
        "style",
        ".navbox",
        ".reflist",
        ".references",
        ".metadata",
        ".side-box",
        ".hatnote",
        ".ambox",
        ".sistersitebox",
    ):
        for el in content.select(selector):
            el.decompose()


def _wikipedia_build_toc(soup):
    toc_root = soup.select_one("#toc") or soup.select_one("#mw-panel-toc")
    if not toc_root:
        return None
    nav = soup.new_tag("nav")
    ul = soup.new_tag("ul")
    seen = set()
    for link in toc_root.select("a"):
        text = _wikipedia_clean_text(link.get_text(" ", strip=True))
        if not text or text.lower() in {"(top)", "top"}:
            continue
        if text in seen:
            continue
        seen.add(text)
        li = soup.new_tag("li")
        li.string = text
        ul.append(li)
    if not ul.find("li"):
        return None
    nav.append(ul)
    return nav


def _wikipedia_simplify_infobox(infobox, soup):
    for tag in infobox.find_all(["img", "style", "link", "svg", "figure", "map"]):
        tag.decompose()
    rows = []
    for tr in infobox.select("tr"):
        th, td = tr.find("th"), tr.find("td")
        if not th or not td:
            continue
        key = _wikipedia_clean_text(th.get_text(" ", strip=True))
        val = _wikipedia_clean_text(td.get_text(" ", strip=True))
        if not key or not val or len(val) > 180:
            continue
        lower = f"{key} {val}".lower()
        if any(x in lower for x in ("show map", "show all", "coordinates:", "wikimedia")):
            continue
        rows.append(f"{key}: {val}")
    replacement = soup.new_tag("div")
    for row in rows[:30]:
        p = soup.new_tag("p")
        p.string = row
        replacement.append(p)
    infobox.replace_with(replacement)


def _strip_wikipedia_chrome(soup):
    for selector in (
        "#mw-navigation",
        "#mw-panel",
        ".vector-header-container",
        ".vector-page-toolbar",
        "#mw-page-base",
        "#footer",
    ):
        for el in soup.select(selector):
            el.decompose()


def _wikipedia_content_root(soup):
    return soup.select_one("#mw-content-text") or soup.select_one("#bodyContent")


def _clean_wikipedia_html(soup):
    lastmod_el = soup.select_one("#footer-info-lastmod")
    lastmod_text = (
        _wikipedia_clean_text(lastmod_el.get_text(" ", strip=True)) if lastmod_el else None
    )
    toc = _wikipedia_build_toc(soup)

    _strip_wikipedia_chrome(soup)
    remove_unwanted_tags(soup)
    remove_comments(soup)

    content = _wikipedia_content_root(soup)
    if not content:
        logger.warning("Wikipedia content root not found")
        return ""

    insert_at = 0
    heading = soup.select_one("#firstHeading")
    if heading:
        h1 = soup.new_tag("h1")
        h1.string = heading.get_text(strip=True)
        content.insert(insert_at, h1)
        insert_at += 1

    if toc:
        content.insert(insert_at, toc)

    infobox = content.select_one("table.infobox")
    if infobox:
        _wikipedia_simplify_infobox(infobox, soup)

    _wikipedia_remove_noise(content)
    _wikipedia_unwrap_links(content)
    for p in content.find_all("p"):
        text = p.get_text(" ", strip=True)
        if text.startswith("Retrieved from") or text.startswith("This page was last edited"):
            if text.startswith("Retrieved from"):
                p.decompose()
    _wikipedia_reorder_content(content)

    if lastmod_text:
        foot = soup.new_tag("p")
        foot.string = lastmod_text
        content.append(foot)

    return _html_fragment_to_markdown(content, MAX_CONTENT_CHARS, plain_links=True)


def _strip_yahoo_finance_chrome(soup):
    for selector in (
        "#ybar",
        "header",
        "footer",
        ".footer",
        "[data-testid='ad-container']",
    ):
        for el in soup.select(selector):
            el.decompose()


def _yahoo_strip_overnight_prices(soup):
    """Remove overnight/extended-hours quote blocks so LLM uses regular close prices."""
    for test_id in (
        "qsp-overnight-price",
        "qsp-overnight-price-change",
        "qsp-overnight-price-change-percent",
        "quote-sticky-hdr",
        "quote-nav-bar",
    ):
        for el in soup.find_all(attrs={"data-testid": test_id}):
            el.decompose()
    for section in soup.select('section.secondary[data-testid="price-statistic"]'):
        section.decompose()


def _yahoo_primary_quote_lines(soup):
    lines = []
    for test_id, label in (
        ("qsp-price", "Current stock price"),
        ("qsp-price-change", "Price change (dollars)"),
        ("qsp-price-change-percent", "Percentage change"),
    ):
        el = soup.find(attrs={"data-testid": test_id})
        if el:
            text = el.get_text(" ", strip=True)
            if text:
                lines.append(f"{label}: {text}")
    return lines


def _yahoo_finance_sections(soup):
    sections = []
    seen = set()

    hdr = soup.find("section", attrs={"data-testid": "quote-hdr"})
    if hdr:
        sections.append(hdr)
        seen.add(id(hdr))

    stats_root = soup.find(attrs={"data-testid": "quote-statistics"})
    if stats_root:
        section = stats_root.find_parent("section") or stats_root
        if id(section) not in seen:
            sections.append(section)
            seen.add(id(section))

    if sections:
        return sections

    for test_id in ("quote-title", "quote-price", "quote-statistics"):
        el = soup.find(attrs={"data-testid": test_id})
        if el and id(el) not in seen:
            sections.append(el)
            seen.add(id(el))

    return sections


def _clean_yahoo_finance_html(soup):
    remove_unwanted_tags(soup)
    remove_comments(soup)
    _strip_yahoo_finance_chrome(soup)
    _yahoo_strip_overnight_prices(soup)
    quote_lines = _yahoo_primary_quote_lines(soup)
    result = _clean_from_root(
        soup,
        root_selectors=("main", "section.mainContent", "section.main"),
        noise_selectors=_YAHOO_NOISE,
        preprocess=_materialize_fin_streamers,
        max_chars=MAX_CONTENT_CHARS,
        fallback_fn=_clean_yahoo_finance_html_fallback,
    )
    if quote_lines:
        header = "\n".join(quote_lines) + "\n\n"
        result = header + result if result else header
    return result


def _clean_yahoo_finance_html_fallback(soup):
    _yahoo_strip_overnight_prices(soup)
    quote_lines = _yahoo_primary_quote_lines(soup)
    sections = _yahoo_finance_sections(soup)
    if not sections:
        return "\n".join(quote_lines) if quote_lines else ""
    for section in sections:
        _materialize_fin_streamers(section)
    body = _build_article_from_parts(soup, sections, MAX_CONTENT_CHARS)
    if quote_lines:
        header = "\n".join(quote_lines) + "\n\n"
        body = header + body if body else header
    return body


def _is_yahoo_finance_source(filename):
    name = str(filename).lower()
    if "yahoo" in name and "finance" in name:
        return True
    url = extract_url_from_html(filename)
    return "finance.yahoo.com" in (url or "").lower()


def _is_cars_source(filename):
    name = str(filename).lower()
    if "cars.com" in name:
        return True
    url = extract_url_from_html(filename)
    return "cars.com" in (url or "").lower()


def _is_amazon_source(filename):
    name = str(filename).lower()
    if "amazon.com" in name or " _ amazon.html" in name:
        return True
    url = extract_url_from_html(filename)
    return "amazon.com" in (url or "").lower() or "/dp/" in (url or "")


def _is_upwork_source(filename):
    name = str(filename).lower()
    if "upwork.com" in name:
        return True
    url = extract_url_from_html(filename)
    return "upwork.com" in (url or "").lower()


def _cars_listing_parts(soup):
    parts = []
    seen = set()

    def add(el):
        if el is not None and id(el) not in seen:
            seen.add(id(el))
            parts.append(el)

    title = soup.select_one("h1.listing-title") or soup.select_one("h1.sticky-header-listing-title")
    if title:
        add(title.find_parent("div", class_="title-section") or title.parent)

    add(soup.select_one("div.price-section"))

    for section in soup.select("section.seller-info"):
        add(section)
        break

    for dl in soup.select("dl.fancy-description-list"):
        if dl.find_parent(attrs={"data-qa": "similar-vehicles"}):
            continue
        add(dl)
        break

    for section in soup.select("section.features-section"):
        add(section)
        break

    return parts


def _clean_cars_html(soup):
    remove_unwanted_tags(soup)
    remove_comments(soup)
    parts_result = _clean_cars_html_fallback(soup)
    if len(parts_result) >= 1500:
        return parts_result
    return _clean_from_root(
        soup,
        root_selectors=("#main-content", "main"),
        noise_selectors=_CARS_NOISE,
        max_chars=25000,
        fallback_fn=_clean_cars_html_fallback,
    )


def _cars_trim_features(container, soup, max_items=25):
    for section in container.select("section.features-section, div.all_features-section"):
        items = []
        for el in section.select("li, dt, dd, p"):
            text = el.get_text(" ", strip=True)
            if text and len(text) > 2:
                items.append(text[:120])
        if not items:
            continue
        ul = soup.new_tag("ul")
        for text in items[:max_items]:
            li = soup.new_tag("li")
            li.string = text
            ul.append(li)
        section.replace_with(ul)


def _clean_cars_html_fallback(soup):
    parts = _cars_listing_parts(soup)
    if not parts:
        logger.warning("Cars.com listing sections not found")
        return ""
    container = soup.new_tag("article")
    seen = set()
    for part in parts:
        if part is None or id(part) in seen:
            continue
        seen.add(id(part))
        container.append(part.extract() if part.parent else part)
    _cars_trim_features(container, soup)
    return _html_fragment_to_markdown(container, 25000)


def _clean_amazon_html(soup):
    remove_unwanted_tags(soup)
    remove_comments(soup)
    parts_result = _clean_amazon_html_fallback(soup)
    if len(parts_result) >= 2000:
        return parts_result
    return _clean_from_root(
        soup,
        root_selectors=("#dp-container", "#dp", "#ppd"),
        noise_selectors=_AMAZON_NOISE,
        max_chars=MAX_CONTENT_CHARS,
        fallback_fn=_clean_amazon_html_fallback,
    )


def _clean_amazon_html_fallback(soup):
    parts = _amazon_product_parts(soup)
    if not parts:
        logger.warning("Amazon product sections not found")
        return ""
    return _build_article_from_parts(soup, parts, MAX_CONTENT_CHARS)


def _clean_reuters_html(soup):
    remove_unwanted_tags(soup)
    remove_comments(soup)

    def _fallback(s):
        parts = _reuters_article_parts(s)
        if not parts:
            logger.warning("Reuters article sections not found")
            return ""
        return _build_article_from_parts(s, parts, REUTERS_MAX_CONTENT_CHARS)

    def _preprocess(fragment):
        _reuters_preprocess(fragment, soup)

    return _clean_from_root(
        soup,
        root_selectors=("main", "article", '[data-testid="ArticleBody"]'),
        noise_selectors=_REUTERS_NOISE,
        preprocess=_preprocess,
        max_chars=REUTERS_MAX_CONTENT_CHARS,
        min_chars=200,
        fallback_fn=_fallback,
    )


def _clean_upwork_html(soup):
    remove_unwanted_tags(soup)
    remove_comments(soup)
    return _clean_upwork_html_fallback(soup)


def _clean_upwork_html_fallback(soup):
    parts = _upwork_profile_parts(soup)
    if not parts:
        logger.warning("Upwork profile sections not found")
        return ""
    container = soup.new_tag("article")
    seen = set()
    for part in parts:
        if part is None or id(part) in seen:
            continue
        seen.add(id(part))
        container.append(part.extract() if part.parent else part)
    if not container.contents:
        return ""
    _upwork_flatten_stats(container, soup)
    return _html_fragment_to_markdown(container, MAX_CONTENT_CHARS)


def _upwork_flatten_stats(container, soup):
    stats = container.select_one(".cfe-ui-profile-summary-stats")
    if not stats:
        return
    block = soup.new_tag("div")
    for col in stats.select(".col-compact"):
        label_el = col.select_one(".text-base-sm")
        amount_el = col.select_one(".stat-amount")
        if not label_el or not amount_el:
            continue
        label = label_el.get_text(" ", strip=True)
        amount = amount_el.get_text(" ", strip=True)
        if not label or not amount:
            continue
        lower = label.lower()
        if "total jobs" not in lower and "total hours" not in lower:
            continue
        p = soup.new_tag("p")
        p.string = f"{label} {amount}"
        block.append(p)
    if block.contents:
        stats.replace_with(block)


def _upwork_profile_parts(soup):
    parts = []
    seen = set()

    def add(el):
        if el is not None and id(el) not in seen:
            seen.add(id(el))
            parts.append(el)

    for h2 in soup.find_all("h2"):
        name = h2.get_text(" ", strip=True)
        if name and name.lower() != "this site uses cookies":
            add(h2.find_parent("section") or h2.find_parent("div", class_="air3-card-section") or h2)
            break

    add(soup.select_one(".cfe-ui-profile-summary"))
    add(soup.select_one(".cfe-ui-profile-summary-stats"))

    for section in soup.select("section.air3-card-section"):
        classes = " ".join(section.get("class") or [])
        if "work-history" in classes:
            continue
        if section.select_one(".cfe-ui-profile-summary-stats"):
            add(section)
        elif section.select_one(".air3-line-clamp") and not section.select_one(".work-history"):
            add(section)

    return parts


def _amazon_product_parts(soup):
    parts = []
    seen = set()

    def add(el):
        if el is not None and id(el) not in seen:
            seen.add(id(el))
            parts.append(el)

    for elem_id in (
        "titleSection",
        "averageCustomerReviews_feature_div",
        "bylineInfo_feature_div",
        "corePriceDisplay_desktop_feature_div",
        "corePrice_desktop",
        "corePrice_feature_div",
        "tp-inline-twister-dim-values-container",
        "apex_desktop",
        "buybox",
        "feature-bullets",
        "detailBullets_feature_div",
        "productDetails_feature_div",
        "productDetails_techSpec_section_1",
        "prodDetails",
        "productDescription_feature_div",
    ):
        add(soup.find(id=elem_id))

    add(soup.find(id="pqv-ratings"))

    if not parts:
        add(soup.find(id="centerCol") or soup.find(id="ppd"))

    return parts


def _reuters_article_parts(soup):
    parts = []

    headline = soup.find("h1", attrs={"data-testid": "Heading"})
    if headline:
        parts.append(headline)

    author = soup.find(attrs={"data-testid": "AuthorName"})
    if author:
        parts.append(author)

    pub_meta = soup.find("meta", attrs={"name": "article:published_time"})
    if pub_meta and pub_meta.get("content"):
        time_el = soup.new_tag("time")
        time_el["datetime"] = pub_meta["content"]
        time_el.string = pub_meta["content"]
        pub_p = soup.new_tag("p")
        pub_p.append(time_el)
        parts.append(pub_p)

    mod_meta = soup.find("meta", attrs={"name": "article:modified_time"})
    if mod_meta and mod_meta.get("content"):
        time_el = soup.new_tag("time")
        time_el["datetime"] = mod_meta["content"]
        time_el.string = mod_meta["content"]
        mod_p = soup.new_tag("p")
        mod_p.append(time_el)
        parts.append(mod_p)

    body = soup.find(attrs={"data-testid": "ArticleBody"})
    if body:
        body_wrap = soup.new_tag("div")
        char_count = 0
        for el in body.find_all(attrs={"data-testid": True}):
            testid = el.get("data-testid", "")
            if testid in {"promo-box", "Link", "NewTabSymbol"}:
                continue
            if testid == "Body" and "Trust Principles" in el.get_text(" ", strip=True):
                continue
            if testid not in {"Body", "paragraph-0"} and not testid.startswith("paragraph-"):
                continue
            text = el.get_text(" ", strip=True)
            if not text:
                continue
            body_wrap.append(el.extract())
            char_count += len(text)
            if char_count >= 50000:
                break
        if body_wrap.contents:
            parts.append(body_wrap)
            got_body = True
        else:
            got_body = False
    else:
        got_body = False

    if not got_body:
        from cleaners.structured_data import _extract_embedded_paragraphs
        paragraphs = _extract_embedded_paragraphs(soup, max_chars=50000)
        if paragraphs:
            body_wrap = soup.new_tag("div")
            for text in paragraphs[:20]:
                p = soup.new_tag("p")
                p.string = text
                body_wrap.append(p)
            parts.append(body_wrap)

    return parts


def clean_html_for_llm(filename, preserve_classes=None, preserve_ids=None,
                      min_content_score=MIN_CONTENT_SCORE):

    preserve_classes = preserve_classes or set()
    preserve_ids = preserve_ids or set()

    logger.info(f"Starting HTML cleaning for file: {filename}")

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            html_content = f.read()
        logger.info(f"Successfully read HTML file. Content length: {len(html_content)} characters")
    except Exception as e:
        logger.error(f"Error reading file {filename}: {e}")
        raise

    soup = parse_html(html_content)
    is_reuters = _is_reuters_source(filename)
    is_wikipedia = _is_wikipedia_source(filename)
    is_yahoo_finance = _is_yahoo_finance_source(filename)
    is_cars = _is_cars_source(filename)
    is_amazon = _is_amazon_source(filename)
    is_upwork = _is_upwork_source(filename)

    if is_wikipedia:
        result = _clean_wikipedia_html(soup)
        logger.info(f"HTML cleaning completed for {filename}")
        return result

    if is_yahoo_finance:
        result = _clean_yahoo_finance_html(soup)
        logger.info(f"HTML cleaning completed for {filename}")
        return result

    if is_reuters:
        result = _clean_reuters_html(soup)
        logger.info(f"HTML cleaning completed for {filename}")
        return result

    if is_cars:
        result = _clean_cars_html(soup)
        logger.info(f"HTML cleaning completed for {filename}")
        return result

    if is_amazon:
        result = _clean_amazon_html(soup)
        logger.info(f"HTML cleaning completed for {filename}")
        return result

    if is_upwork:
        result = _clean_upwork_html(soup)
        logger.info(f"HTML cleaning completed for {filename}")
        return result

    reuters_tail = _reuters_tail_tags(soup) if is_reuters else set()
    score_threshold = REUTERS_MIN_CONTENT_SCORE if is_reuters else min_content_score

    structured_data = extract_structured_data(soup)

    remove_unwanted_tags(soup)
    remove_comments(soup)

    elements_to_remove = []

    for tag in soup.find_all(True):
        if tag in elements_to_remove:
            continue

        tag_classes = set(tag.get('class', []))
        tag_id = tag.get('id', '')

        if tag_classes.intersection(preserve_classes) or tag_id in preserve_ids:
            continue

        if is_reuters and tag in reuters_tail:
            continue

        is_boilerplate, _ = is_likely_boilerplate(tag)

        if is_boilerplate:
            score, _ = calculate_content_score(tag)
            if score < score_threshold:
                elements_to_remove.append(tag)
        elif is_empty_element(tag):
            elements_to_remove.append(tag)

    for tag in elements_to_remove:
        if tag.parent:
            tag.decompose()

    clean_attributes(soup)

    clean_html = str(soup.body) if soup.body else str(soup)
    markdown_output = convert_html_to_markdown(clean_html)
    final_output = clean_markdown_text(markdown_output)

    if structured_data:
        final_output = f"{structured_data}\n\n{final_output}"

    max_chars = REUTERS_MAX_CONTENT_CHARS if is_reuters else MAX_CONTENT_CHARS
    if max_chars and len(final_output) > max_chars:
        logger.info(f"Truncating cleaned content from {len(final_output)} "
                    f"to {max_chars} characters")
        final_output = final_output[:max_chars] + "\n\n[content truncated]"

    logger.info(f"HTML cleaning completed for {filename}")
    return final_output
