# FunkyTown Dependency Images

This repo contains Dockerfiles that will create container images with the required dependencies for various facets
of the FunkyTown project.

## Prerequisites

* podman

### Issues on older RHEL systems

 Some older Red Hat systems (<= RHEL 7.6?) have issues running rootless containers with podman. You can get around this
 by either running with root privileges, or installing & configuring uidmap through the following COPR repo:
```bash
curl -o /etc/yum.repos.d/rhel7.6-rootless-preview.repo https://copr.fedorainfracloud.org/coprs/vbatts/shadow-utils-newxidmap/repo/epel-7/vbatts-shadow-utils-newxidmap-epel-7.repo
yum install -y shadow-utils46-newxidmap slirp4netns
echo "$UID:10000:65536" >> /etc/subuid
echo "$UID:10000:65536" >> /etc/subgid
```

## os-inception

Contains all required dependencies to execute the os-inception playbooks.

### Prepare build environment

```
git clone {{ this project }}
dnf install podman
podman build -t os-inception:1.0.0 .
podman tag localhost/os-inception:1.0.0 registry.gpslab.cbr.redhat.com/funkytown/os-inception:1.0.0
podman push registry.gpslab.cbr.redhat.com/funkytown/os-inception:1.0.0
```

### Execute playbook inside a container

```
podman pull registry.gpslab.cbr.redhat.com/funkytown/os-inception:1.0.0
podman run -t --privileged -v /etc/puppetlabs:/etc/puppetlabs:rw -v /etc/puppet/cloud_environments:/etc/puppet/cloud_environments:rw -v /etc/hosts:/etc/hosts:rw -v /home/cloud-user:/home/cloud-user:rw registry.gpslab.cbr.redhat.com/funkytown/os-inception:1.0.0 ansible-playbook /home/cloud-user/os-inception/create-openstack-on-openstack.yml --extra-vars "os_project=os14"
```

### TODO

1. ~~Add/install maxhammer and foremanapi python packages~~
1. ~~Update os-inception `create-tenant-and-bastion` playbook to remove dependency installation and RPM removal~~
1. Test (and fix if necessary) `create-tenant-and-bastion` in the container, as opposed to a python virtualenv

## openshift-ansible

Contains required dependencies to execute the `openshift-ansible` playbooks in the lab cloud environment.