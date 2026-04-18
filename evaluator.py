import logging
from hashlib import sha256
import json
from pathlib import Path

from cache_utils import build_cache_key, load_json, save_json
from llm import extract_structured, extract_structured_list
from models import CandidateProfile, EvaluationResult, Job, JobMatchDecision

logger = logging.getLogger(__name__)

EVALUATION_SYSTEM = """You are a career advisor evaluating job listings against a candidate's CV.
For each job, decide if the candidate is a sensible application target. Consider:
- Skills alignment
- Experience level match
- Domain relevance
- Stated location preferences

Prefer concise reasons. A plausible stretch can still be marked as a match."""

PROFILE_SYSTEM = """You extract a compact job-matching profile from a candidate CV.
Capture only the facts that are likely to be reused across many job evaluations."""

BATCH_SIZE = 10
DESCRIPTION_PREVIEW_CHARS = 600
PROFILE_CACHE_VERSION = "candidate-profile-v1"
EVALUATION_CACHE_VERSION = "job-evaluation-v2"


def build_candidate_profile(cv_text: str) -> CandidateProfile:
    """Extract a compact candidate profile once and reuse it across batches."""
    cache_key = build_cache_key(
        "candidate_profile",
        PROFILE_CACHE_VERSION,
        cv_text,
    )
    cached_profile = load_json("candidate_profiles", cache_key)
    if cached_profile is not None:
        profile = CandidateProfile.model_validate(cached_profile)
        logger.info("Candidate profile cache hit")
        return profile

    prompt = f"""Extract a compact candidate profile from this CV for job matching.

CV:
---
{cv_text}
---

Return:
- summary: at most 2 sentences
- core_skills: up to 12 technical skills or keywords
- target_roles: up to 6 role titles or role families
- preferred_locations: only explicit locations or remote/hybrid preferences
- seniority: one short phrase
- domains: up to 6 relevant industries, product areas, or problem domains"""

    profile = extract_structured(
        prompt=prompt,
        schema=CandidateProfile,
        system=PROFILE_SYSTEM,
    )
    save_json(
        "candidate_profiles",
        cache_key,
        profile.model_dump(),
    )
    return profile


def candidate_profile_to_text(profile: CandidateProfile) -> str:
    """Render the reusable profile into a compact prompt block."""
    lines = [
        f"Summary: {profile.summary}".strip(),
        f"Seniority: {profile.seniority}".strip(),
    ]
    if profile.core_skills:
        lines.append(f"Skills: {', '.join(profile.core_skills)}")
    if profile.target_roles:
        lines.append(f"Target roles: {', '.join(profile.target_roles)}")
    if profile.domains:
        lines.append(f"Domains: {', '.join(profile.domains)}")
    if profile.preferred_locations:
        lines.append(
            f"Preferred locations: {', '.join(profile.preferred_locations)}"
        )
    return "\n".join(line for line in lines if not line.endswith(":"))


def evaluate_jobs(jobs: list[Job], cv_text: str) -> list[EvaluationResult]:
    """Evaluate all jobs against the CV. Returns list of EvaluationResults."""
    if not jobs:
        return []

    candidate_profile = build_candidate_profile(cv_text)
    return evaluate_jobs_with_profile(jobs, candidate_profile)


def evaluate_jobs_with_profile(
    jobs: list[Job], candidate_profile: CandidateProfile
) -> list[EvaluationResult]:
    """Evaluate all jobs against a reusable compact candidate profile."""
    if not jobs:
        return []

    all_results: list[EvaluationResult] = []
    cached_results_by_id: dict[str, JobMatchDecision] = {}
    uncached_payloads: list[dict[str, str]] = []
    uncached_job_ids: list[str] = []
    candidate_profile_text = candidate_profile_to_text(candidate_profile)

    for job in jobs:
        payload = _build_job_payload(job)
        cache_key = build_cache_key(
            "job_evaluation",
            EVALUATION_CACHE_VERSION,
            candidate_profile.model_dump(),
            payload,
        )
        cached_result = load_json("job_evaluations", cache_key)
        if cached_result is not None:
            cached_results_by_id[payload["job_id"]] = (
                JobMatchDecision.model_validate(cached_result)
            )
            continue

        uncached_payloads.append(payload)
        uncached_job_ids.append(payload["job_id"])

    for i in range(0, len(uncached_payloads), BATCH_SIZE):
        batch = uncached_payloads[i : i + BATCH_SIZE]
        batch_results = _evaluate_batch(batch, candidate_profile_text)
        batch_by_id = {
            result.job_id: result for result in batch_results
        }
        missing_job_ids = [
            payload["job_id"]
            for payload in batch
            if payload["job_id"] not in batch_by_id
        ]
        if missing_job_ids:
            raise RuntimeError(
                "Missing evaluation results for job IDs: "
                + ", ".join(missing_job_ids)
            )

        for payload in batch:
            decision = batch_by_id[payload["job_id"]]
            cached_results_by_id[decision.job_id] = decision
            cache_key = build_cache_key(
                "job_evaluation",
                EVALUATION_CACHE_VERSION,
                candidate_profile.model_dump(),
                payload,
            )
            save_json(
                "job_evaluations",
                cache_key,
                decision.model_dump(),
            )
        logger.info(
            f"Evaluated batch {i // BATCH_SIZE + 1}: "
            f"{len(batch)} jobs"
        )

    cache_hits = len(jobs) - len(uncached_job_ids)
    if cache_hits:
        logger.info(f"Evaluation cache hit: {cache_hits}/{len(jobs)} jobs")
    if uncached_job_ids:
        logger.info(
            f"Evaluation cache miss: {len(uncached_job_ids)}/{len(jobs)} jobs"
        )

    for job in jobs:
        job_id = _make_job_id(job)
        decision = cached_results_by_id[job_id]
        all_results.append(
            EvaluationResult(
                job_title=job.title,
                company=job.company,
                match=decision.match,
                reason=decision.reason,
                url=job.url,
            )
        )

    return all_results


