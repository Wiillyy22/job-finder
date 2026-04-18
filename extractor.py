import logging
from urllib.parse import urljoin

from pydantic import BaseModel

from cache_utils import build_cache_key, load_json, save_json
from crawler import crawl_job_details_batch
from llm import extract_structured, extract_structured_list
from models import Job

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM = """You are a job listing extractor. Given the markdown content of a company's career page,
extract all individual job listings you can find. For each job, extract the title, department, location,
URL (if available), and a brief description snippet. If information is missing, leave it as an empty string.
Only extract actual job postings - ignore navigation, headers, footers, etc."""

EXTRACTION_CACHE_VERSION = "job-list-extraction-v2"
DETAIL_CACHE_VERSION = "job-detail-summary-v2"


class ExtractedJob(BaseModel):
    title: str
    department: str = ""
    location: str = ""
    url: str = ""
    description: str = ""


class JobDescription(BaseModel):
    description: str = ""


def extract_jobs_from_markdown(
    markdown: str, company_name: str, base_url: str
) -> list[Job]:
    """Extract structured job listings from career page markdown."""
    if not markdown.strip():
        logger.warning(f"No markdown content for {company_name}")
        return []

    # Truncate very long pages to stay within token limits
    if len(markdown) > 50000:
        markdown = markdown[:50000] + "\n\n[Content truncated...]"

    cache_key = build_cache_key(
        "job_extraction",
        EXTRACTION_CACHE_VERSION,
        company_name,
        base_url,
        markdown,
    )
    cached_jobs = load_json("job_extractions", cache_key)
    if cached_jobs is not None:
        jobs = [Job.model_validate(item) for item in cached_jobs]
        logger.info(f"Extraction cache hit for {company_name}: {len(jobs)} jobs")
        return jobs

    prompt = f"""Extract all job listings from this career page for {company_name}.

Career page content:
---
{markdown}
---

For each job found, extract:
- title: the job title
- department: the department or team (if mentioned)
- location: the location (if mentioned)
- url: the link to the full job posting (if available)
- description: a brief description or key requirements snippet

Return ALL jobs you find on the page."""

    extracted_jobs = extract_structured_list(
        prompt=prompt,
        item_schema=ExtractedJob,
        system=EXTRACTION_SYSTEM,
    )

    jobs: list[Job] = []
    for extracted_job in extracted_jobs:
        url = extracted_job.url
        if url and not url.startswith("http"):
            url = urljoin(base_url, url)
        jobs.append(
            Job(
                title=extracted_job.title,
                department=extracted_job.department,
                location=extracted_job.location,
                url=url,
                description=extracted_job.description,
                company=company_name,
            )
        )

    save_json(
        "job_extractions",
        cache_key,
        [job.model_dump() for job in jobs],
    )

    logger.info(f"Extracted {len(jobs)} jobs from {company_name}")
    return jobs


async def enrich_jobs_with_details(
    jobs: list[Job],
) -> list[Job]:
    """Crawl individual job pages to get full descriptions."""
    urls_to_crawl = [job.url for job in jobs if job.url]
    if not urls_to_crawl:
        return jobs

    logger.info(f"Enriching {len(urls_to_crawl)} jobs with full descriptions")
    details = await crawl_job_details_batch(urls_to_crawl)

    for job in jobs:
        if job.url and job.url in details and details[job.url]:
            detail_markdown = details[job.url]
            # Truncate individual job pages
            if len(detail_markdown) > 10000:
                detail_markdown = detail_markdown[:10000]

            cache_key = build_cache_key(
                "job_detail_summary",
                DETAIL_CACHE_VERSION,
                job.url,
                detail_markdown,
            )
            cached_summary = load_json("job_details", cache_key)
            if cached_summary is not None:
                result = JobDescription.model_validate(cached_summary)
                if result.description:
                    job.description = result.description
                continue

            prompt = f"""Extract the job details from this job posting page.
Summarize the key responsibilities, requirements, and qualifications in the description field (2-3 paragraphs).

Page content:
---
{detail_markdown}
---"""

            try:
                result = extract_structured(
                    prompt=prompt,
                    schema=JobDescription,
                    system="Extract the single job's details from this page.",
                )
                save_json(
                    "job_details",
                    cache_key,
                    result.model_dump(),
                )
                if result.description:
                    job.description = result.description
            except Exception as e:
                logger.warning(
                    f"Failed to enrich {job.title}: {e}"
                )

    return jobs
