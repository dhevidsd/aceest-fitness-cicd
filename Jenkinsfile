// ACEest Fitness & Gym - Jenkins CI/CD pipeline
//
// Required Jenkins setup (see README "Jenkins setup"):
//   * Credentials: 'dockerhub-creds' (username/password or token), 'sonarqube-token' (secret text),
//     'kubeconfig' (secret file) for the target Minikube/Kubernetes cluster.
//   * Agent with python3, docker and kubectl available.
pipeline {
    agent any

    triggers {
        // Poll GitHub for changes every ~2 minutes; a GitHub webhook can also trigger the job.
        pollSCM('H/2 * * * *')
    }

    parameters {
        choice(name: 'DEPLOY_STRATEGY',
               choices: ['rolling', 'bluegreen', 'canary', 'ab', 'shadow', 'all', 'none'],
               description: 'Kubernetes deployment strategy for this build')
        string(name: 'CANARY_WEIGHT', defaultValue: '20', description: 'Canary traffic percentage')
        booleanParam(name: 'PUSH_IMAGE', defaultValue: true, description: 'Push image to Docker Hub')
    }

    environment {
        IMAGE_REPO   = 'dhevishreeds/aceest-fitness'
        SONAR_HOST   = 'http://localhost:9000'
        APP_VERSION  = sh(returnStdout: true,
                          script: "sed -n 's/^VERSION = \"\\(.*\\)\"\$/\\1/p' ACEest_Fitness.py").trim()
        IMAGE_TAG    = "${APP_VERSION}-${BUILD_NUMBER}"
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --oneline'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    . venv/bin/activate
                    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
                    flake8 . --count --max-line-length=100 --statistics
                '''
            }
        }

        stage('Unit Tests + Coverage') {
            steps {
                sh '''
                    . venv/bin/activate
                    mkdir -p reports
                    pytest -v --junitxml=reports/pytest-report.xml \
                           --cov=. --cov-report=xml:reports/coverage.xml --cov-report=html:reports/htmlcov
                '''
            }
            post {
                always {
                    junit 'reports/pytest-report.xml'
                }
            }
        }

        stage('SonarQube Analysis + Quality Gate') {
            steps {
                withCredentials([string(credentialsId: 'sonarqube-token', variable: 'SONAR_TOKEN')]) {
                    // sonar.qualitygate.wait makes the scanner fail the build if the gate fails.
                    sh '''
                        docker run --rm --network host -v "$WORKSPACE:/usr/src" \
                          -e SONAR_HOST_URL="$SONAR_HOST" -e SONAR_TOKEN="$SONAR_TOKEN" \
                          sonarsource/sonar-scanner-cli \
                          -Dsonar.projectVersion="$APP_VERSION" \
                          -Dsonar.qualitygate.wait=true -Dsonar.qualitygate.timeout=300
                    '''
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                sh '''
                    docker build -t $IMAGE_REPO:$IMAGE_TAG -t $IMAGE_REPO:$APP_VERSION -t $IMAGE_REPO:latest .
                    docker build -t $IMAGE_REPO:1.0.0 --build-arg APP_MODULE=versions.ACEest_Fitness_v1_0 .
                    docker build -t $IMAGE_REPO:1.1.0 --build-arg APP_MODULE=versions.ACEest_Fitness_v1_1 .
                '''
            }
        }

        stage('Containerized Tests') {
            steps {
                sh '''
                    docker run --rm $IMAGE_REPO:$IMAGE_TAG pytest -v
                    docker rm -f aceest-smoke-$BUILD_NUMBER 2>/dev/null || true
                    docker run -d --name aceest-smoke-$BUILD_NUMBER $IMAGE_REPO:$IMAGE_TAG
                    sleep 5
                    docker exec aceest-smoke-$BUILD_NUMBER python -c \
                      "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/version').read().decode())"
                '''
            }
            post {
                always {
                    sh 'docker rm -f aceest-smoke-$BUILD_NUMBER || true'
                }
            }
        }

        stage('Push to Docker Hub') {
            when { expression { params.PUSH_IMAGE } }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                                  usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
                    sh '''
                        echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
                        for t in $IMAGE_TAG $APP_VERSION latest 1.0.0 1.1.0; do
                            docker push $IMAGE_REPO:$t
                        done
                    '''
                }
            }
            post {
                always {
                    sh 'docker logout || true'
                }
            }
        }

        stage('Deploy to Kubernetes') {
            when { expression { params.DEPLOY_STRATEGY != 'none' } }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh '''
                        chmod +x scripts/*.sh
                        kubectl get namespace aceest >/dev/null 2>&1 || scripts/deploy.sh init
                        if [ "$DEPLOY_STRATEGY" = "canary" ]; then
                            scripts/deploy.sh canary "$IMAGE_TAG" "$CANARY_WEIGHT"
                        else
                            scripts/deploy.sh "$DEPLOY_STRATEGY" "$IMAGE_TAG"
                        fi
                        kubectl -n aceest get deploy,svc,ingress -o wide
                    '''
                }
            }
            post {
                failure {
                    // deploy.sh already reverted to the last stable version (rollout undo /
                    // colour kept / canary weight 0); use scripts/rollback.sh for manual rollback.
                    echo "Deployment failed; last stable version kept/restored for ${params.DEPLOY_STRATEGY}."
                }
            }
        }

        stage('Package Build Artifact') {
            steps {
                sh '''
                    mkdir -p dist
                    tar czf dist/aceest-fitness-$IMAGE_TAG.tar.gz \
                        ACEest_Fitness.py app.py versions requirements.txt Dockerfile k8s scripts
                    echo "$IMAGE_REPO:$IMAGE_TAG" > dist/image-$IMAGE_TAG.txt
                '''
                archiveArtifacts artifacts: 'dist/*, reports/**', fingerprint: true
            }
        }
    }

    post {
        success {
            echo "ACEest Fitness ${APP_VERSION} (build ${BUILD_NUMBER}) delivered successfully."
        }
        failure {
            echo 'ACEest Fitness pipeline failed. Check the logs above.'
        }
    }
}
