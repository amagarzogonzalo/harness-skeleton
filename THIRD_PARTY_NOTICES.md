# Third-party notices

This project contains material adapted from **ECC** (https://github.com/affaan-m/ECC),
commit `90606c8315ee09cafc303515c5f33024db6b9882`, used under the MIT License.
The adapted files are rewritten for this harness: model-specific language was
removed, commands and paths were changed, OWASP references were updated to the
2025 lists, and stack-specific instructions were split into opt-in modules.

## Adapted files

| File in this repository | Adapted from |
|---|---|
| `.opencode/agent/security-reviewer.md` | `prompts/agents/security-reviewer.txt`, `skills/security-review/SKILL.md`, `commands/security.md` |
| `.opencode/agent/critic.md` (pre-existing) | `prompts/agents/code-reviewer.txt` (review stance only) |
| `.opencode/skills/tdd/SKILL.md` | `commands/tdd.md`, `skills/tdd-workflow/SKILL.md`, `prompts/agents/tdd-guide.txt` |
| `.opencode/skills/loop/SKILL.md` | `prompts/agents/loop-operator.txt`, `commands/checkpoint.md` |
| `.opencode/skills/checkpoint/SKILL.md` | `commands/checkpoint.md` |
| `.opencode/skills/harness-audit/SKILL.md` | `commands/harness-audit.md`, `prompts/agents/harness-optimizer.txt` |
| `modules/lang-python/agent/python-reviewer.md` | `prompts/agents/python-reviewer.txt` |
| `modules/lang-rust/agent/rust-reviewer.md` | `prompts/agents/rust-reviewer.txt` |
| `modules/lang-ts/agent/typescript-reviewer.md` | `prompts/agents/code-reviewer.txt`, `commands/code-review.md` |
| `modules/review-ai/agent/agent-architecture-reviewer.md` | `skills/agent-harness-construction/SKILL.md` |

Everything else is original to this project or derived from public specifications
(OWASP Top 10:2025, OWASP ASVS 5.0, OWASP LLM Top 10:2025, SLSA, GitHub Actions
security hardening). Those specifications are not copied into this repository.

## MIT License

Copyright (c) 2026 Affaan Mustafa

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
