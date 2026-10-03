# 11. GitHub Actions

## What is it?

**GitHub Actions** runs **workflows** (YAML files in `.github/workflows/`) on GitHub's machines when something happens: a push, a pull request, a schedule. A workflow has **jobs**; each job runs **steps** on a fresh virtual machine (a **runner**).

## Why this project uses it

Every change is tested automatically, exactly as a reviewer would want: static checks, a security scan of the image, and the complete end-to-end test with real backups, restores and failures. A weekly scheduled run also catches problems from new base images even when nobody changes the code.

**Alternatives:** GitLab CI, Jenkins, CircleCI, Buildkite.

## How it works: the three jobs

[`.github/workflows/ci.yaml`](../.github/workflows/ci.yaml):

| Job | What it does | Fails when |
|---|---|---|
| `static` | `scripts/lint.sh`: ShellCheck, yamllint, ruff, pytest, hadolint, promtool, compose and dashboard validation | any check finds a problem |
| `image` | builds the image, scans it with **Trivy** | a fixable HIGH or CRITICAL vulnerability exists |
| `e2e` | `scripts/e2e.sh` on a fresh runner, then uploads `reports/` | any of the 11 sections fails |

```yaml
  e2e:
    name: End-to-end (backups, drills, PITR, outage, damage, lost key)
    needs: static
    runs-on: ubuntu-24.04
    timeout-minutes: 45
    steps:
      - uses: actions/checkout@v5
      - name: Run the end-to-end test
        run: scripts/e2e.sh
```

`needs: static` means the expensive test only runs when the cheap checks passed. `if: always()` steps publish the results to the job summary and keep the reports as an artifact even when the test fails, and `scripts/down.sh --purge` always cleans up.

### The end-to-end test, section by section
[`scripts/e2e.sh`](../scripts/e2e.sh) writes `reports/e2e-results.md`. Every number in it is measured:

1. fresh start (secrets, certificates, stack, stanza, first full backup)
2. the application writes; incremental and differential backups
3. restore drill (no missing orders, amcheck)
4. repository verification
5. accident (`DROP TABLE orders`) and point-in-time recovery, then a backup and drill on the new timeline
6. storage outage: alert fires, the database keeps working, archiving catches up, no orders lost
7. bit rot: a backup file is damaged in storage; verify and the drill catch it; alerts fire
8. lost encryption key: nothing can be restored without it
9. security checks (network separation, encryption at rest, credentials, anonymous S3 access)
10. monitoring (every series present, no alert left firing)

### Static checks you may not know
- **ShellCheck** finds bugs in shell scripts (unquoted variables, `A && B || C` traps).
- **hadolint** lints Dockerfiles (pinned versions, `pipefail` in `RUN` steps).
- **ruff** lints Python.
- **yamllint** checks YAML style and syntax.

## Where it is integrated

- Workflow: [`.github/workflows/ci.yaml`](../.github/workflows/ci.yaml)
- Static checks, also runnable locally: [`scripts/lint.sh`](../scripts/lint.sh)
- End-to-end: [`scripts/e2e.sh`](../scripts/e2e.sh) (resume from a section with `E2E_FROM=5 scripts/e2e.sh`)

## Try it

```bash
scripts/lint.sh                     # needs shellcheck, yamllint, ruff, pytest and Docker
scripts/e2e.sh                      # the full test (deletes this stack's data first)
E2E_FROM=6 scripts/e2e.sh           # only sections 6-10, on the running stack
```

On GitHub: the repository's **Actions** tab → a run → the job summary shows `e2e-results.md`.

## Common mistakes

- **Testing only on the developer's laptop.** CI proves it works on a clean machine.
- **No cleanup step with `if: always()`.** Failed runs leave state behind (matters for self-hosted runners).
- **Only static checks.** They cannot tell you whether a restore works.

## Check yourself

1. Why does the `e2e` job have `needs: static`?
2. What does the `image` job protect against?
3. Why does the workflow also run on a schedule?

<details><summary>Answers</summary>

1. The end-to-end test is slow; there is no point running it when a quick check already failed.
2. Shipping an image with known, fixable HIGH/CRITICAL vulnerabilities in its packages.
3. Base images and packages change over time even when the code does not; the weekly run notices breakage early.

</details>

Next: [How everything fits together](12-how-it-fits-together.md)
