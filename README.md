# Job Finder Agent

This project crawls company career pages, extracts job listings, and scores them against your CV using an LLM.

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

4. Run the default pipeline:

```bash
python main.py
```

Optional:
- `python main.py --enrich` to crawl individual job pages for richer descriptions
- `python main_crew.py` to run the CrewAI version

## Output

Results are written to:
- `output/matching_jobs.md`
- `output/non_matching_jobs.md`

## Notes

- `cv.md`, `config.yaml`, `.env`, cache files, and generated output are ignored by git.
- Share `cv.example.md` and `config.example.yaml` as the public templates.
