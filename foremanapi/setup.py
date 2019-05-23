#!/usr/bin/env python

import setuptools

setuptools.setup(name="foremanapi",
                 version="1.0",
                 description= "Manage and distribute an Openstack overcloud configuration",
                 author="iTEAM",
                 author_email="cloudteam-support@cbr.lab",
                 url="https://westworld.usersys.redhat.com:8090/stash/projects/ITEAM/repos/foremanapi/browse",
                 install_requires=['requests'],
                 packages=['foremanapi']
                 )
