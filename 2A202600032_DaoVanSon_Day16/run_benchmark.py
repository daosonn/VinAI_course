from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich import print

from src.reflexion_lab.agents import ReActAgent, ReflexionAgent
from src.reflexion_lab.reporting import build_report, save_report
from src.reflexion_lab.utils import load_dataset, save_jsonl

app = typer.Typer(add_completion=False)


@app.command()
def main(
    dataset: str = "data/hotpot_mini.json",
    out_dir: str = "outputs/sample_run",
    reflexion_attempts: int = 3,
    runtime: str = "ollama",
    model: str = "llama3.1:8b",
    limit: int | None = None,
) -> None:
    os.environ["REFLEXION_RUNTIME"] = runtime
    if runtime == "ollama":
        os.environ["OLLAMA_MODEL"] = model

    examples = load_dataset(dataset)
    if limit is not None:
        examples = examples[:limit]

    print(
        f"[cyan]Running benchmark[/cyan] runtime={runtime} model={model} "
        f"examples={len(examples)} reflexion_attempts={reflexion_attempts}"
    )

    react = ReActAgent()
    reflexion = ReflexionAgent(max_attempts=reflexion_attempts)

    react_records = [react.run(example) for example in examples]
    reflexion_records = [reflexion.run(example) for example in examples]

    out_path = Path(out_dir)
    save_jsonl(out_path / "react_runs.jsonl", react_records)
    save_jsonl(out_path / "reflexion_runs.jsonl", reflexion_records)

    all_records = react_records + reflexion_records
    report = build_report(all_records, dataset_name=Path(dataset).name, mode=runtime)
    json_path, md_path = save_report(report, out_path)

    print(f"[green]Saved[/green] {json_path}")
    print(f"[green]Saved[/green] {md_path}")
    print(json.dumps(report.summary, indent=2))


if __name__ == "__main__":
    app()
