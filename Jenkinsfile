#!/bin/groovy

def moduleNames = ['os-inception']
def buildImage(m) {
	return {
		dir(m) {
			sh "podman build -t '${env.IMG_PREFIX}/${m}:${env.IMG_TAG}' ."
		}
	}
}

def pushImage(dir) {
	return {
		dir(dir) {
			sh "podman push '${env.IMG_PREFIX}/${dir}:${env.IMG_TAG}'"
		}
	}
}


pipeline {
	agent any

	environment {
		IMG_PREFIX = "${env.LAB_REGISTRY}/funkytown"
		IMG_TAG = '1.0.0'
	}

	stages {
		stage('Build') {
			steps {
				script {
					parallel moduleNames.collectEntries { m -> [m: buildImage(m)]}
				}
			}
		}

		stage('Deploy') {
			when {
				branch 'master'
			}
			steps {
				script {
					parallel moduleNames.collectEntries { m -> [m: pushImage(m)]}
				}
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
