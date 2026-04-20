import json
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Allow imports from parent directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models import RunSnapshot, make_job_id

app = FastAPI(title="Job Finder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "runs"


def _load_snapshot(run_id: str) -> RunSnapshot | None:
    path = DATA_DIR / f"{run_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return RunSnapshot.model_validate(data)


def _list_run_files() -> list[Path]:
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.glob("*.json"), reverse=True)


def _get_previous_run_id(current_run_id: str) -> str | None:
    files = _list_run_files()
    ids = [f.stem for f in files]
    try:
        idx = ids.index(current_run_id)
    except ValueError:
        return None
    if idx + 1 < len(ids):
        return ids[idx + 1]
    return None


def _compute_new_flags(
    snapshot: RunSnapshot, prev_job_ids: set[str] | None
) -> dict[str, bool]:
    """Return {job_id: is_new} for every job in the snapshot."""
    if prev_job_ids is None:
        return {make_job_id(j.job): False for j in snapshot.jobs}
    return {
        make_job_id(j.job): make_job_id(j.job) not in prev_job_ids
        for j in snapshot.jobs
    }


# --- Response models ---


class RunSummary(BaseModel):
    run_id: str
    timestamp: str
    job_count: int
    match_count: int
    company_count: int


class JobResponse(BaseModel):
    job_id: str
    title: str
    company: str
    department: str
    location: str
    url: str
    description: str
    match: bool
    reason: str
    is_new: bool


class JobsResponse(BaseModel):
    run_id: str
    timestamp: str
    jobs: list[JobResponse]
    total: int
    matching: int
    non_matching: int
    new: int


class CompanyStat(BaseModel):
    name: str
    total: int
    matching: int


class StatsResponse(BaseModel):
    run_id: str
    timestamp: str
    total_jobs: int
    matching_jobs: int
    non_matching_jobs: int
    new_jobs: int
    match_rate: float
    companies: list[CompanyStat]


# --- Endpoints ---


@app.get("/api/runs", response_model=list[RunSummary])
def list_runs():
    runs = []
    for f in _list_run_files():
        snapshot = _load_snapshot(f.stem)
        if not snapshot:
            continue
        runs.append(
            RunSummary(
                run_id=snapshot.run_id,
                timestamp=snapshot.timestamp,
                job_count=len(snapshot.jobs),
                match_count=sum(1 for j in snapshot.jobs if j.match),
                company_count=len(snapshot.companies_searched),
            )
        )
    return runs


@app.get("/api/runs/latest")
def latest_run():
    files = _list_run_files()
    if not files:
        return {"error": "No runs found"}
    run_id = files[0].stem
    return get_run_jobs(run_id, None, None, False, None)


@app.get("/api/runs/{run_id}/jobs", response_model=JobsResponse)
def get_run_jobs(
    run_id: str,
    match: Optional[bool] = Query(None),
    company: Optional[str] = Query(None),
    new_only: bool = Query(False),
    search: Optional[str] = Query(None),
):
    snapshot = _load_snapshot(run_id)
    if not snapshot:
        return JobsResponse(
            run_id=run_id,
            timestamp="",
            jobs=[],
            total=0,
            matching=0,
            non_matching=0,
            new=0,
        )

    # Compute new flags
    prev_run_id = _get_previous_run_id(run_id)
    prev_job_ids = None
    if prev_run_id:
        prev_snapshot = _load_snapshot(prev_run_id)
        if prev_snapshot:
            prev_job_ids = {make_job_id(j.job) for j in prev_snapshot.jobs}

    new_flags = _compute_new_flags(snapshot, prev_job_ids)

    # Build full job list
    all_jobs = []
    for j in snapshot.jobs:
        job_id = make_job_id(j.job)
        all_jobs.append(
            JobResponse(
                job_id=job_id,
                title=j.job.title,
                company=j.job.company,
                department=j.job.department,
                location=j.job.location,
                url=j.job.url,
                description=j.job.description,
                match=j.match,
                reason=j.reason,
                is_new=new_flags.get(job_id, False),
            )
        )

    # Apply filters
    filtered = all_jobs
    if match is not None:
        filtered = [j for j in filtered if j.match == match]
    if company:
        filtered = [
            j for j in filtered if j.company.lower() == company.lower()
        ]
    if new_only:
        filtered = [j for j in filtered if j.is_new]
    if search:
        term = search.lower()
        filtered = [
            j
            for j in filtered
            if term in j.title.lower()
            or term in j.description.lower()
            or term in j.reason.lower()
            or term in j.company.lower()
        ]

    return JobsResponse(
        run_id=snapshot.run_id,
        timestamp=snapshot.timestamp,
        jobs=filtered,
        total=len(all_jobs),
        matching=sum(1 for j in all_jobs if j.match),
        non_matching=sum(1 for j in all_jobs if not j.match),
        new=sum(1 for j in all_jobs if j.is_new),
    )


@app.get("/api/runs/{run_id}/stats", response_model=StatsResponse)
def get_run_stats(run_id: str):
    snapshot = _load_snapshot(run_id)
    if not snapshot:
        return StatsResponse(
            run_id=run_id,
            timestamp="",
            total_jobs=0,
            matching_jobs=0,
            non_matching_jobs=0,
            new_jobs=0,
            match_rate=0.0,
            companies=[],
        )

    prev_run_id = _get_previous_run_id(run_id)
    prev_job_ids = None
    if prev_run_id:
        prev_snapshot = _load_snapshot(prev_run_id)
        if prev_snapshot:
            prev_job_ids = {make_job_id(j.job) for j in prev_snapshot.jobs}

    new_flags = _compute_new_flags(snapshot, prev_job_ids)

    total = len(snapshot.jobs)
    matching = sum(1 for j in snapshot.jobs if j.match)
    non_matching = total - matching
    new_count = sum(1 for v in new_flags.values() if v)

    # Per-company stats
    company_stats: dict[str, dict] = {}
    for j in snapshot.jobs:
        name = j.job.company
        if name not in company_stats:
            company_stats[name] = {"name": name, "total": 0, "matching": 0}
        company_stats[name]["total"] += 1
        if j.match:
            company_stats[name]["matching"] += 1

    companies = sorted(
        company_stats.values(), key=lambda c: c["total"], reverse=True
    )

    return StatsResponse(
        run_id=snapshot.run_id,
        timestamp=snapshot.timestamp,
        total_jobs=total,
        matching_jobs=matching,
        non_matching_jobs=non_matching,
        new_jobs=new_count,
        match_rate=round(matching / total * 100, 1) if total else 0.0,
        companies=[CompanyStat(**c) for c in companies],
    )
