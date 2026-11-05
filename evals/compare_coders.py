#!/usr/bin/env python3
"""Compare two OpenCode coder models on an isolated HumanEval sample."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile
import time


MODELS = {
    "haiku": "bedrock-opencode/claude-haiku-5-5#medium",
    "luna": "bedrock-opencode/gpt-6-luna#medium",
}


def load_tasks(path, count):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        tasks = [json.loads(line) for line in stream]
    selected = random.Random(42).sample(tasks, count)
    return sorted(selected, key=lambda task: int(task["task_id"].split("/")[-1]))


def check_solution(source, task):
    with tempfile.TemporaryDirectory(prefix="oc-eval-check-") as directory:
        work = Path(directory)
        program = source + "\n\n" + task["test"] + "\n\ncheck(" + task["entry_point"] + ")\n"
        (work / "check.py").write_text(program, encoding="utf-8")
        command = [
            "bwrap", "--ro-bind", "/usr", "/usr", "--ro-bind", "/bin", "/bin",
            "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
            "--ro-bind", str(work), "/work", "--dir", "/tmp", "--proc", "/proc",
            "--dev", "/dev", "--unshare-net", "--setenv", "HOME", "/tmp",
            "--chdir", "/work", "/usr/bin/python3", "-I", "check.py",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        except subprocess.TimeoutExpired:
            return False, "check timed out"
        return result.returncode == 0, result.stderr[-500:]


def run_case(task, label):
    with tempfile.TemporaryDirectory(prefix="oc-eval-code-") as directory:
        path = Path(directory) / "task.py"
        path.write_text(task["prompt"], encoding="utf-8")
        prompt = (
            "Complete the function in task.py according to its docstring. "
            "Edit only task.py. Do not access tests or the network. "
            "Do not add unrelated code. Reply briefly when done."
        )
        command = [
            "opencode", "run", "--standalone", "--auto", "--agent", "coder-weak",
            "--model", MODELS[label], "--format", "json", prompt,
        ]
        start = time.monotonic()
        try:
            environment = os.environ.copy()
            environment["PWD"] = directory
            run = subprocess.run(command, cwd=directory, env=environment,
                                 capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return {"task": task["task_id"], "model": label, "passed": False,
                    "seconds": 120, "cost_usd": None, "error": "OpenCode timed out"}
        seconds = round(time.monotonic() - start, 2)
        events = []
        for line in run.stdout.splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        cost = sum(event.get("part", {}).get("cost", 0) for event in events
                   if event.get("type") == "step_finish")
        session = next((event.get("sessionID") for event in events if event.get("sessionID")), None)
        tokens = None
        if session:
            try:
                export = subprocess.run(
                    ["opencode", "session", "export", session, "--sanitize"],
                    cwd=directory, env=environment, capture_output=True, text=True, timeout=10,
                )
                info = json.loads(export.stdout)["info"]
                cost = info.get("cost", cost)
                tokens = info.get("tokens")
            except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
                pass
        source = path.read_text(encoding="utf-8")
        passed, error = check_solution(source, task) if source != task["prompt"] else (False, "unchanged")
        if run.returncode:
            error = (run.stderr or error)[-500:]
        return {"task": task["task_id"], "model": label, "passed": passed,
                "seconds": seconds, "cost_usd": round(cost, 8), "tokens": tokens,
                "session": session,
                "error": "" if passed else error}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="Official HumanEval.jsonl.gz path")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    tasks = load_tasks(args.dataset, args.count)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_case, task, label): (task["task_id"], label)
                   for task in tasks for label in MODELS}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{len(results)}/{len(futures)} {result['task']} {result['model']} "
                  f"pass={result['passed']} cost=${result['cost_usd']} "
                  f"time={result['seconds']}s", flush=True)
    results.sort(key=lambda result: (int(result["task"].split("/")[-1]), result["model"]))
    args.results.parent.mkdir(parents=True, exist_ok=True)
    args.results.write_text(
        "".join(json.dumps(result, separators=(",", ":")) + "\n" for result in results),
        encoding="utf-8",
    )
    for label in MODELS:
        subset = [result for result in results if result["model"] == label]
        print(f"{label}: {sum(result['passed'] for result in subset)}/{len(subset)} passed, "
              f"${sum(result['cost_usd'] or 0 for result in subset):.4f}, "
              f"{sum(result['seconds'] for result in subset):.1f}s")


if __name__ == "__main__":
    main()
