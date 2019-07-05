FROM registry.access.redhat.com/ubi8/python-27

ENV LD_LIBRARY_PATH=/opt/rh/python27/root/usr/lib64

# required due to bugs in older pip versions
RUN pip install -U pip
COPY requirements.txt .
RUN pip install -r requirements.txt
