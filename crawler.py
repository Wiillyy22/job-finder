import asyncio
import logging

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

logger = logging.getLogger(__name__)

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
        fb_md = (
            fb_result.markdown.raw_markdown
            if fb_result.success and fb_result.markdown
            else ""
        )
        if len(fb_md.strip()) > MIN_MARKDOWN_LENGTH:
            logger.info(
                f"Fallback selector '{selector}' worked for "
                f"{name}: {len(fb_md)} chars"
            )
            return fb_md
    return ""


async def crawl_career_page(url: str, company_name: str) -> str:
    """Crawl a single career page and return its content as markdown."""
    config = CrawlerRunConfig(
        wait_until="networkidle",
        page_timeout=30000,
        remove_overlay_elements=True,
        scan_full_page=True,
        word_count_threshold=5,
    )

    logger.info(f"Crawling {company_name}: {url}")

    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        result = await crawler.arun(url=url, config=config)

        markdown = ""
        if result.success:
            markdown = result.markdown.raw_markdown if result.markdown else ""
        else:
            logger.warning(
                f"Initial crawl failed for {company_name}: {result.error_message}"
            )

        if len(markdown.strip()) < MIN_MARKDOWN_LENGTH:
            markdown = await _try_fallback_selectors(
                crawler, url, company_name
            )

        logger.info(
            f"Crawled {company_name}: {len(markdown)} chars of markdown"
        )
        return markdown


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

        return result.markdown.raw_markdown if result.markdown else ""


async def crawl_many_career_pages(
    urls_and_names: list[tuple[str, str]],
) -> dict[str, str]:
    """Crawl multiple career pages concurrently.

    Returns a dict mapping company name -> markdown content.
    """
    results = {}

    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        for url, name in urls_and_names:
            config = CrawlerRunConfig(
                wait_until="networkidle",
                page_timeout=30000,
                remove_overlay_elements=True,
                scan_full_page=True,
                word_count_threshold=5,
            )

            logger.info(f"Crawling {name}: {url}")
            result = await crawler.arun(url=url, config=config)

            markdown = ""
            if result.success:
                markdown = (
                    result.markdown.raw_markdown if result.markdown else ""
                )
            else:
                logger.warning(
                    f"Initial crawl failed for {name}: {result.error_message}"
                )

            # If we got very little content, try fallback CSS selectors
            if len(markdown.strip()) < MIN_MARKDOWN_LENGTH:
                markdown = await _try_fallback_selectors(
                    crawler, url, name
                )

            results[name] = markdown
            if markdown:
                logger.info(f"Crawled {name}: {len(markdown)} chars")
            else:
                logger.error(f"No content extracted for {name}")

            # Rate limiting between requests
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
                results[url] = (
                    result.markdown.raw_markdown if result.markdown else ""
                )
            else:
                logger.warning(f"Failed to crawl detail: {url}")
                results[url] = ""

            await asyncio.sleep(1)

    return results
