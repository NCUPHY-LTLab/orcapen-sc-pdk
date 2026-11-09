<!-- Copy to .github/pull_request_template.md. Reviewers read the Issue from
the line below; keep it even when the PR body also says "Closes". -->
Issue: <https://github.com/OWNER/REPO/issues/N>

Closes #N

## Acceptance

<!-- One box per acceptance criterion of the Issue, ticked with its evidence.
Claude review is opt-in only, including high-risk PRs. Add `claude-review`
only when the Human or Architecture explicitly requests it on the Issue or PR;
carry their explicit Issue request here, never auto-label for risk or size. -->
- [ ] <criterion> — <evidence: test, screenshot, CI run, log line>

## Boundaries

<!-- Review findings answered `document` or `observe` (github-flow Two-stage
findings), one line each, so the Human sees what this PR declares outside the
supported use. Empty if none. -->
- <condition> — document: <where it is stated> | observe: <triage Issue>

## CI change

<!-- Only when .github/ or CI config changes. Plain words for the Human:
what runs on which event before and after, the expected time change, and
what could break. -->

## Open decisions

<!-- Anything the Human must decide; empty if none. -->
