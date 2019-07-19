FROM registry.access.redhat.com/ubi7/ubi

USER root

# Add local repos to container
COPY repos /etc/yum.repos.d/
COPY requirements.txt /tmp/
COPY Gemfile1 /tmp/
COPY Gemfile2 /tmp/
ADD http://<artifactory server>/artifactory/api/pypi/packages/pip/19.1.1/pip-19.1.1-py2.py3-none-any.whl /tmp/
ADD http://<artifactory server>/artifactory/api/pypi/packages/setuptools/41.0.1/setuptools-41.0.1-py2.py3-none-any.whl /tmp/
ADD http://<artifactory server>/artifactory/api/pypi/packages/source/W/wheel/wheel-0.33.4-py2.py3-none-any.whl /tmp/
COPY pip.conf /root/
COPY .gemrc /root/
COPY maxhammer /tmp/maxhammer
COPY foremanapi /tmp/foremanapi

ENV LD_LIBRARY_PATH=/opt/rh/python27/root/usr/lib64

# Install dependencies and prerequisites
RUN echo "### Install/remove RPMs ###" && \
    yum-config-manager --disable ubi-7 ubi-7-rhah ubi-server-extras-rpms \
    ubi-7-server-optional-rpms ubi-server-rhscl-7-rpms && \
    yum install -y git patch gcc make rubygems rubygem-bundler qemu-img \
      jq-1.5-1.el7 python-devel sshpass python-dns unzip && \
    yum remove -y pyOpenSSL PyYAML python-requests python-ipaddress python-inotify && \
    echo "### Install python modules ###" && \
    curl -o /tmp/get-pip.py http://<repo server>/get-pip.py && \
    python /tmp/get-pip.py --no-index --find-links=/tmp && \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    echo "### Install ruby gems ###" && \
    bundle install --gemfile=/tmp/Gemfile1 --clean && \
    bundle install --gemfile=/tmp/Gemfile2 --clean && \
    echo "### Install maxhammer/foremanapi ###" && \
    cd /tmp/foremanapi && \
    python setup.py sdist && \
    cd /tmp/maxhammer && \
    python setup.py sdist && \
    pip install /tmp/foremanapi/dist/foremanapi-*.tar.gz && \
    pip install /tmp/maxhammer/dist/maxhammer-*.tar.gz && \
    echo "### Clean up ###" && \
    yum clean all && \
    rm -f /etc/yum.repos.d/mirror* && \
    rm -f /tmp/requirements.txt /tmp/get-pip.py /tmp/Gemfile* /tmp/.gemrc /tmp/pip-19.1.1-py2.py3-none-any.whl /tmp/setuptools-41.0.1-py2.py3-none-any.whl /tmp/wheel-0.33.4-py2.py3-none-any.whl && \
    rm -rf /tmp/.bundle /tmp/maxhammer /tmp/foremanapi /tmp/.pip && \
    echo "### Create container user ###" && \
    useradd -u 1000 cloud-user

USER cloud-user
