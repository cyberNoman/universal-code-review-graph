# QA Test Plan — Universal Code Review Graph

## Launch Readiness Validation

This directory contains **5 QA agent prompts** — one for each AI model. Paste each file into its respective AI and let it run through every test. All 5 must return **PASS** before we launch.

| Agent File | AI Model | Focus Area |
|------------|----------|------------|
| `claude-qa-agent.md` | Claude / Claude Code | Architecture + Security + Edge cases |
| `kimi-k2-qa-agent.md` | Kimi K2.5 | MCP protocol compliance + Token savings validation |
| `codex-qa-agent.md` | OpenAI Codex / ChatGPT | Code correctness + Python best practices |
| `qwen-qa-agent.md` | Qwen | Multi-language parsing + Cross-file resolution |
| `gemini-qa-agent.md` | Gemini Pro | Documentation + API consistency + UX |

## How to use

1. Open the AI model (Kimi, ChatGPT, Gemini, Qwen, Claude)
2. Copy-paste the entire contents of the corresponding `.md` file
3. Attach / provide access to the `universal-code-graph/` directory
4. Let the AI run all tests and produce a **VERDICT**
5. Collect all 5 verdicts in the checklist below

## Launch Checklist

- [ ] Claude QA Agent — PASS / FAIL
- [ ] Kimi K2.5 QA Agent — PASS / FAIL
- [ ] Codex QA Agent — PASS / FAIL
- [ ] Qwen QA Agent — PASS / FAIL
- [ ] Gemini QA Agent — PASS / FAIL

## Pass Criteria

- **All 5 agents must return PASS** for launch
- Any **FAIL** must include the specific test ID and failure reason
- Fix the issue, re-run only the failed agent
- When all 5 are green, the product is launch-ready
