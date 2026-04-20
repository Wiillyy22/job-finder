"""One-time script to generate a sample run snapshot from existing markdown output.
Run once, then delete. Used to bootstrap frontend development."""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_DIR / "output"
DATA_DIR = PROJECT_DIR / "data" / "runs"


def parse_markdown_table(filepath: Path, is_match: bool) -> list[dict]:
    """Parse a markdown results table into job entries."""
    jobs = []
    text = filepath.read_text()
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line.startswith("|") or line.startswith("| Job Title") or line.startswith("|---"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 3:
            continue

        title_cell = parts[0]
        company = parts[1]
        reason = parts[2]

        # Extract URL and title from markdown link
        link_match = re.match(r"\[(.+?)\]\((.+?)\)", title_cell)
        if link_match:
            title = link_match.group(1)
            url = link_match.group(2)
        else:
            title = title_cell
            url = ""

        # Generate a simple hash-based job_id
        from hashlib import sha256
        stable = f"{company}||{title}||||||"
        job_id = sha256(stable.encode()).hexdigest()[:12]

        jobs.append({
            "job_id": job_id,
            "job": {
                "title": title,
                "department": "",
                "location": "",
                "url": url,
                "description": "",
                "company": company,
            },
            "match": is_match,
            "reason": reason,
        })
    return jobs


def main():
    matching = parse_markdown_table(OUTPUT_DIR / "matching_jobs.md", True)
    non_matching = parse_markdown_table(OUTPUT_DIR / "non_matching_jobs.md", False)

    all_jobs = matching + non_matching
    companies = sorted(set(j["job"]["company"] for j in all_jobs))

    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y-%m-%dT%H-%M-%S")

    snapshot = {
        "run_id": run_id,
        "timestamp": now.isoformat(),
        "companies_searched": companies,
        "jobs": all_jobs,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{run_id}.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"Snapshot written: {path}")
    print(f"  Total jobs: {len(all_jobs)}")
    print(f"  Matching: {len(matching)}")
    print(f"  Non-matching: {len(non_matching)}")
    print(f"  Companies: {len(companies)}")


if __name__ == "__main__":
    main()
