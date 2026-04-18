import logging
from pathlib import Path

from dotenv import load_dotenv
import yaml

from crew import build_crew
from evaluator import write_results
from models import Config, EvaluationResult

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent
DEFAULT_CONFIG = PROJECT_DIR / "config.yaml"
DEFAULT_CV = PROJECT_DIR / "cv.md"
OUTPUT_DIR = PROJECT_DIR / "output"


def run(
    config_path: Path = DEFAULT_CONFIG,
    cv_path: Path = DEFAULT_CV,
    output_dir: Path = OUTPUT_DIR,
):
    # Load config
    logger.info(f"Loading config from {config_path}")
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    config = Config.model_validate(raw)
    logger.info(f"Found {len(config.companies)} companies to search")

    # Load CV
    logger.info(f"Loading CV from {cv_path}")
    cv_text = cv_path.read_text()

    # Build and run crew
    logger.info("=== Building CrewAI Crew ===")
    crew = build_crew(config.companies, cv_text)

    logger.info("=== Running Crew ===")
    result = crew.kickoff()

    # Extract results
    logger.info("=== Processing Results ===")
    evaluator_task = crew.tasks[-1]

    if evaluator_task.output and evaluator_task.output.pydantic:
        eval_results = evaluator_task.output.pydantic.results
    else:
        # Fallback: try parsing from raw output
        logger.warning(
            "No pydantic output, attempting to parse raw output"
        )
        import json

        raw_output = str(result)
        try:
            data = json.loads(raw_output)
            if isinstance(data, dict) and "results" in data:
                eval_results = [
                    EvaluationResult.model_validate(r)
                    for r in data["results"]
                ]
            elif isinstance(data, list):
                eval_results = [
                    EvaluationResult.model_validate(r) for r in data
                ]
            else:
                logger.error("Could not parse crew output")
                return
        except json.JSONDecodeError:
            logger.error(f"Failed to parse crew output: {raw_output[:200]}")
            return

    # Write output files
    logger.info("=== Writing Results ===")
    match_path, no_match_path = write_results(eval_results, output_dir)

    matching = sum(1 for r in eval_results if r.match)
    non_matching = len(eval_results) - matching

    logger.info("=== Done! ===")
    logger.info(f"Matching jobs ({matching}): {match_path}")
    logger.info(f"Non-matching jobs ({non_matching}): {no_match_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Find jobs that match your CV (CrewAI version)"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to config.yaml",
    )
    parser.add_argument(
        "--cv", type=Path, default=DEFAULT_CV, help="Path to your CV"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory",
    )
    args = parser.parse_args()

    run(
        config_path=args.config,
        cv_path=args.cv,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()
