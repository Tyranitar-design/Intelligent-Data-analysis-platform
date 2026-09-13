# Expert Agent Quick Reference

## How To Use

- If the task is vague, start with `project-manager-senior` or `prompt-engineer`.
- If the task spans multiple streams, start with `agents-orchestrator`.
- If the task makes a factual quality claim, pair the work with `testing-reality-checker` or `testing-evidence-collector`.

## Fast Routing Table

| Task | Primary Expert | Support Experts | Expected Output |
|---|---|---|---|
| Turn a rough idea into a buildable plan | `project-manager-senior` | `prompt-engineer`, `agents-orchestrator` | clarified scope, phased plan, concrete tasks |
| Design or refactor backend APIs, services, schemas | `engineering-backend-architect` | `engineering-security-engineer`, `engineering-code-reviewer` | API shape, service boundaries, data model decisions |
| Build or improve ETL, ingestion, storage, data pipelines | `engineering-data-engineer` | `data-consolidation-agent`, `engineering-backend-architect` | ingestion flow, schema mapping, pipeline structure |
| Build ML or DL workflows, model services, evaluation paths | `engineering-ai-engineer` | `engineering-data-engineer`, `testing-reality-checker` | model workflow, evaluation plan, deployment structure |
| Combine data from multiple sources into one reporting layer | `data-consolidation-agent` | `engineering-data-engineer`, `engineering-technical-writer` | unified dataset, source mapping, aggregation logic |
| Build dashboards, analytics pages, visual components | `engineering-frontend-developer` | `engineering-code-reviewer`, `engineering-technical-writer` | UI implementation plan, component structure, UX-sensitive details |
| Perform security review or harden risky flows | `engineering-security-engineer` | `engineering-code-reviewer`, `engineering-backend-architect` | threat list, concrete security fixes, risk priorities |
| Review code quality before merge or after a big change | `engineering-code-reviewer` | `engineering-security-engineer`, `testing-reality-checker` | issue list, regression risks, missing tests |
| Verify APIs, crawling endpoints, background jobs, integration behavior | `testing-api-tester` | `testing-evidence-collector`, `testing-reality-checker` | reproducible checks, observed results, pass/fail evidence |
| Prove whether a claimed fix actually works | `testing-reality-checker` | `testing-evidence-collector`, `testing-api-tester` | reality check, counterexamples, confidence level |
| Produce handoff docs, architecture notes, onboarding docs | `engineering-technical-writer` | `project-manager-senior`, `engineering-backend-architect` | docs, decision summaries, readable developer guidance |
| Coordinate a multi-track implementation effort | `agents-orchestrator` | `project-manager-senior`, `prompt-engineer` | work split, role assignments, execution order |

## Best Pairings

- `engineering-ai-engineer` + `engineering-data-engineer`
  Best for end-to-end data-to-model workflows.
- `engineering-backend-architect` + `engineering-security-engineer`
  Best for API, auth, task queues, and storage-sensitive work.
- `testing-api-tester` + `testing-evidence-collector`
  Best for proving behavior with concrete evidence.
- `project-manager-senior` + `agents-orchestrator`
  Best for complex changes with multiple moving parts.

## Suggested Priority Order

1. Clarify scope with `project-manager-senior` or `prompt-engineer`
2. Choose the implementation expert
3. Add a verification expert
4. Add `agents-orchestrator` only when the work genuinely spans multiple expert tracks

