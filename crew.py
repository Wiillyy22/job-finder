import os

from crewai import Agent, Crew, Process, Task
from pydantic import BaseModel

from models import CompanyConfig, EvaluationResult, Job
from tools import EvaluateJobsTool, ScrapeJobsTool


# Wrapper models for structured task output
class JobList(BaseModel):
    jobs: list[Job]


class EvaluationResultList(BaseModel):
    results: list[EvaluationResult]


def build_crew(
    companies: list[CompanyConfig], cv_text: str
) -> Crew:
    """Build a CrewAI crew for job finding and evaluation."""

    # CrewAI uses litellm under the hood — prefix with provider name
    provider = os.getenv("LLM_PROVIDER", "anthropic")
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    if provider == "anthropic":
        llm = f"anthropic/{model}"
    elif provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        llm = f"openai/{model}"
    else:
        llm = model

    # --- Tools ---
    scrape_tool = ScrapeJobsTool()
    evaluate_tool = EvaluateJobsTool()

    # --- Agents ---
    scraper_agent = Agent(
        role="Job Listing Scraper",
        goal=(
            "Scrape company career pages and return all job listings "
            "as structured data"
        ),
        backstory=(
            "You are an expert job listing collector. You use the "
            "'Scrape Jobs' tool to crawl each company's career page "
            "and extract structured job listings. You call the tool "
            "once per company and combine all results."
        ),
        tools=[scrape_tool],
        llm=llm,
        verbose=True,
    )

    evaluator_agent = Agent(
        role="Career Match Evaluator",
        goal=(
            "Evaluate each job listing against the candidate's CV and "
            "determine which jobs are a good match"
        ),
        backstory=(
            "You are an experienced career advisor and technical recruiter. "
            "You understand how to match candidate skills, experience, and "
            "goals to job requirements. You provide honest, encouraging "
            "assessments with clear reasoning."
        ),
        tools=[evaluate_tool],
        llm=llm,
        verbose=True,
    )

    # --- Format company list for the scraper task ---
    company_list = "\n".join(
        f"- {c.name}: {c.careers_url}" for c in companies
    )

    # --- Tasks ---
    scraper_task = Task(
        description=(
            f"Scrape job listings from the following company career pages.\n\n"
            f"Companies:\n{company_list}\n\n"
            f"For EACH company listed above, call the 'Scrape Jobs' tool "
            f"with the company_name and url. The tool handles crawling and "
            f"extraction internally and returns a JSON array of jobs.\n\n"
            f"Combine all the jobs from every company into one list and "
            f"return it."
        ),
        expected_output=(
            "A JSON object with a 'jobs' key containing an array of all "
            "extracted job listings, each with title, department, location, "
            "url, description, and company fields."
        ),
        agent=scraper_agent,
        output_pydantic=JobList,
    )

    evaluator_task = Task(
        description=(
            f"Evaluate all the job listings from the previous task against "
            f"the candidate's CV below. For each job, determine if the "
            f"candidate should apply (match=true) or not (match=false), "
            f"and provide a one-sentence reason.\n\n"
            f"## Candidate CV:\n{cv_text}\n\n"
            f"Use the 'Evaluate Jobs' tool, passing the jobs from the "
            f"previous task as a JSON string and the CV text above. "
            f"Return the complete list of evaluation results."
        ),
        expected_output=(
            "A JSON object with a 'results' key containing an array of "
            "evaluation results, each with job_title, company, match "
            "(boolean), reason, and url fields."
        ),
        agent=evaluator_agent,
        context=[scraper_task],
        output_pydantic=EvaluationResultList,
    )

    # --- Crew ---
    return Crew(
        agents=[scraper_agent, evaluator_agent],
        tasks=[scraper_task, evaluator_task],
        process=Process.sequential,
        verbose=True,
    )
