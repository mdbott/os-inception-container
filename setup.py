#!/usr/bin/env python

import setuptools

setuptools.setup(name="maxhammer",
                 version="2.1.2",
                 description= "Manage and distribute an Openstack configuration via Foreman",
                 author="CBRLAB",
                 author_email="cloudteam-support@cbr.lab",
                 url="https://atlas.org/stash/projects/CBRLAB/repos/maxhammer/browse",
                 install_requires=['Jinja2==2.7.2','PyYAML==3.12','configobj==4.7.2','paramiko>=1.15.2','foremanapi>=1.0','zenlog>=1.1','dirtools>=0.2.0'],
                 packages=['maxhammer'],
                 entry_points = {'console_scripts': ['maxhammer=maxhammer:main'], },
                 )
