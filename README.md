# os-inception-container

Build a container image with all required dependencies to execute the os-inception playbook

> **NOTE**: Some older Red Hat systems may require podman to be run with root privileges

#### Prepare build environment

```
git clone {{ this project }}
dnf install podman
podman build -t os-inception:1.0.0 .
podman tag localhost/os-inception:1.0.0 registry.gpslab.cbr.redhat.com/funkytown/os-inception:1.0.0
podman push registry.gpslab.cbr.redhat.com/funkytown/os-inception:1.0.0
```

#### Execute playbook inside a container

```
podman pull registry.gpslab.cbr.redhat.com/funkytown/os-inception:1.0.0
podman run -t --privileged -v /etc/puppetlabs:/etc/puppetlabs:rw -v /etc/puppet/cloud_environments:/etc/puppet/cloud_environments:rw -v /etc/hosts:/etc/hosts:rw -v /home/cloud-user:/home/cloud-user:rw registry.gpslab.cbr.redhat.com/funkytown/os-inception:1.0.0 ansible-playbook /home/cloud-user/os-inception/create-openstack-on-openstack.yml --extra-vars "os_project=os14"
```

#### TODO
1. ~~Add/install maxhammer and foremanapi python packages~~
1. ~~Update os-inception `create-tenant-and-bastion` playbook to remove dependency installation and RPM removal~~
1. Test (and fix if necessary) `create-tenant-and-bastion` in the container, as opposed to a python virtualenv
