FROM registry.access.redhat.com/ubi7/ubi

USER root

# Add local repos to container
COPY repos/* /etc/yum.repos.d/

ENV LD_LIBRARY_PATH=/opt/rh/python27/root/usr/lib64

# Install dependencies and remove conflicting RPMs
RUN yum install -y git patch gcc make rubygems rubygem-bundler qemu-img \
      jq-1.5-1.el7 python-devel sshpass python-dns unzip && \
    yum remove -y pyOpenSSL PyYAML python-requests python-ipaddress python-inotify && \
    yum clean all && \
    curl -o /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py && \
    python /tmp/get-pip.py && \
    pip install --upgrade pip && \
    pip install python-openstackclient python-neutronclient decorator==4.4.0 \
      openstacksdk==0.15 ansible==2.6.4 stevedore==1.27 requests==2.18.0 \
      keystoneauth1==3.9.0 ipaddress==1.0.17 notario && \
    rm -f /etc/yum.repos.d/* && \
    useradd -u 1000 cloud-user

USER cloud-user
