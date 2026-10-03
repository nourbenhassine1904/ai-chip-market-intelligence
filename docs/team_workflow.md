# Team Workflow

The project is maintained by four students. Keep `main` as the stable branch.
Do not develop directly on `main`; use a dedicated branch for each substantial
task. Suggested branch names include `feature/data-eda`, `feature/arima`,
`feature/var-vecm`, `feature/garch`, `feature/lstm-gru`,
`feature/evaluation` and `docs/report`.

## Workflow

1. `git checkout main`
2. `git pull origin main`
3. `git checkout -b feature/nom-de-la-tache`
4. Make and review the task changes.
5. `git add <files>`
6. `git commit -m "type: description claire"`
7. `git push -u origin feature/nom-de-la-tache`
8. Open a pull request targeting `main`.
9. Another team member reviews the pull request.
10. Merge after review.

Use the actual task branch name in place of `feature/nom-de-la-tache`.
Resolve review feedback on the branch before merging.

## Commit conventions

- `feat:` — new project capability or analysis step
- `fix:` — correction
- `docs:` — documentation change
- `refactor:` — code restructuring without changing intended behavior
- `test:` — test changes
- `chore:` — maintenance and project setup

Examples:

- `feat: add Yahoo Finance data loader`
- `feat: add ADF and KPSS stationarity tests`
- `fix: align trading dates across assets`
- `docs: document VAR methodology`
