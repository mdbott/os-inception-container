#!/usr/bin/env python

import argparse
import os
import sys
import yaml
import logging
import traceback
from maxhammer import foreman, distribution
from colorlog import ColoredFormatter

# Argument defaults
DEFAULT_PUPPETENV_PATH = '/etc/puppet/cloud_environments/'
DEFAULT_ANSIBLEENV_PATH = '/etc/ansible/environments/'
DEFAULT_UNDERCLOUD_HOST = ''
DEFAULT_UNDERCLOUD_USER = 'stack'
DEFAULT_UNDERCLOUD_PORT = '22'
DEFAULT_BUILD_HOSTGROUP = True
DEFAULT_BUILD_OVERCLOUD = True
DEFAULT_BUILD_CEPH = True
DEFAULT_TEMPLATE_PATH = '/home/stack/overcloud'
DEFAULT_OVERCLOUD_ANSIBLE_PATH = '/home/stack/overcloud-ansible'
DEFAULT_PUPPETENV_PREFIX = 'icloud_'
DEFAULT_MANIFEST_FILE = 'maxhammer.yaml'


class Runner():


    def _load_yaml(self, filename):
        """
        Loads YAML from file and returns the parsed result
        :param filename:
        :return:
        """
        with open(filename, 'r') as stream:
            result = yaml.load(stream)
            return result


    def _setup_logging(self, verbosity):
        """
        Setup logging with desired verbosity
        :param verbosity:
        :return:
        """
        # Set custom levels for 3rd-party modules to avoid too much spamming
        logging.getLogger("requests").setLevel(logging.ERROR)
        logging.getLogger("urllib3").setLevel(logging.ERROR)
        logging.getLogger("dirtools").setLevel(logging.WARNING)
        logging.getLogger("paramiko").setLevel(logging.WARNING)

        logger = logging.getLogger(__name__)
        LOGFORMAT = '%(log_color)s%(asctime)s%(reset)s | %(log_color)s%(name)-12s %(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s'
        LOGCOLOUR = {
            'DEBUG':'blue',
            'INFO':'green',
            'WARNING': 'orange',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
        formatter = ColoredFormatter(LOGFORMAT,log_colors=LOGCOLOUR)
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        logger.addHandler(stream)

        logger.setLevel((logging.ERROR - (verbosity*10)))

        return logger

    def _build_hostgroup(self, clouddata_config, hostgroup_config_path):
        """
        (Re-)builds a hostgroup configuration in Foreman
        :param clouddata_config: deserialized clouddata configuration
        :param hostgroup_config_path: path to hostgroup configuration yaml file
        :return:
        """
        # Build the cloud config
        fc = foreman.Foreman(clouddata_config, hostgroup_config_path, logger=self.logger)
        custom_cloud_config = fc.process_config()

        # Create the hostgroups from that config, add the puppetclasses and the associated smart variable overrides
        fc.cloud_create(custom_cloud_config)


    def run(self):
        """
        Main execution
        :return:
        """
        parser = argparse.ArgumentParser(description='Load the cloud config from the environment, '
                                                     'generate the required Cloud Hostgroups & overcloud configuration')

        parser.add_argument('--branch', help='Name of the branch to process')
        parser.add_argument('--puppetenvpath', default=DEFAULT_PUPPETENV_PATH, help='Path to the puppet environments')

        # Connection details for the undercloud host
        parser.add_argument('--overcloudtemplates', default=DEFAULT_TEMPLATE_PATH, help='Path to the generated overcloud templates')
        parser.add_argument('--overcloudansible', default=DEFAULT_OVERCLOUD_ANSIBLE_PATH, help='Path to the generated overcloud ansible config')

        # Controlling build behaviour
        parser.add_argument('--hostgroup',    dest='buildhostgroup', action='store_true', help='Build Hostgroups in Foreman')
        parser.add_argument('--no-hostgroup', dest='buildhostgroup', action='store_false', help='Do not build Hostgroups in Foreman')
        parser.set_defaults(buildhostgroup=DEFAULT_BUILD_HOSTGROUP)

        parser.add_argument('--manifest', help='Path to distribution manifest')
        parser.add_argument('--no-dist', dest='nomanifest', action='store_true', help='Do not perform any distribution')
        parser.add_argument('--no-remote-dist', dest='remotedist', default=True, action='store_false', help='Do not perform distribution to a remote host')
        parser.add_argument('--no-local-dist', dest='localdist', default=True, action='store_false', help='Do not perform distribution to a local destination')

        # Additional behaviour args
        parser.add_argument("-v","--verbose",action="count",dest="verbosity",help="Verbose mode. Can be used multiple times to increase output. Use -vvv for debugging output.")

        # Parse and validate arguments
        args = parser.parse_args()

        # Verify branch as mandatory argument
        if args.branch is None:
            parser.print_help()
            sys.exit(1)

        # initialize logging
        verbosity = args.verbosity
        if args.verbosity == None or args.verbosity < 0:
            verbosity = 0
        self.logger = self._setup_logging(verbosity)

        # validate clouddata arguments
        clouddata_path = os.path.join(args.puppetenvpath, DEFAULT_PUPPETENV_PREFIX + args.branch, 'clouddata','clouddata',args.branch+'.yaml')
        if not os.path.exists(clouddata_path):
            self.logger.error("Unable to find clouddata file (expected: %s)" % clouddata_path)
            sys.exit(1)

        # Load and validate clouddata config
        try:
            clouddata_config = self._load_yaml(clouddata_path)
        except Exception as error:
            self.logger.fatal("Clouddata could not be read (%s): %s" % (clouddata_path,str(error)))
            sys.exit(1)

        # Load and validate hostgroup config
        if not 'buildserver' in clouddata_config:
            self.logger.fatal("Parameter 'buildserver' missing in clouddata")
            sys.exit(1)

        # Are we setting up the hostgroup on Foreman?
        if args.buildhostgroup:
            self.logger.info("Building hostgroups in Foreman.")
            hostgroup_config_path = os.path.join(args.puppetenvpath, DEFAULT_PUPPETENV_PREFIX + args.branch, 'hostgroups')

            # validate our config path exists
            if not os.path.exists(hostgroup_config_path):
                self.logger.error("Unable to find hostgroup config path (expected: %s)" % hostgroup_config_path)
                sys.exit(1)

            self._build_hostgroup(clouddata_config, hostgroup_config_path)
        else:
            self.logger.info("Not building hostgroups in Foreman.")

        # Process our manifest
        if args.nomanifest:
            self.logger.info("Not performing distribution.")
        else:
            if args.manifest:
                manifest_file = args.manifest
            else:
                manifest_file = os.path.join(args.puppetenvpath, DEFAULT_PUPPETENV_PREFIX + args.branch, DEFAULT_MANIFEST_FILE)

            if not os.path.exists(manifest_file):
                self.logger.error("Distribution manifest not found: {}".format(manifest_file))
                sys.exit(1)
            self.logger.info("Distributing configurations using manifest: {}".format(manifest_file))

            source_base = args.puppetenvpath + '/' + DEFAULT_PUPPETENV_PREFIX + args.branch

            try:
                dist = distribution.Distribution(manifest_file, clouddata_config=clouddata_config, source_base=source_base,
                                             send_to_local=args.localdist, send_to_remote=args.remotedist, logger=self.logger)
                if dist.precheck():
                    dist.distribute()
            except Exception as error:
                str_error = traceback.format_exc()
                self.logger.error(str(error))
                self.logger.debug(str_error)
