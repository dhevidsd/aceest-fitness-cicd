# SonarQube Report — ACEest Fitness & Gym

- Server: SonarQube Community Build 26.11.0.134175 (local Docker container `sonarqube:community`)
- Project key: `aceest-fitness`, version 2.0.0
- Quality gate: **Sonar way** (default) — enforced in Jenkins with `-Dsonar.qualitygate.wait=true`

| Metric | Value |
|---|---|
| Quality Gate | OK (Passed) |
| Bugs | 0 |
| Vulnerabilities | 0 |
| Security Hotspots | 0 |
| Code Smells | 0 |
| Technical Debt | 0 min |
| Coverage | 97.7 % |
| Duplicated Lines | 0.0 % |
| Lines of Code | 317 |
| Unit Tests | 42 (0 failures) |
| Reliability Rating | A |
| Security Rating | A |
| Maintainability Rating | A |
| Open Issues | 0 |

## Quality gate conditions

| Metric | Comparator | Threshold | Actual | Status |
|---|---|---|---|---|
| new_coverage | LT | 80 | 100.0 | OK |
| new_duplicated_lines_density | GT | 3 | 0.0 | OK |
| new_violations | GT | 0 | 0 | OK |

## Notes

- The first scan reported 3 vulnerabilities (rule `python:S4502`, *CSRF protection disabled*) on `Flask(__name__)`
  in each version. The service is a stateless JSON API with no cookie/session authentication, so CSRF does not apply;
  the lines are annotated with a justification and `# NOSONAR`. The re-scan shows Security Rating A.
- `versions/` holds intentional copies of earlier releases and is excluded from duplication detection (`sonar.cpd.exclusions`).
- Raw API exports: [measures.json](measures.json), [quality-gate.json](quality-gate.json), [issues.json](issues.json).
