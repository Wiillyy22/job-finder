import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
import yaml

load_dotenv()

from crawler import crawl_many_career_pages
from evaluator import evaluate_jobs, write_results
from extractor import enrich_jobs_with_details, extract_jobs_from_markdown
from models import Config, RunJob, RunSnapshot, make_job_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent
DEFAULT_CONFIG = PROJECT_DIR / "config.yaml"
DEFAULT_CV = PROJECT_DIR / "cv.md"
OUTPUT_DIR = PROJECT_DIR / "output"
DATA_DIR = PROJECT_DIR / "data" / "runs"


async def run(
    config_path: Path = DEFAULT_CONFIG,
    cv_path: Path = DEFAULT_CV,
    output_dir: Path = OUTPUT_DIR,
    enrich: bool = True,
):
    # Load config
    logger.info(f"Loading config from {config_path}")
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    config = Config.model_validate(raw)
    logger.info(f"Found {len(config.companies)} companies to search")

    # Load CV
    logger.info(f"Loading CV from {cv_path}")
    cv_text = cv_path.read_text()

    # Step 1: Crawl all career pages
    logger.info("=== Step 1: Crawling career pages ===")
    urls_and_names = [
        (c.careers_url, c.name) for c in config.companies
    ]
    page_markdowns = await crawl_many_career_pages(urls_and_names)

    # Step 2: Extract job listings from each page
    logger.info("=== Step 2: Extracting job listings ===")
    all_jobs = []
    for company in config.companies:
        markdown = page_markdowns.get(company.name, "")
        if not markdown:
            logger.warning(f"No content for {company.name}, skipping")
            continue
        try:
            jobs = extract_jobs_from_markdown(
                markdown, company.name, company.careers_url
            )
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to extract jobs from {company.name}: {e}")
            continue

    logger.info(f"Total jobs extracted: {len(all_jobs)}")

    if not all_jobs:
        logger.error("No jobs found. Check your career page URLs.")
        return

    # Step 2.5 (optional): Enrich with full descriptions
    if enrich:
        logger.info("=== Step 2.5: Enriching job descriptions ===")
        all_jobs = await enrich_jobs_with_details(all_jobs)

    # Step 3: Evaluate jobs against CV
    logger.info("=== Step 3: Evaluating job matches ===")
    results = evaluate_jobs(all_jobs, cv_text)

    # Step 4: Write output files
    logger.info("=== Step 4: Writing results ===")
    match_path, no_match_path = write_results(results, output_dir)

    matching = sum(1 for r in results if r.match)
    non_matching = len(results) - matching

    # Step 5: Save run snapshot for the frontend
    logger.info("=== Step 5: Saving run snapshot ===")
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y-%m-%dT%H-%M-%S")
    jobs_by_id = {}
    duplicate_job_ids = set()
    for job in all_jobs:
        job_id = make_job_id(job)
        if job_id in jobs_by_id:
            duplicate_job_ids.add(job_id)
        jobs_by_id[job_id] = job

    if duplicate_job_ids:
        duplicate_list = ", ".join(sorted(duplicate_job_ids))
        raise RuntimeError(
            "Duplicate job IDs detected while building the run snapshot: "
            f"{duplicate_list}"
        )

    run_jobs = []
    for r in results:
        job = jobs_by_id.get(r.job_id)
        if job:
            run_jobs.append(
                RunJob(
                    job_id=r.job_id,
                    job=job,
                    match=r.match,
                    reason=r.reason,
                )
            )
    snapshot = RunSnapshot(
        run_id=run_id,
        timestamp=now.isoformat(),
        companies_searched=[c.name for c in config.companies],
        jobs=run_jobs,
    )
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = DATA_DIR / f"{run_id}.json"
    snapshot_path.write_text(
        json.dumps(snapshot.model_dump(), ensure_ascii=False, indent=2)
    )
    logger.info(f"Run snapshot saved: {snapshot_path}")

    logger.info("=== Done! ===")
    logger.info(f"Matching jobs ({matching}): {match_path}")
    logger.info(f"Non-matching jobs ({non_matching}): {no_match_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Find jobs that match your CV"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to config.yaml",
    )
    parser.add_argument(
        "--cv", type=Path, default=DEFAULT_CV, help="Path to your CV"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip crawling individual job pages for descriptions (faster, less accurate)",
    )
    args = parser.parse_args()

    asyncio.run(
        run(
            config_path=args.config,
            cv_path=args.cv,
            output_dir=args.output,
            enrich=not args.no_enrich,
        )
    )


if __name__ == "__main__":
    main()
