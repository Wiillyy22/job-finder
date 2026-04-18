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
    job_title: str
    company: str
    match: bool
    reason: str
    url: str = ""
