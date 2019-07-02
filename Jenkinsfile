#!/bin/groovy

pipeline {
	agent any

	environment {
		IMAGE_NAME = "${env.LAB_REGISTRY}/funkytown/os-inception:1.0.0"
	}

	stages {
		stage('Build') {
			steps {
				sh 'podman build -t ${IMAGE_NAME} .'
			}
		}

		stage('Deploy') {
			when {
				branch 'master'
			}
			steps {
				sh 'podman push ${IMAGE_NAME}'
			}
		}
	}

	post {
		always {
			deleteDir()
//			sh 'podman rmi ${IMAGE_NAME}'
		}
	}
}
