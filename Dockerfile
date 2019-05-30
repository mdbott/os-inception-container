FROM registry.access.redhat.com/ubi7/ubi

USER root

# Add local repos to container
COPY repos/* /etc/yum.repos.d/
COPY requirements.txt /tmp/
COPY Gemfile /tmp/
COPY maxhammer /tmp/
COPY foremanapi /tmp/

ENV LD_LIBRARY_PATH=/opt/rh/python27/root/usr/lib64

# Install dependencies and prerequisites
RUN echo "### Install/remove RPMs ###" && \
    yum install -y git patch gcc make rubygems rubygem-bundler qemu-img \
      jq-1.5-1.el7 python-devel sshpass python-dns unzip && \
    yum remove -y pyOpenSSL PyYAML python-requests python-ipaddress python-inotify && \
    echo "### Install python modules ###" && \
    curl -o /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py && \
    python /tmp/get-pip.py && \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    echo "### Install ruby gems ###" && \
    bundle install --gemfile=/tmp/Gemfile --clean && \
    echo "### Install maxhammer/foremanapi ###" && \
    cd /tmp/foremanapi && \
    python setup.py sdist && \
    cd /tmp/maxhammer && \
    python setup.py sdist && \
    pip install /tmp/foremanapi/dist/foremanapi-*.tar.gz && \
    pip install /tmp/maxhammer/dist/maxhammer-*.tar.gz && \
    echo "### Clean up ###" && \
    yum clean all && \
    rm -f /etc/yum.repos.d/* && \
    rm -f /tmp/requirements.txt /tmp/Gemfile* && \
    rm -rf /tmp/maxhammer /tmp/foremanapi && \
    echo "### Create container user ###" && \
    useradd -u 1000 cloud-user

USER cloud-user
