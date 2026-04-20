from hashlib import sha256

from pydantic import BaseModel, Field


class CompanyConfig(BaseModel):
    name: str
    careers_url: str


class Config(BaseModel):
    companies: list[CompanyConfig]


class Job(BaseModel):
    title: str
    department: str = ""
    location: str = ""
    url: str = ""
    description: str = ""
    company: str = ""


class CandidateProfile(BaseModel):
    summary: str = ""
    core_skills: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    seniority: str = ""
    domains: list[str] = Field(default_factory=list)


class JobMatchDecision(BaseModel):
    job_id: str
    match: bool
    reason: str


class EvaluationResult(BaseModel):
    job_id: str
    job_title: str
    company: str
    match: bool
    reason: str
    url: str = ""


# --- Shared utilities ---


def compact_text(text: str, max_chars: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def make_job_id(job: Job) -> str:
    stable_fields = [
        job.company.strip(),
        job.title.strip(),
        job.department.strip(),
        job.location.strip(),
        job.url.strip(),
        compact_text(job.description, 200),
    ]
    digest = sha256("||".join(stable_fields).encode("utf-8")).hexdigest()
    return digest[:12]


# --- Run snapshot models ---


class RunJob(BaseModel):
    job_id: str
    job: Job
    match: bool
    reason: str


class RunSnapshot(BaseModel):
    run_id: str
    timestamp: str
    companies_searched: list[str]
    jobs: list[RunJob]
