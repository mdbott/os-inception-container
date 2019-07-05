#!/bin/groovy

def modules = ['os-inception', 'openshift-ansible']

def imgName(module) {
	return "${env.IMG_PREFIX}/${module}:${env.IMG_TAG}"
}

def buildImage(module) {
	return {
		dir(module) {
			sh "podman build -t '${imgName(module)}' ."
		}
	}
}

def pushImage(module) {
	return {
		dir(module) {
			sh "podman push '${imgName(module)}'"
		}
	}
}

def deleteImage(module) {
	return {
		dir(module) {
			sh "podman rmi '${imgName(module)}'"
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
					parallel modules.collectEntries { m -> [(m): buildImage(m)]}
				}
			}
		}

		stage('Deploy') {
			when {
				branch 'master'
			}
			steps {
				script {
					parallel modules.collectEntries { m -> [(m): pushImage(m)]}
				}
			}
		}
	}

	post {
		always {
			deleteDir()
			script {
				try {
					parallel modules.collectEntries { m -> [(m): deleteImage(m)]}
				} catch (ignored) {}
			}
		}
		failure {
			updateGitlabCommitStatus name: 'build', state: 'failed'
		}
		success {
			updateGitlabCommitStatus name: 'build', state: 'success'
		}
	}
}
