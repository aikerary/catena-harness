# Coder routing evaluation

`compare_coders.py` compares Haiku 5.5 and GPT-6 Luna at medium effort through the same `coder-weak` agent. It samples 30 tasks from the official [OpenAI HumanEval dataset](https://github.com/openai/human-eval), gives each run an isolated `task.py`, and checks the edited code against tests that the agent cannot read. Generated code is executed inside a `bubblewrap` sandbox without network access. The JSONL result contains pass/fail, elapsed time, estimated OpenCode cost, and session ID for each run.

On Linux, download the official dataset and run:

```sh
curl -fsSL https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz -o /tmp/HumanEval.jsonl.gz
python evals/compare_coders.py /tmp/HumanEval.jsonl.gz --count 30 --workers 4 --results evals/results/humaneval-30.jsonl
```

The sample is deterministic (`Random(42)`). It measures small Python function edits under this harness. It does not measure multi-file engineering, debugging, long-context work, or orchestration. Use repository-specific tasks and acceptance tests before changing the default coder when the HumanEval results are close.

`compare_extractor.py` adds five isolated tasks against a copy of a real JavaScript module. It never edits the source repository. Each task has a failing baseline, then compares both models using hidden Node assertions in the same network-free sandbox:

```sh
python evals/compare_extractor.py /path/to/source-maps-downloader/extractor.js --results evals/results/extractor-5.jsonl
```

The five tasks cover map parsing, logging, return shape, and collection across multiple webpack manifests. They provide a small repository-level check, not a general software-engineering score. See `REPORT.md` for the recorded run and routing decision.
