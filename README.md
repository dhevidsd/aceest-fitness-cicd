# ACEest Fitness & Gym — CI/CD Project

[![CI/CD Pipeline](https://github.com/dhevidsd/aceest-fitness-cicd/actions/workflows/main.yml/badge.svg)](https://github.com/dhevidsd/aceest-fitness-cicd/actions/workflows/main.yml)

A Flask web application for **ACEest Fitness & Gym** management, delivered with a
fully automated CI/CD pipeline using **Pytest**, **Docker**, **GitHub Actions**,
and **Jenkins**.

## Overview

The app exposes a REST API preserving the core domain logic of the original
desktop prototype (see `reference/`):

- **Program calorie factors**: Fat Loss (FL)=22, Muscle Gain (MG)=35, Beginner (BG)=26.
- **Calorie estimate** = round(weight_kg * factor).
- **BMI** = weight_kg / (height_m ** 2) with standard categories.

### API Endpoints

| Method | Endpoint          | Description                                 |
|--------|-------------------|---------------------------------------------|
| GET    | `/` or `/health`  | Health check — returns `{"status":"ok"}`.   |
| GET    | `/programs`       | List programs and calorie factors.          |
| POST   | `/clients`        | Create a client.                            |
| GET    | `/clients`        | List all clients.                           |
| GET    | `/clients/<name>` | Get a single client (404 if missing).       |
| POST   | `/bmi`            | Compute BMI + category.                     |
| POST   | `/calories`       | Estimate calories.                          |

## Local Setup & Execution

\`\`\`bash
git clone https://github.com/dhevidsd/aceest-fitness-cicd.git
cd aceest-fitness-cicd
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
\`\`\`

### Examples

\`\`\`bash
curl http://localhost:5000/health
curl http://localhost:5000/programs
curl -X POST http://localhost:5000/clients -H "Content-Type: application/json" \
  -d '{"name":"Ravi","age":30,"height":175,"weight":80,"program":"Muscle Gain (MG)"}'
\`\`\`

### Running Tests Manually

\`\`\`bash
pytest -v
flake8 . --select=E9,F63,F7,F82 --show-source --statistics
\`\`\`

### Docker

\`\`\`bash
docker build -t aceest-fitness .
docker run --rm -p 5000:5000 aceest-fitness
curl http://localhost:5000/health
docker run --rm aceest-fitness pytest -v
\`\`\`

## CI/CD Integration Logic

### GitHub Actions (Continuous Integration)

Defined in `.github/workflows/main.yml`, triggered on every push and pull request:

- **Build & Lint + Automated Testing** — Python 3.12, install deps, flake8, pytest.
- **Docker Image Assembly & Containerized Tests** — build image, run pytest inside the container, and verify /health responds.

### Jenkins (Primary BUILD & Quality Gate)

Defined in `Jenkinsfile` as a declarative pipeline that pulls the latest code and performs a clean build: Checkout → Install Dependencies → Lint → Test → Build Docker Image. Acts as the secondary validation layer / quality gate before delivery.

## Project Structure

\`\`\`
.
├── app.py
├── requirements.txt
├── tests/test_app.py
├── Dockerfile
├── .dockerignore
├── Jenkinsfile
├── .github/workflows/main.yml
├── reference/Aceestver-3.2.4.py   # original Tkinter desktop baseline
└── README.md
\`\`\`

## License

Released under the MIT License.
