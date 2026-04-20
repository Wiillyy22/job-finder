import os

from crewai import Agent, Crew, Process, Task
from models import CompanyConfig
from tools import EvaluateJobsTool, ScrapeJobsTool


def build_crew(
    companies: list[CompanyConfig], cv_text: str
) -> Crew:
    """Build a CrewAI crew for job finding and evaluation."""

    # CrewAI uses native providers — prefix with provider name
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
            "as structured data by calling the Scrape Jobs tool"
        ),
        backstory=(
            "You are an expert job listing collector. You have NO "
            "knowledge of what jobs exist at any company — the ONLY way "
            "to find jobs is by calling the 'Scrape Jobs' tool with the "
            "company name and URL. You must call it once per company. "
            "Never fabricate or guess job listings."
        ),
        tools=[scrape_tool],
        llm=llm,
        cache=False,
        verbose=True,
    )

    evaluator_agent = Agent(
        role="Career Match Evaluator",
        goal=(
            "Evaluate each job listing against the candidate's CV by "
            "calling the Evaluate Jobs tool"
        ),
        backstory=(
            "You are an experienced career advisor and technical recruiter. "
            "You MUST use the 'Evaluate Jobs' tool to perform evaluations. "
            "You understand how to match candidate skills, experience, and "
            "goals to job requirements. You provide honest, encouraging "
            "assessments with clear reasoning."
        ),
        tools=[evaluate_tool],
        llm=llm,
        cache=False,
        verbose=True,
    )

    # --- Format company list for the scraper task ---
    company_list = "\n".join(
        f"- {c.name}: {c.careers_url}" for c in companies
    )

    # --- Tasks ---
    # NOTE: output_pydantic is deliberately omitted — with Anthropic's
    # native provider, it triggers structured output mode which bypasses
    # tool calling entirely. We parse the output in main_crew.py instead.
    scraper_task = Task(
        description=(
            f"You MUST call the 'Scrape Jobs' tool for each company below. "
            f"Do NOT skip any company. Do NOT fabricate results.\n\n"
            f"Companies:\n{company_list}\n\n"
            f"Steps:\n"
            f"1. Call 'Scrape Jobs' with company_name and url for the "
            f"first company\n"
            f"2. Repeat for each remaining company\n"
            f"3. Combine all returned job arrays into one list\n"
            f"4. Return the combined list as a JSON object with a 'jobs' key"
        ),
        expected_output=(
            "A JSON object with a 'jobs' key containing an array of all "
            "extracted job listings, each with title, department, location, "
            "url, description, and company fields."
        ),
        agent=scraper_agent,
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
            f"Return the complete list of evaluation results as a JSON "
            f"object with a 'results' key."
        ),
        expected_output=(
            "A JSON object with a 'results' key containing an array of "
            "evaluation results, each with job_id, job_title, company, "
            "match (boolean), reason, and url fields."
        ),
        agent=evaluator_agent,
        context=[scraper_task],
    )

    # --- Crew ---
    return Crew(
        agents=[scraper_agent, evaluator_agent],
        tasks=[scraper_task, evaluator_task],
        process=Process.sequential,
        verbose=True,
    )