def _evaluate_batch(
    jobs: list[dict[str, str]], candidate_profile_text: str
) -> list[JobMatchDecision]:
    """Evaluate a batch of compact job payloads against the candidate profile."""
    jobs_json = json.dumps(jobs, ensure_ascii=False)

    prompt = f"""Evaluate these jobs against the candidate profile.

Candidate profile:
{candidate_profile_text}

Jobs:
{jobs_json}

Return one result for every input job.
Rules:
- Use the exact input job_id
- Set match=true only if the candidate is a sensible person to apply
- reason must be a single short sentence"""

    return extract_structured_list(
        prompt=prompt,
        item_schema=JobMatchDecision,
        system=EVALUATION_SYSTEM,
    )


def _build_job_payload(job: Job) -> dict[str, str]:
    description = _compact_text(job.description, DESCRIPTION_PREVIEW_CHARS)
    payload = {
        "job_id": _make_job_id(job),
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "description": description,
    }
    if job.department:
        payload["department"] = job.department
    return payload


def _make_job_id(job: Job) -> str:
    stable_fields = [
        job.company.strip(),
        job.title.strip(),
        job.department.strip(),
        job.location.strip(),
        job.url.strip(),
        _compact_text(job.description, 200),
    ]
    digest = sha256("||".join(stable_fields).encode("utf-8")).hexdigest()
    return digest[:12]


def _compact_text(text: str, max_chars: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def write_results(
    results: list[EvaluationResult], output_dir: Path
) -> tuple[Path, Path]:
    """Write evaluation results to two markdown files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    matching = [r for r in results if r.match]
    non_matching = [r for r in results if not r.match]

    match_path = output_dir / "matching_jobs.md"
    no_match_path = output_dir / "non_matching_jobs.md"

    # Write matching jobs
    with open(match_path, "w") as f:
        f.write("# Jobs to Apply For\n\n")
        if matching:
            f.write(
                "| Job Title | Company | Why It Fits |\n"
            )
            f.write("|-----------|---------|-------------|\n")
            for r in matching:
                title = r.job_title.replace("|", "/")
                reason = r.reason.replace("|", "/")
                url_part = (
                    f"[{title}]({r.url})" if r.url else title
                )
                f.write(
                    f"| {url_part} | {r.company} | {reason} |\n"
                )
        else:
            f.write("No matching jobs found.\n")

        f.write(f"\n\n*Total: {len(matching)} matching jobs*\n")

    # Write non-matching jobs
    with open(no_match_path, "w") as f:
        f.write("# Jobs That Don't Fit\n\n")
        if non_matching:
            f.write("| Job Title | Company | Why Not |\n")
            f.write("|-----------|---------|----------|\n")
            for r in non_matching:
                title = r.job_title.replace("|", "/")
                reason = r.reason.replace("|", "/")
                url_part = (
                    f"[{title}]({r.url})" if r.url else title
                )
                f.write(
                    f"| {url_part} | {r.company} | {reason} |\n"
                )
        else:
            f.write("All jobs were a match!\n")

        f.write(
            f"\n\n*Total: {len(non_matching)} non-matching jobs*\n"
        )

    logger.info(
        f"Results written: {len(matching)} matching, "
        f"{len(non_matching)} non-matching"
    )
    return match_path, no_match_path
