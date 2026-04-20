# Job Finder Agent

An automated pipeline that crawls company career pages, extracts job listings, and evaluates them against your CV using LLMs. It enriches each job with a full description from its detail page, then scores how well it fits your background — saving you hours of manual searching.

## Quick start

1. Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Create your local files:

```bash
cp .env.example .env
cp cv.example.md cv.md
cp config.example.yaml config.yaml
```

3. Edit:
- `.env` with your API key and model settings
- `cv.md` with your own CV
- `config.yaml` with the companies you want to search

4. Run:

```bash
python main.py
```

## Two pipelines

The project implements the same job-finding workflow in two ways:

**`python main.py`** — Direct orchestration. A straightforward Python pipeline where each step (crawl, extract, enrich, evaluate) is called explicitly. Deterministic, fast, and easy to debug.

**`python main_crew.py`** — Agent-based orchestration using [CrewAI](https://www.crewai.com/). The same crawling, extraction, and evaluation logic is wrapped as tools that autonomous agents decide when and how to call. This demonstrates how the pipeline adapts to an agent framework where the LLM drives the control flow rather than hardcoded steps.

Both produce the same output and share all core modules (`crawler.py`, `extractor.py`, `evaluator.py`, `llm.py`).

## How it works

1. **Crawl** — Visits each company's career page using a headless browser (Crawl4AI), with automatic pagination detection and fallback CSS selectors for sites that block content.
2. **Extract** — Sends the page markdown to an LLM to extract structured job listings (title, department, location, URL).
3. **Enrich** — Crawls each individual job page and summarizes its description using a fast, cheap model (Haiku). This gives the evaluator real requirements to work with instead of just job titles.
4. **Evaluate** — Compares each job against a compact candidate profile extracted from your CV, deciding match/no-match with a one-sentence reason.

All LLM results are cached to disk (`.cache/`), so subsequent runs skip already-processed jobs.

## Options

- `python main.py --no-enrich` — Skip the enrichment step (faster, but evaluations are based on job titles only)
- `--config path/to/config.yaml` — Use a different company list
- `--cv path/to/cv.md` — Use a different CV
- `--output path/to/dir` — Write results to a different directory

## Output

Results are written to:
- `output/matching_jobs.md` — Jobs worth applying for, with reasoning
- `output/non_matching_jobs.md` — Jobs that don't fit, with reasoning

## Notes

- `cv.md`, `config.yaml`, `.env`, cache files, and generated output are ignored by git.
- Share `cv.example.md` and `config.example.yaml` as the public templates.
