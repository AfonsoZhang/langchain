# Conditional HITL review across resume

This reproducer uses public `create_agent`, `HumanInTheLoopMiddleware`,
`InMemorySaver`, and `Command(resume=...)` APIs. The model is scripted; tools only
append their names to a local list. No model service or external tool is contacted.

The model proposes `alpha` and `beta` with fixed IDs, order, and arguments. A `when`
predicate reads a mutable set. Initially only `alpha` requires review. After the
interrupt, the set changes and the reviewer submits the original rejection.

## Observed results

| Selection on resume | Batched result | Per-call result |
| --- | --- | --- |
| `alpha` (stable control) | Reject `call_alpha`; execute beta | Reject `call_alpha`; beta already ran |
| `beta` (same count) | Reject `call_beta`; execute alpha | No rejection; both tools execute |
| `alpha, beta` | Raise decision-count mismatch; execute neither | Reject `call_alpha`; beta already ran |
| empty | No rejection; both tools execute | No rejection; both tools execute |

Sync and async invocation gave identical results. In per-call mode the unreviewed
beta call runs before the initial pause, so it is not reconsidered on resume.

The per-call PR explicitly requires `when` to return the same answer for a given
call across interrupt/resume. The changing-set cases violate that requirement;
they illustrate why it matters, not a claim that live policy changes are supported.
`when=False` means no human review, not denied authorization. This is a controlled
API exercise, not evidence of a production incident or a general ACL bypass.

## Source and environment

Collected on 2026-10-07 with Python 3.12.13 and each checkout's frozen lockfile:

- Master `f5a80b1b04cd4602573f3b35b99d457ba28b8dc9`: LangChain 1.4.3,
  langchain-core 1.6.7, LangGraph 1.2.11; batched mode only.
- [PR #41062](https://github.com/langchain-ai/langchain/pull/41062), head
  `4d85bcdb174577137cb92bfaac455b07cc70e36b`: LangChain 1.4.3,
  langchain-core 1.6.6, LangGraph 1.2.13; both modes.

Exact version records and JSONL outputs are adjacent to this README. This evidence
branch is based on the second checkout. It contains no runtime fix.

## Run

From a full checkout of this branch:

```bash
cd libs/langchain_v1
uv sync --frozen
uv run --frozen --no-sync python ../../hitl-when-repro/reproduce.py --per-call
```

To check master, copy `reproduce.py` outside the repository, check out the master
commit above, run `uv sync --frozen` from the same package, and run the copied
script without `--per-call`.

Prepared and executed with Codex assistance. The companion contribution clarifies
the replay contract and adds stable-predicate coverage; it does not change runtime
behavior for changing predicates.
