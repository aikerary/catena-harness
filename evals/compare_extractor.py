#!/usr/bin/env python3
"""Compare coder models on isolated changes to a real JavaScript module."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from compare_coders import MODELS


TASKS = [
    (
        "single-quoted-values",
        "Update extractor.js so webpack chunk maps accept single-quoted values as well as double-quoted values. Preserve existing behavior.",
        "const r=await extractChunkReferences(`n.u=e=>({29:'abcd1234'}[e]+\".c.js\")`); assert(r instanceof Set); assert(r.has('abcd1234.c.js'));",
    ),
    (
        "quoted-numeric-keys",
        "Update extractor.js so webpack chunk maps accept numeric keys written as quoted strings as well as bare numeric keys. Preserve existing behavior.",
        "const r=await extractChunkReferences(`n.u=e=>({\"29\":\"abcd1234\"}[e]+\".c.js\")`); assert(r instanceof Set); assert(r.has('abcd1234.c.js'));",
    ),
    (
        "quiet-extraction",
        "Remove routine console logging from extractor.js. Extraction must return the same chunks without writing to stdout.",
        "let calls=0; console.log=()=>{calls++}; const r=await extractChunkReferences(`n.u=e=>({29:\"abcd1234\"}[e]+\".c.js\")`); assert(r.has('abcd1234.c.js')); assert.strictEqual(calls,0);",
    ),
    (
        "uniform-fallback-result",
        "Make extractChunkReferences return a Set in every branch, including its generic fallback. Preserve the fallback's extracted chunk paths.",
        "const r=await extractChunkReferences(`n.u=e=>foo({29:\"abcd1234\"}[e]);`); assert(r instanceof Set); assert(r.has('abcd1234.js'));",
    ),
    (
        "multiple-manifests",
        "Update extractor.js to collect chunk paths from every webpack .u assignment in one input, instead of returning after the first match. Preserve the Set return type.",
        "const r=await extractChunkReferences(`n.u=e=>({29:\"abcd1234\"}[e]+\".c.js\");x.u=e=>({30:\"fedcba98\"}[e]+\".c.js\");`); assert(r instanceof Set); assert(r.has('abcd1234.c.js')); assert(r.has('fedcba98.c.js'));",
    ),
]


def check(source_dir, assertion):
    test = (
        "const assert=require('assert');\n"
        "const {extractChunkReferences}=require('./extractor.js');\n"
        "(async()=>{ " + assertion + " })().catch(e=>{console.error(e);process.exit(1)});\n"
    )
    (source_dir / "check.js").write_text(test, encoding="utf-8")
    command = [
        "bwrap", "--ro-bind", "/usr", "/usr", "--ro-bind", "/bin", "/bin",
        "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
        "--ro-bind", str(source_dir), "/work", "--dir", "/tmp", "--proc", "/proc",
        "--dev", "/dev", "--unshare-net", "--setenv", "HOME", "/tmp",
        "--chdir", "/work", "/usr/bin/node", "check.js",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    except subprocess.TimeoutExpired:
        return False, "check timed out"
    return result.returncode == 0, result.stderr[-300:]


def run_case(source, task, label):
    name, prompt, assertion = task
    with tempfile.TemporaryDirectory(prefix="oc-eval-repo-") as directory:
        work = Path(directory)
        shutil.copy2(source, work / "extractor.js")
        environment = os.environ.copy()
        environment["PWD"] = directory
        command = [
            "opencode", "run", "--standalone", "--auto", "--agent", "coder-weak",
            "--model", MODELS[label], "--format", "json",
            prompt + " Edit only extractor.js. Do not access tests or the network. Reply briefly.",
        ]
        start = time.monotonic()
        try:
            run = subprocess.run(command, cwd=directory, env=environment,
                                 capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return {"task": name, "model": label, "passed": False,
                    "seconds": 120, "cost_usd": None, "error": "OpenCode timed out"}
        events = []
        for line in run.stdout.splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        session = next((event.get("sessionID") for event in events if event.get("sessionID")), None)
        cost = sum(event.get("part", {}).get("cost", 0) for event in events
                   if event.get("type") == "step_finish")
        tokens = None
        if session:
            export = subprocess.run(["opencode", "session", "export", session, "--sanitize"],
                                    cwd=directory, env=environment, capture_output=True,
                                    text=True, timeout=10)
            if export.returncode == 0:
                info = json.loads(export.stdout)["info"]
                cost = info.get("cost", cost)
                tokens = info.get("tokens")
        passed, error = check(work, assertion)
        if run.returncode:
            error = (run.stderr or error)[-300:]
        return {"task": name, "model": label, "passed": passed,
                "seconds": round(time.monotonic() - start, 2),
                "cost_usd": round(cost, 8), "tokens": tokens, "session": session,
                "error": "" if passed else error}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Path to source-maps-downloader/extractor.js")
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(run_case, source, task, label): (task[0], label)
                   for task in TASKS for label in MODELS}
        results = []
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{len(results)}/{len(futures)} {result['task']} {result['model']} "
                  f"pass={result['passed']} cost=${result['cost_usd']}", flush=True)
    results.sort(key=lambda result: (result["task"], result["model"]))
    args.results.parent.mkdir(parents=True, exist_ok=True)
    args.results.write_text(
        "".join(json.dumps(result, separators=(",", ":")) + "\n" for result in results),
        encoding="utf-8",
    )
    for label in MODELS:
        subset = [result for result in results if result["model"] == label]
        print(label, sum(result["passed"] for result in subset), len(subset),
              round(sum(result["cost_usd"] or 0 for result in subset), 6))


if __name__ == "__main__":
    main()
