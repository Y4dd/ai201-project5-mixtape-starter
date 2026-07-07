# Standardized AI Workflow for the Mixtape Bug Hunt — Design

## Purpose

Project 5 ("Mixtape Bug Hunt") requires fixing bugs from 5 known, already-filed GitHub issues on `Y4dd/ai201-project5-mixtape-starter` (#1–#5, matching `project.md`'s numbering 1:1) through a real SDLC: branch → investigate → fix → test → review → PR → merge → close, each fully documented with a root-cause-analysis entry in `submission.md`. This spec defines one standardized pipeline applied identically to all 5 issues, so each gets the same rigor rather than an ad hoc process that drifts as more issues get worked.

This is a learning exercise (CodePath AI201) — `project.md` explicitly grades the student's own diagnosis skill and prescribes a specific human/AI split ("you find the suspicious code → AI helps you understand it → you verify the diagnosis by reading it yourself"). The workflow below is designed around that constraint, not around fixing bugs as fast as possible.

## Scope

All 5 issues, run one at a time — fully closed (merged, RCA written, GitHub issue closed) before the next one starts. No parallelism: the human confirmation gate (below) requires interactive back-and-forth per issue, which doesn't fit a parallel/worktree model, and `project.md` explicitly wants each RCA written while the investigation is fresh rather than batched.

**Constraint discovered during design:** `.claude/skills` and `.claude/commands` in this repo are sandbox-protected paths (blocked even though the parent `.claude/` directory is otherwise writable) — a custom project-level Claude Code skill or slash-command is not available as the standardization mechanism. Standardization instead comes from this written spec plus disciplined, identical invocation of the Superpowers skills named below, per issue.

## Core principle: human calls the root cause, AI does the legwork

For every issue, the AI never writes a fix based on its own unconfirmed hypothesis. The AI reproduces, traces, and proposes — then stops. The human reads the flagged code and explicitly confirms or rejects before any fix code is written.

## The pipeline (repeated identically for each of the 5 issues)

### Stage 1 — Pick up the issue
- `gh issue view <N> --json title,body,url` — fetches the actual report verbatim. This is the canonical bug description fed to the investigation subagent (GitHub issue bodies already contain the full report, repro steps included — no need to also copy from `project.md` for this).
- `gh issue develop <N> --base bugfix/mixtape --name issue-<N>-<slug> --checkout` — creates the branch off `bugfix/mixtape`, links it to the issue (visible in the issue's "Development" section on GitHub), and checks it out.

### Stage 2 — Investigate (dispatched to a subagent)
Dispatch a fresh `Explore`-type subagent with a self-contained brief: the issue body from Stage 1, the affected service file (per the table in `CLAUDE.md`), and pointers to the already-verified architecture/test-baseline facts in `CLAUDE.md` (so it doesn't re-derive things we already know, e.g. which tests currently fail).

Its job is `systematic-debugging` Phases 1–2 plus the "form a single hypothesis" part of Phase 3, scoped to just this issue: reproduce it, trace the call chain from the route down through the service, compare against a working sibling pattern where one exists. **It must stop at a hypothesis — no fix code, no file edits.**

It returns: the hypothesis ("I think X is the root cause because Y"), the exact file/line, the supporting evidence gathered, and any open uncertainty.

Rationale for using a subagent here specifically: this stage is read-heavy and exploration-noisy. Keeping it out of the main thread means issue #5's investigation doesn't start with 4 prior bugs' worth of exploration transcript behind it.

### Stage 3 — Human confirmation gate
The hypothesis + evidence is relayed to the human as-is, then the AI stops. The human reads the flagged code themselves. The gate is asked the same way every time, as a 3-way choice:
1. Confirmed — implement the fix
2. Not the root cause — re-investigate
3. Let me look first, pause here

Rejecting loops back to Stage 2 with whatever steer the human gives. No fix is written on an unconfirmed hypothesis.

### Stage 4 — Fix & verify
Once confirmed: `test-driven-development` red/green cycle — write one regression test that fails against current code for the confirmed reason, watch it fail correctly, implement the minimal fix, watch it pass. Run the full `pytest tests/` suite (not just the new test) to check for regressions elsewhere, per `project.md`'s explicit side-effect-check requirement. `verification-before-completion` gates any "this is fixed" claim on actual command output. Commit on the issue branch: `fix: <description>`.

### Stage 5 — Document & review
- `gh issue comment <N>` with the confirmed root cause and what changed — posted before the PR exists, as a real paper trail on the ticket.
- `requesting-code-review` dispatches the code-reviewer subagent against `BASE_SHA` (branch point off `bugfix/mixtape`) `..HEAD_SHA` (tip of the issue branch). Critical/Important feedback becomes follow-up commits before proceeding; Minor issues can be noted and skipped with reasoning.
- Finalize the RCA entry (5 required fields) in `submission.md` while the investigation is still fresh.

### Stage 6 — Integrate
- `gh pr create --base bugfix/mixtape --title "fix: ..." --body "Closes #<N>\n\n<RCA summary>"`. Title is the conventional commit message, since squash-merge uses it as the final commit subject.
- Human confirms, then `gh pr merge --squash`. This is what keeps `bugfix/mixtape` at one commit per fix, satisfying `project.md`'s submission checkpoint even though the work happened on a branch.
- **Explicit `gh issue close <N> --comment "Fixed in <squash-sha> on bugfix/mixtape."`** — required because this repo's default branch is `main`, not `bugfix/mixtape`, and GitHub's `Closes #N` auto-close keyword only fires on merge to the default branch. Keeping `Closes #N` in the PR body still creates the cross-reference link; it just doesn't auto-close here.
- Delete the issue branch after merge.

> **Correction to `CLAUDE.md`:** its current workflow section implies `Closes #N` closes the issue on merge. That's only true for merges to the default branch (`main`); since PRs here merge into `bugfix/mixtape`, closing must be done explicitly via `gh issue close`. Update `CLAUDE.md` to reflect this after this spec is approved.

## Cross-issue tracking

One `TaskCreate` task per issue (5 total), each referencing this spec for its stage checklist rather than exploding into per-stage micro-tasks. The order the 5 issues are worked in is not fixed by this pipeline — it's a planning-time decision — the pipeline behaves identically regardless of sequence.

## Escalation paths

- **Investigation subagent can't pin down a hypothesis** (can't reproduce, or evidence inconclusive): it reports that honestly rather than guessing. Human and AI decide together whether to dig further or swap to a different one of the 5 issues, per `project.md`'s Milestone 2 guidance.
- **Human rejects the hypothesis at the gate**: back to Stage 2 with whatever steer is given. Never proceeds to a fix on an unconfirmed hypothesis.
- **Fix doesn't fully resolve it, or breaks other tests**: `systematic-debugging`'s existing rule applies unmodified — under 3 attempts, back to root-cause investigation with the new information; at 3+ failed attempts, stop and raise it as a possible architecture problem instead of trying a 4th patch.
- **Code review flags Critical/Important issues**: fixed as follow-up commits before the PR is merged.
- **An issue's investigation reveals entanglement with another of the 5** (`project.md` notes some bugs share root-cause patterns): surface this explicitly rather than silently fixing two issues in one branch, since that breaks the one-branch/one-PR/one-issue mechanics. Decide together whether to split the fix or file a combined PR that closes both issues.

## Testing conventions

New test files (`test_feed.py` for #2, `test_notifications.py` for #4) follow the existing fixture pattern already in the repo: an in-memory `sqlite:///:memory:` `app` fixture plus hand-built seed fixtures per test file, not dependent on `seed_data.py`'s mutable state. Same convention already recorded in `CLAUDE.md`.

## Skills this pipeline is built from (not reimplemented)

- `systematic-debugging` — Stage 2 (Phases 1–2 + hypothesis) and the escalation rule in Stage 4.
- `test-driven-development` — Stage 4's red/green cycle.
- `requesting-code-review` — Stage 5's reviewer-subagent dispatch.
- `verification-before-completion` — gates any success claim in Stage 4.
- The one piece with no off-the-shelf skill: the Stage 3 human-confirmation gate, added specifically for this project's grading requirements.
