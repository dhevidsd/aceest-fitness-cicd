# ACEest Fitness & Gym — CI/CD Project

[![CI/CD Pipeline](https://github.com/dhevidsd/aceest-fitness-cicd/actions/workflows/main.yml/badge.svg)](https://github.com/dhevidsd/aceest-fitness-cicd/actions/workflows/main.yml)

A Flask web application for **ACEest Fitness & Gym** management, delivered with a
fully automated CI/CD pipeline using **Pytest**, **SonarQube**, **Docker / Docker Hub**,
**GitHub Actions**, **Jenkins** and **Kubernetes (Minikube)** with Rolling Update,
Blue-Green, Canary, A/B Testing and Shadow deployment strategies.

- Docker Hub: [dhevishreeds/aceest-fitness](https://hub.docker.com/r/dhevishreeds/aceest-fitness) (tags `1.0.0`, `1.1.0`, `2.0.0`, `latest`)
- SonarQube report: [docs/sonarqube/sonarqube-report.md](docs/sonarqube/sonarqube-report.md)
- Assignment 2 report: [docs/Assignment2_Report.md](docs/Assignment2_Report.md) ([DOCX](docs/Assignment2_Report.docx))

## Overview

The app exposes a REST API preserving the core domain logic of the original
desktop prototype:

- **Program calorie factors**: Fat Loss (FL)=22, Muscle Gain (MG)=35, Beginner (BG)=26.
- **Calorie estimate** = round(weight_kg * factor).
- **BMI** = weight_kg / (height_m ** 2) with standard categories.

### Application Versions

| Version | Module | Features |
|---------|--------|----------|
| 1.0.0 | `versions/ACEest_Fitness_v1_0.py` | Health, programs, calorie estimation |
| 1.1.0 | `versions/ACEest_Fitness_v1_1.py` | + client management, BMI |
| 2.0.0 | `ACEest_Fitness.py` (latest) | + client deletion, workout logging |

Every version exposes `GET /version` (version, deployment track, pod hostname) and an
`X-App-Version` response header, so you can see which version served a request.
`app.py` is kept as a backward-compatible entry point that re-exports `ACEest_Fitness`.

### API Endpoints

| Method | Endpoint                   | Description                                  |
|--------|----------------------------|----------------------------------------------|
| GET    | `/` or `/health`           | Health check — returns `{"status":"ok"}`.    |
| GET    | `/version`                 | Version, deployment track and hostname.      |
| GET    | `/programs`                | List programs and calorie factors.           |
| POST   | `/clients`                 | Create a client.                             |
| GET    | `/clients`                 | List all clients.                            |
| GET    | `/clients/<name>`          | Get a single client (404 if missing).        |
| DELETE | `/clients/<name>`          | Delete a client (v2.0).                      |
| POST   | `/clients/<name>/workouts` | Log a workout `{type, duration_min}` (v2.0). |
| GET    | `/clients/<name>/workouts` | List workouts + total minutes (v2.0).        |
| POST   | `/bmi`                     | Compute BMI + category.                      |
| POST   | `/calories`                | Estimate calories.                           |

## Local Setup & Execution

```bash
git clone https://github.com/dhevidsd/aceest-fitness-cicd.git
cd aceest-fitness-cicd
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python ACEest_Fitness.py
```

### Examples

```bash
curl http://localhost:5000/health
curl http://localhost:5000/version
curl -X POST http://localhost:5000/clients -H "Content-Type: application/json" \
  -d '{"name":"Ravi","age":30,"height":175,"weight":80,"program":"Muscle Gain (MG)"}'
curl -X POST http://localhost:5000/clients/Ravi/workouts -H "Content-Type: application/json" \
  -d '{"type":"Run","duration_min":30}'
```

### Running Tests Manually

```bash
pytest -v --cov=. --cov-report=xml:reports/coverage.xml --junitxml=reports/pytest-report.xml
flake8 . --count --show-source --statistics
```

### SonarQube

```bash
docker run -d --name aceest-sonarqube -p 9000:9000 \
  -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true sonarqube:community
# Create a token in SonarQube (My Account > Security), then:
docker run --rm --network host -v "$PWD:/usr/src" \
  -e SONAR_HOST_URL=http://localhost:9000 -e SONAR_TOKEN=<token> \
  sonarsource/sonar-scanner-cli -Dsonar.qualitygate.wait=true
```

Configuration lives in `sonar-project.properties` (coverage is read from `reports/coverage.xml`).

### Docker

The `APP_MODULE` build argument selects which application version is packaged.

```bash
docker build -t dhevishreeds/aceest-fitness:2.0.0 .
docker build -t dhevishreeds/aceest-fitness:1.1.0 --build-arg APP_MODULE=versions.ACEest_Fitness_v1_1 .
docker build -t dhevishreeds/aceest-fitness:1.0.0 --build-arg APP_MODULE=versions.ACEest_Fitness_v1_0 .
docker run --rm -p 5000:5000 dhevishreeds/aceest-fitness:2.0.0
docker run --rm dhevishreeds/aceest-fitness:2.0.0 pytest -v
```

## Kubernetes Deployment (Minikube)

```bash
minikube start -p aceest --driver=docker --cpus=4 --memory=6g --addons=ingress
scripts/deploy.sh init            # namespace 'aceest' + all manifests under k8s/
curl -H "Host: rolling.aceest.local" http://<minikube-ip>/version
```

| Strategy | Manifest | Endpoint (ingress host / NodePort) | Deploy | Rollback |
|----------|----------|------------------------------------|--------|----------|
| Rolling Update | `k8s/rolling/` | `rolling.aceest.local` / `:30080` | `deploy.sh rolling <ver>` | `rollback.sh rolling` (last good revision) |
| Blue-Green | `k8s/blue-green/` | `bluegreen.aceest.local` / `:30081`; idle colour at `preview.bluegreen.aceest.local` | `deploy.sh bluegreen <ver>` | `rollback.sh bluegreen` (switch colour back) |
| Canary | `k8s/canary/` | `canary.aceest.local` / `:30082` (stable pods only) | `deploy.sh canary <ver> 20`, `deploy.sh promote-canary` | `rollback.sh canary` (weight 0) |
| A/B Testing | `k8s/ab-testing/` | `ab.aceest.local` / `:30083` (A only); header `X-User-Group: B` or cookie `ab_group=always` → B | `deploy.sh ab <ver>` | `rollback.sh ab` (all users → A) |
| Shadow | `k8s/shadow/` | `shadow.aceest.local` / `:30084`; requests mirrored to `aceest-shadow` | `deploy.sh shadow <ver>` | `rollback.sh shadow` (stop mirroring) |

To browse by hostname, add `<minikube-ip> rolling.aceest.local bluegreen.aceest.local
preview.bluegreen.aceest.local canary.aceest.local ab.aceest.local shadow.aceest.local`
to `/etc/hosts`.

Rollback safety: a rollout that does not become healthy within `ROLLOUT_TIMEOUT` (default 120s)
is rolled back automatically. Its ReplicaSet is labelled `aceest/failed=true`, so later
rollbacks skip it and return to the last known-good version. Blue-green only switches traffic
after a smoke test against the idle colour passes.

## CI/CD Integration Logic

### GitHub Actions (Continuous Integration)

Defined in `.github/workflows/main.yml`, triggered on every push and pull request:

- **Build & Lint + Automated Testing** — Python 3.12, install deps, flake8, pytest.
- **Docker Image Assembly & Containerized Tests** — build image, run pytest inside the container, and verify /health responds.

### Jenkins (Build, Quality Gate & Delivery)

Defined in `Jenkinsfile` (declarative). `pollSCM('H/2 * * * *')` polls GitHub and triggers a
build on new commits.

Checkout → Install Dependencies → Lint → Unit Tests + Coverage → SonarQube Analysis + Quality Gate →
Build Docker Images (`<ver>-<build>`, `<ver>`, `latest`, `1.0.0`, `1.1.0`) → Containerized Tests →
Push to Docker Hub → Deploy to Kubernetes (parameter `DEPLOY_STRATEGY`) → Package & Archive
Artifacts (`dist/aceest-fitness-<ver>-<build>.tar.gz`, test and coverage reports).

**Jenkins setup**

- Agent with `python3` (+ `venv`), `docker` and `kubectl`.
- Plugins: Pipeline, Git, JUnit, Credentials Binding, Timestamper.
- Credentials:
  - `dockerhub-creds` — username + Docker Hub access token.
  - `sonarqube-token` — secret text.
  - `kubeconfig` — secret file (e.g. `minikube -p aceest kubectl -- config view --flatten`).

## Project Structure

```
.
├── ACEest_Fitness.py              # latest application (v2.0.0)
├── app.py                         # backward-compatible entry point
├── versions/                      # v1.0.0 and v1.1.0 snapshots
├── tests/                         # pytest suites
├── requirements.txt
├── setup.cfg                      # flake8 + coverage config
├── sonar-project.properties
├── Dockerfile / .dockerignore
├── Jenkinsfile
├── .github/workflows/main.yml
├── k8s/                           # namespace, NodePorts and one folder per strategy
├── scripts/                       # deploy.sh, rollback.sh
├── docs/                          # Assignment 2 report + SonarQube report
└── README.md
```

## License

Released under the MIT License.
