import asyncio
import logging
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

logger = logging.getLogger(__name__)

MAX_PAGES = 15  # Safety cap to avoid infinite pagination loops

BROWSER_CONFIG = BrowserConfig(
    headless=True,
    browser_type="chromium",
    viewport_width=1280,
    viewport_height=800,
)

# CSS selectors to try when the initial crawl returns little/no content.
# These target common job listing containers across various career sites.
FALLBACK_SELECTORS = [
    ".friday-jobs-grid",
    ".job-list",
    ".jobs-list",
    ".careers-list",
    "[class*='job-item']",
    "[class*='job-listing']",
    "[class*='opening']",
    "main",
    "#content",
]

MIN_MARKDOWN_LENGTH = 50  # Below this, try fallback selectors


def _get_markdown(result) -> str:
    """Extract markdown from a crawl result, preferring fit_markdown over raw."""
    if not result.success or not result.markdown:
        return ""
    # fit_markdown strips boilerplate (nav, footer, ads) automatically
    fit = getattr(result.markdown, "fit_markdown", None)
    if fit and len(fit.strip()) > MIN_MARKDOWN_LENGTH:
        return fit
    return result.markdown.raw_markdown or ""


async def _try_fallback_selectors(
    crawler: AsyncWebCrawler, url: str, name: str
) -> str:
    """Try fallback CSS selectors when initial crawl returns little content."""
    logger.info(
        f"Low content for {name}, trying fallback selectors..."
    )
    for selector in FALLBACK_SELECTORS:
        fallback_config = CrawlerRunConfig(
            wait_until="domcontentloaded",
            page_timeout=30000,
            css_selector=selector,
        )
        fb_result = await crawler.arun(url=url, config=fallback_config)
        fb_md = _get_markdown(fb_result)
        if len(fb_md.strip()) > MIN_MARKDOWN_LENGTH:
            logger.info(
                f"Fallback selector '{selector}' worked for "
                f"{name}: {len(fb_md)} chars"
            )
            return fb_md
    return ""


def _detect_pagination(markdown: str, url: str) -> list[str]:
    """Detect paginated career pages and return URLs for remaining pages.

    Handles two common patterns:
    1. Greenhouse-style: numbered page links like "* 1 * 2 * 3 ..." in the markdown
    2. Generic: "Next" / ">" links with page= query params
    """
    extra_pages: list[str] = []
    parsed = urlparse(url)

    # Pattern 1: Greenhouse boards — numbered pagination markers in markdown
    # Matches sequences like "* 1\n* 2\n* 3" or "[2](/url?page=2)"
    page_nums = re.findall(r"\[(\d+)\]\([^)]*[?&]page=(\d+)[^)]*\)", markdown)
    if page_nums:
        max_page = max(int(num) for _, num in page_nums)
        for page in range(2, min(max_page + 1, MAX_PAGES + 1)):
            extra_pages.append(_set_page_param(url, page))
        if extra_pages:
            logger.info(f"Detected {len(extra_pages)} additional pages via page links")
            return extra_pages

    # Pattern 2: Plain numbered list pagination (e.g. "* 1 * 2 * 3 * ... * 9")
    numbered = re.findall(r"^\s*\*\s+(\d+)\s*$", markdown, re.MULTILINE)
    if len(numbered) >= 2:
        nums = sorted(set(int(n) for n in numbered))
        if nums[0] == 1 and nums[-1] > 1 and nums == list(range(1, nums[-1] + 1)):
            for page in range(2, min(nums[-1] + 1, MAX_PAGES + 1)):
                extra_pages.append(_set_page_param(url, page))
            if extra_pages:
                logger.info(
                    f"Detected {len(extra_pages)} additional pages via numbered markers"
                )
                return extra_pages

    return extra_pages


