# Harness adaptation evaluation — 2026-11-05

The `work/clevertwin` harness was tested with OpenCode v2.2.0 and AWS profile `aiker-bot`. Haiku 5.5 and GPT-6 Luna used the same `coder-weak` instructions at medium effort. Each run received a separate workspace, and acceptance tests were hidden from the agent. Costs below are OpenCode's per-session estimates, including cache usage; wall time includes tool and server overhead. The HumanEval dataset SHA-256 was `b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef`; the JavaScript module came from `source-maps-downloader` commit `0e0012ab0d3584b6e7c2bebce4d9544718246920`.

| Sample | Model | Passed | Total estimated cost | Median wall time |
| --- | --- | ---: | ---: | ---: |
| 30 deterministic HumanEval Python edits | Haiku 5.5 | 30/30 | $0.025449 | 11.35 s |
| 30 deterministic HumanEval Python edits | GPT-6 Luna | 30/30 | $0.011341 | 9.11 s |
| 5 isolated JavaScript repository changes | Haiku 5.5 | 5/5 | $0.012742 | 20.57 s |
| 5 isolated JavaScript repository changes | GPT-6 Luna | 5/5 | $0.008185 | 13.74 s |

Both models passed every selected task. Luna was faster and cheaper in both samples, so `coder-weak` remains on Luna medium. Haiku remains assigned to narrow discovery, formatting, and other short specialist work. These results do not establish a quality ranking for complex architecture, long context, or other repositories; continue to route those cases to Luna max and Terra orchestration according to agent scope.

Live smoke checks confirmed that all three Bedrock model IDs respond, including configured Terra and Luna effort variants. Plan/Terra-high, Build/Terra-medium, and Build-strong/Terra-max each delegated to `triage` through the native `subagent` tool and received a linked child session. Build answered a Spanish request in English. OpenCode's effective agent list resolves `build` to Terra medium, `plan` to Terra high, `Build-strong` to Terra max, and `coder-weak` to Luna medium. The effective model list exposes the intended costs and limits for all three custom Bedrock models.

Limitations: This run used a public function benchmark and five changes to one JavaScript module. It did not compare Terra's planning quality across effort settings or test automatic compaction near a context limit. The `#max` variants were accepted in live requests and resolve to `reasoning.effort=max` in OpenCode's effective model configuration; the AWS-side request body was not independently traced.
