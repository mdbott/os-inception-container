#!/bin/groovy

def moduleNames = ['os-inception', 'openshift-ansible']
def buildImage(m) {
	return {
		dir(m) {
			sh "podman build -t '${env.IMG_PREFIX}/${m}:${env.IMG_TAG}' ."
		}
	}
}

def pushImage(m) {
	return {
		dir(m) {
			sh "podman push '${env.IMG_PREFIX}/${m}:${env.IMG_TAG}'"
		}
	}
}


pipeline {
	agent any

	options {
		gitLabConnection('consulting-gitlab')
	}

	triggers {
		gitlab(triggerOnPush: true, triggerOnMergeRequest: true, branchFilterType: 'All')
	}

	environment {
		IMG_PREFIX = "${env.LAB_REGISTRY}/funkytown"
		IMG_TAG = '1.0.0'
	}

	stages {
		stage('Build') {
			steps {
				script {
					parallel moduleNames.collectEntries { m -> [(m): buildImage(m)]}
				}
			}
		}

		stage('Deploy') {
			when {
				branch 'master'
			}
			steps {
				script {
					parallel moduleNames.collectEntries { m -> [(m): pushImage(m)]}
				}
			}
		}
	}

	post {
		always {
			deleteDir()
//			sh 'podman rmi ${IMAGE_NAME}'
		}
		failure {
			updateGitlabCommitStatus name: 'build', state: 'failed'
		}
		success {
			updateGitlabCommitStatus name: 'build', state: 'success'
		}
	}
}
