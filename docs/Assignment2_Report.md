# ACEest Fitness & Gym — CI/CD Pipeline Implementation Report

**Student:** DHEVI SHREE D S (BITS ID 2025TM93120)  
**Course:** Introduction to DevOps (CSIZG514/SEZG514) — Assignment 2  
**Repository:** https://github.com/dhevidsd/aceest-fitness-cicd  
**Container registry:** https://hub.docker.com/r/dhevishreeds/aceest-fitness

## 1. CI/CD Architecture Overview

Assignment 1 delivered the ACEest Flask application, a 23-test Pytest suite, a Dockerfile, a GitHub
Actions workflow and a basic Jenkins build. Assignment 2 extends that into an end-to-end
pipeline that takes every commit from source control, through quality gates, to a
Kubernetes cluster using five progressive delivery strategies.

```
Developer ──git push──▶ GitHub ──pollSCM (H/2)──▶ Jenkins pipeline
                          │                         │
                          └─▶ GitHub Actions (PR/push CI)
Jenkins: Checkout → Lint (flake8) → Pytest + coverage → SonarQube + Quality Gate
       → Docker build (1.0.0 / 1.1.0 / 2.0.0-<build>) → Pytest inside container
       → Push to Docker Hub → Deploy to Minikube (strategy parameter) → Archive artifacts
Kubernetes (namespace aceest, ingress-nginx):
       Rolling | Blue-Green | Canary | A/B Testing | Shadow   (+ scripted rollback)
```

**Application versions.** `ACEest_Fitness.py` is the latest release (2.0.0). Earlier releases
are kept in `versions/` (1.0.0: programs and calories; 1.1.0: clients and BMI). Version 2.0.0
adds client deletion and workout logging. Every version serves `/version` and an
`X-App-Version` header with the version and deployment track, so you can see which version
answered each request. One Dockerfile builds any version through the `APP_MODULE` build argument.

**Pipeline stages (Jenkinsfile).**

| Stage | Tooling | Gate / output |
|---|---|---|
| Trigger | `pollSCM('H/2 * * * *')` on GitHub | New commit starts a build |
| Lint | flake8 | Syntax errors and style violations fail the build |
| Unit tests | Pytest + pytest-cov | 42 tests, JUnit report, coverage XML/HTML |
| Static analysis | SonarQube + sonar-scanner (`sonar.qualitygate.wait=true`) | Build fails if the *Sonar way* gate fails |
| Build | Docker | Images `<ver>-<build>`, `<ver>`, `latest`, `1.0.0`, `1.1.0` |
| Container tests | `docker run … pytest` + `/version` smoke test | Validates the exact image to be deployed |
| Registry | Docker Hub `dhevishreeds/aceest-fitness` | Versioned, immutable tags |
| Deploy | kubectl + `scripts/deploy.sh <strategy>` | Health-checked rollout with auto-rollback |
| Artifacts | `archiveArtifacts` | Source bundle, image reference, test/coverage reports |

**Deployment strategies (Minikube, ingress-nginx).** Each strategy has its own manifests under
`k8s/`, an ingress host (`<strategy>.aceest.local`) and a NodePort (30080–30084).

| Strategy | Mechanism | Rollback |
|---|---|---|
| Rolling Update | `maxSurge 1, maxUnavailable 0`, readiness probes on `/health` | `rollout undo` to the last revision not marked failed |
| Blue-Green | Two full deployments; the live Service selector points at one colour; the idle colour is reachable at a preview host and smoke-tested before switching | Patch the selector back (takes about 3 s) |
| Canary | Second ingress with `canary-weight` (default 20%); `promote-canary` moves the image to stable | Set the weight to 0 and undo the canary deployment |
| A/B Testing | Variant B selected by header `X-User-Group: B` or cookie `ab_group` | Remove the routing rules, so all users get A |
| Shadow | `mirror-target` sends a copy of live traffic to the shadow deployment; its responses are discarded | Remove the mirror annotation and undo |

