pipeline {
    agent any

    options {
        timestamps()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
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
                    flake8 . --count --max-line-length=100 --statistics --exit-zero
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest -v --junitxml=report.xml
                '''
            }
            post {
                always {
                    junit 'report.xml'
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t aceest-fitness:${BUILD_NUMBER} .'
            }
        }
    }

    post {
        success {
            echo 'ACEest Fitness BUILD completed successfully.'
        }
        failure {
            echo 'ACEest Fitness BUILD failed. Check the logs above.'
        }
    }
}
