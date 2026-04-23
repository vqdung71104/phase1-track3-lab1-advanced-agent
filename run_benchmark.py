from __future__ import annotations
import json
from pathlib import Path
import typer
from rich import print
from src.reflexion_lab.agents import ReActAgent, ReflexionAgent
from src.reflexion_lab.reporting import build_report, save_report
from src.reflexion_lab.utils import load_dataset, save_jsonl
app = typer.Typer(add_completion=False)

@app.command()
def main(dataset: str = "data/hotpot_mini.json", out_dir: str = "outputs/sample_run", reflexion_attempts: int = 3) -> None:
    examples = load_dataset(dataset)
    
    react = ReActAgent()
    reflexion = ReflexionAgent(max_attempts=reflexion_attempts)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    all_records = []
    react_records = []
    reflexion_records = []
    total = len(examples)
    
    print(f"Bắt đầu chạy ReAct ({total} câu)...")
    for i, example in enumerate(examples):
        print(f"\n---> ReAct: Đang xử lý câu {i+1}/{total}")
        record = react.run(example)
        react_records.append(record)
        all_records.append(record)
        
        # Lưu kết quả liên tục vào file
        save_jsonl(out_path / "react_runs.jsonl", react_records)
        report = build_report(all_records, dataset_name=Path(dataset).name, mode="api")
        save_report(report, out_path)
        
    print(f"\nBắt đầu chạy Reflexion ({total} câu)...")
    for i, example in enumerate(examples):
        print(f"\n---> Reflexion: Đang xử lý câu {i+1}/{total}")
        record = reflexion.run(example)
        reflexion_records.append(record)
        all_records.append(record)
        
        # Lưu kết quả liên tục vào file
        save_jsonl(out_path / "reflexion_runs.jsonl", reflexion_records)
        report = build_report(all_records, dataset_name=Path(dataset).name, mode="api")
        save_report(report, out_path)

    print("\n[green]Hoàn thành toàn bộ quy trình![/green]")
    print(json.dumps(report.summary, indent=2))

if __name__ == "__main__":
    app()