def _set_page_param(url: str, page: int) -> str:
    """Set or replace the 'page' query parameter in a URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params["page"] = [str(page)]
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


async def _crawl_single_page(
    crawler: AsyncWebCrawler, url: str, company_name: str
) -> str:
    """Crawl one page and return markdown (with fallback selectors)."""
    config = CrawlerRunConfig(
        wait_until="networkidle",
        page_timeout=30000,
        remove_overlay_elements=True,
        scan_full_page=True,
        word_count_threshold=5,
    )

    result = await crawler.arun(url=url, config=config)

    markdown = _get_markdown(result)
    if not result.success:
        logger.warning(
            f"Crawl failed for {company_name}: {result.error_message}"
        )

    if len(markdown.strip()) < MIN_MARKDOWN_LENGTH:
        markdown = await _try_fallback_selectors(
            crawler, url, company_name
        )

    return markdown


async def crawl_career_page(url: str, company_name: str) -> str:
    """Crawl a career page, following pagination if detected."""
    logger.info(f"Crawling {company_name}: {url}")

    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        # Crawl page 1
        first_page = await _crawl_single_page(crawler, url, company_name)

        if not first_page:
            logger.info(f"Crawled {company_name}: 0 chars of markdown")
            return ""

        # Check for pagination
        extra_urls = _detect_pagination(first_page, url)
        if not extra_urls:
            logger.info(
                f"Crawled {company_name}: {len(first_page)} chars of markdown (1 page)"
            )
            return first_page

        # Crawl remaining pages
        all_pages = [first_page]
        for i, page_url in enumerate(extra_urls, start=2):
            logger.info(f"Crawling {company_name} page {i}: {page_url}")
            page_md = await _crawl_single_page(crawler, page_url, company_name)
            if page_md.strip():
                all_pages.append(page_md)
            else:
                logger.info(f"Page {i} returned no content, stopping pagination")
                break
            await asyncio.sleep(1)  # Rate limiting between pages

        combined = "\n\n".join(all_pages)
        logger.info(
            f"Crawled {company_name}: {len(combined)} chars of markdown "
            f"({len(all_pages)} pages)"
        )
        return combined


async def crawl_job_detail(url: str) -> str:
    """Crawl a single job detail page for its full description."""
    config = CrawlerRunConfig(
        wait_until="networkidle",
        page_timeout=20000,
        remove_overlay_elements=True,
        word_count_threshold=5,
    )

    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        result = await crawler.arun(url=url, config=config)

        if not result.success:
            logger.warning(f"Failed to crawl job detail: {url}")
            return ""

        return _get_markdown(result)


async def crawl_many_career_pages(
    urls_and_names: list[tuple[str, str]],
) -> dict[str, str]:
    """Crawl multiple career pages, following pagination where detected.

    Returns a dict mapping company name -> markdown content.
    """
    results = {}

    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        for url, name in urls_and_names:
            logger.info(f"Crawling {name}: {url}")

            # Crawl first page
            first_page = await _crawl_single_page(crawler, url, name)

            if not first_page:
                logger.error(f"No content extracted for {name}")
                results[name] = ""
                await asyncio.sleep(2)
                continue

            # Check for pagination
            extra_urls = _detect_pagination(first_page, url)
            if not extra_urls:
                results[name] = first_page
                logger.info(f"Crawled {name}: {len(first_page)} chars (1 page)")
                await asyncio.sleep(2)
                continue

            # Crawl remaining pages
            all_pages = [first_page]
            for i, page_url in enumerate(extra_urls, start=2):
                logger.info(f"Crawling {name} page {i}: {page_url}")
                page_md = await _crawl_single_page(crawler, page_url, name)
                if page_md.strip():
                    all_pages.append(page_md)
                else:
                    logger.info(f"Page {i} returned no content, stopping pagination")
                    break
                await asyncio.sleep(1)

            combined = "\n\n".join(all_pages)
            results[name] = combined
            logger.info(
                f"Crawled {name}: {len(combined)} chars ({len(all_pages)} pages)"
            )

            # Rate limiting between companies
            await asyncio.sleep(2)

    return results


async def crawl_job_details_batch(
    urls: list[str],
) -> dict[str, str]:
    """Crawl multiple job detail pages. Returns url -> markdown mapping."""
    results = {}

    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        for url in urls:
            config = CrawlerRunConfig(
                wait_until="networkidle",
                page_timeout=20000,
                remove_overlay_elements=True,
                word_count_threshold=5,
            )

            result = await crawler.arun(url=url, config=config)

            if result.success:
                results[url] = _get_markdown(result)
            else:
                logger.warning(f"Failed to crawl detail: {url}")
                results[url] = ""

            await asyncio.sleep(1)

    return results