## 2. Verification Results

- **Tests:** 42 Pytest cases pass locally and inside the container image (coverage 97.7%).
- **SonarQube:** Quality Gate *Passed*; 0 bugs, 0 vulnerabilities, 0 code smells, 0 hotspots,
  0% duplication, A/A/A ratings (see `docs/sonarqube/sonarqube-report.md`).
- **Rolling update:** 400 of 400 health requests sent during the 1.1.0 → 2.0.0 rollout returned HTTP 200.
- **Blue-green:** 150 of 150 requests returned 200 during the switch. A deployment with a broken image
  left live traffic on the old colour.
- **Canary:** about 20% of 100 requests went to 2.0.0 (51/49 at 50%). Rollback restored 100% stable.
- **A/B:** without the header or cookie, requests got 1.1.0 (variant A); with them, 2.0.0 (variant B).
- **Shadow:** each request to the primary also appeared in the shadow pod's access log; users
  only saw responses from the primary.
- **Failure handling:** deploying a non-existent tag timed out, was labelled
  `aceest/failed=true` and was rolled back automatically. A later manual rollback skipped it.

## 3. Challenges Faced and Mitigation

| Challenge | Mitigation |
|---|---|
| Lab host is ephemeral with no public static IP, so GitHub webhooks cannot reach Jenkins (noted in Assignment 1) | Jenkins polls GitHub with `pollSCM('H/2 * * * *')`; a webhook can replace polling on a host with a public endpoint, with no pipeline change |
| Showing several versions side by side in one cluster | Kept version snapshots in `versions/`, used a single Dockerfile with an `APP_MODULE` build argument, and added `/version` plus the `X-App-Version` header for traceability |
| `kubectl rollout undo` after an automatic rollback went back to the broken revision | Failed ReplicaSets are labelled `aceest/failed=true`; `rollback.sh` picks the newest earlier healthy revision with a different image |
| Ingress-nginx takes about 3 s to pick up new endpoints after a blue-green switch | Health checks before switching, then a settle delay (`SWITCH_SETTLE_SECONDS`) before verifying |
| Setting `canary=false` on the A/B ingress did not stop header routing | Rollback removes the header and cookie routing annotations; deploy adds them back |
| No proof that shadow traffic arrived | Enabled gunicorn access logs (`--access-logfile -`) so mirrored requests show in `kubectl logs` |
| SonarQube flagged CSRF (S4502) on `Flask(__name__)` | The API is stateless JSON without cookie or session auth, so CSRF does not apply. Documented and marked `# NOSONAR` on that line only |
| SonarQube Elasticsearch needs a higher `vm.max_map_count` | Ran SonarQube with `SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true` so the shared host's kernel settings stay unchanged |
| Coverage paths not matching inside the scanner container | `relative_files = True` in the coverage config |
| Docker Hub credentials | Never stored in the repository; Jenkins uses the `dockerhub-creds` credential and `docker login --password-stdin` |

## 4. Key Automation Outcomes

- **Single path to production:** every commit is linted, tested, scanned, containerised and
  tested again inside the image before any deployment. A failing quality gate stops the pipeline.
- **Traceable, versioned artifacts:** immutable Docker Hub tags (`1.0.0`, `1.1.0`, `2.0.0`,
  `<ver>-<build>`) plus archived Jenkins artifacts and reports for each build.
- **Zero-downtime releases:** readiness probes, `maxUnavailable: 0` and health-checked colour
  switches gave no failed requests during the tests.
- **Risk-controlled releases:** canary weights, header-based A/B routing and traffic mirroring
  let a new version be tested on real traffic with limited or no user impact.
- **One-command rollback:** `scripts/rollback.sh <strategy>` returns any strategy to the last
  stable version, and the pipeline does this automatically when a rollout fails.
- **Reproducibility:** the same Dockerfile, manifests and scripts run on Minikube locally or on any
  managed Kubernetes cluster by changing the `kubeconfig` credential.
