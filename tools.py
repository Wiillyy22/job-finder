import asyncio
import json
import logging
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from crawler import crawl_career_page
from extractor import extract_jobs_from_markdown
from evaluator import evaluate_jobs
from models import Job

logger = logging.getLogger(__name__)


# --- Tool Input Schemas ---


class ScrapeInput(BaseModel):
    company_name: str = Field(description="Name of the company")
    url: str = Field(description="URL of the company's career page")


class EvaluateInput(BaseModel):
    jobs_json: str = Field(
        description="JSON string of job listings to evaluate"
    )
    cv_text: str = Field(description="The candidate's CV text")


# --- Tools ---


class ScrapeJobsTool(BaseTool):
    name: str = "Scrape Jobs"
    description: str = (
        "Crawls a company's career page and extracts all job listings "
        "into structured data. Returns a JSON array of job objects, each "
        "with title, department, location, url, description, and company "
        "fields. Call this once per company."
    )
    args_schema: Type[BaseModel] = ScrapeInput

    def _run(self, company_name: str, url: str) -> str:
        logger.info(f"Tool: Scraping jobs from {company_name} at {url}")
        markdown = asyncio.run(crawl_career_page(url, company_name))
        if not markdown:
            return json.dumps([])
        jobs = extract_jobs_from_markdown(markdown, company_name, url)
        logger.info(
            f"Tool: Extracted {len(jobs)} jobs from {company_name}"
        )
        return json.dumps(
            [job.model_dump() for job in jobs], ensure_ascii=False
        )


class EvaluateJobsTool(BaseTool):
    name: str = "Evaluate Jobs"
    description: str = (
        "Evaluates a list of job listings against the candidate's CV. "
        "Returns a JSON array of evaluation results with match/no-match "
        "decisions and reasoning."
    )
    args_schema: Type[BaseModel] = EvaluateInput

    def _run(self, jobs_json: str, cv_text: str) -> str:
        logger.info("Tool: Evaluating jobs against CV")
        jobs = [Job.model_validate(j) for j in json.loads(jobs_json)]
        results = evaluate_jobs(jobs, cv_text)
        return json.dumps(
            [r.model_dump() for r in results], ensure_ascii=False
        )
