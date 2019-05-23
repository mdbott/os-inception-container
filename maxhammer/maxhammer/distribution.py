import os
import yaml
import tempfile
import shutil
import errno
import paramiko
import socket
import logging
from subprocess import Popen, PIPE, STDOUT
from maxhammer import fileutil, processor


def deep_get(dictionary, *keys):
    """
    Safe value-getter for nested-dictionaries.

    For a dictionary suchs as: { key1: { key2: value2 } }
    Use as follows:
      deep_get(dict, 'key1', 'key2')
    :param dictionary:
    :param keys: dictionary keys to lookup in order of nest level
    :return:
    """
    return reduce(lambda d, key: d.get(key, None) if isinstance(d, dict) else None, keys, dictionary)

class Destination:
    """
    Represents a maxhammer delivery destination
    """

    def __init__(self, alias, hostname, port, user, identity_key_file=None, logger=None):

        if None in [alias, hostname, port, user]:
            raise Exception("Missing required distribution configuration items.")

        self._alias = alias
        self._hostname = hostname
        self._port = port
        self._user = user

        self._auth_identity = None
        if identity_key_file is not None:
            self.auth_identity = identity_key_file
        else:
            # Attempt to use the maxhammer runner's local identity key if it exists
            homedir = os.getenv('HOME')
            if homedir:
                dist_key = os.path.join(homedir, '.ssh', 'id_rsa')
                self._auth_identity = dist_key

        self.logger = logger or logging.getLogger(__name__)

    def host(self):
        return self._hostname
    def port(self):
        return self._port
    def user(self):
        return self._user
    def auth_key(self):
        return self._auth_identity


class Distribution:
    """
    Handles distribution of cloud configuration components to the desired destination
    """

    def __init__(self, manifest_path, clouddata_config=None, source_base=None, send_to_remote=True, send_to_local=True,
                 logger=None):
        """
        Initialises the class
        :param manifest_path: Path to distribution config
        :param clouddata_config: De-serialized YAML of clouddata
        :param source_base: Base directory to read file sources from
        :param send_to_remote: Global override on whether to perform remote distribution
        :param send_to_local: Global override on whether to perform local distribution
        :return:
        """
        self.manifest_path = manifest_path
        self.clouddata_config = clouddata_config
        self.source_base = source_base
        self.send_to_remote = send_to_remote
        self.send_to_local = send_to_local
        self.logger = logger or logging.getLogger(__name__)
        self._load_config()


    def _load_config(self):
        """
        Load the configuration
        :return:
        """
        if not os.path.exists(self.manifest_path):
            raise Exception("Distribution config file could not be read: {}".format(self.manifest_path))

        try:
            with open(self.manifest_path, 'r') as stream:
                self.config_data = yaml.load(stream)
        except Exception as error:
            raise Exception("Distribution could file could not be parsed: {}".format(self.manifest_path))

        # validate contents of config
        if 'default_source_base' in self.config_data['maxhammer']:
            self.source_base = self.config_data['maxhammer']['default_source_base']
        if 'default_destination_host' in self.config_data['maxhammer']:
            self.dest_host = self.config_data['maxhammer']['default_destination_host']
        if 'default_destination_port' in self.config_data['maxhammer']:
            self.dest_port = self.config_data['maxhammer']['default_destination_port']
        if 'default_auth_identity' in self.config_data['maxhammer']:
            self.auth_identity = self.config_data['maxhammer']['default_auth_identity']

        self._destinations = self._load_destinations()
        self._verify_config()

    def _load_destinations(self):
        """
        Generate the list of delivery destinations using clouddata and maxhammer's manifest
        :return: List of delivery destinations
        """

        destinations = {}

        # Iterate over all clouddata maxhammer hosts
        if not 'maxhammer' in self.clouddata_config:
            raise Exception("Missing expected stanza 'maxhammer' key in clouddata.")

        dest_cfgs = self.clouddata_config.get('maxhammer')
        if dest_cfgs is None:
            return destinations

        for dest_alias in dest_cfgs:
            dest_cfg = dest_cfgs.get(dest_alias)
            dest_host = dest_cfg.get('host')
            dest_port = dest_cfg.get('port')
            dest_user = dest_cfg.get('user')
            dest_key = dest_cfg.get('dist_key')

            try:
                destination = Destination(alias=dest_alias, hostname=dest_host, port=dest_port,
                                          user=dest_user, identity_key_file=dest_key)
                destinations[dest_alias] = destination
                self.logger.debug("Loading remote destination configuration for alias {}".format(dest_alias))
            except Exception as err:
                raise Exception('Unable to configure maxhammer destination (clouddata alias: {}'.format(dest_alias))

        return destinations

    def _verify_config(self):
        """
        Validate that mandatory config arguments have been supplied
        :return: True if config validates
        """
        if not all((self.clouddata_config,self.source_base)):
            raise Exception("Missing required configuration")

    def _check_all_local_destinations(self):
        """
        Pre-check that all defined local destinations are writable
        :return: True if all local destinations are valid, False otherwise
        """
        modules = deep_get(self.config_data, 'maxhammer', 'process_paths')

        if modules is None:
            return True

        for module in modules:
            module_cfg = modules[module]

            if not 'local_destination' in module_cfg:
                continue
            local_path = self._apply_environment_substitution(module_cfg['local_destination'])

            # check if directory already exists
            if os.path.exists(local_path):
                # it does, try to create a temporary file
                try:
                    testfile = tempfile.TemporaryFile(dir=local_path)
                    testfile.close()
                except OSError as err:
                    if err.errno == errno.EACCES:  # 13
                        self.logger.error("Pre-check of module {} failed: local destination {} is not writable.".format(
                            module,local_path))
                    else:
                        self.logger.error("Pre-check of module {} failed: unable to verify local destination {}, reason: {}".format(
                            module,local_path,str(err)))
                    return False
            else:
                # it doesn't, try to create it
                try:
                    os.makedirs(local_path, mode=0755)
                except OSError as err:
                        self.logger.error("Pre-check of module {} failed: unable to verify local destination {}.".format(
                            module,local_path, str(err)))

        return True

    def _check_remote_destination(self):
        """
        Pre-check that the defined remote destination is valid, can be connected to, and written to.
        :return: True if remote destination is valid, False otherwise
        """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        for alias in self._destinations:
            d = self._destinations.get(alias)
            try:
                ssh.connect(d.host(), d.port(), d.user(), d.auth_key())
                ssh.close()
            except (paramiko.BadHostKeyException, paramiko.AuthenticationException,
                    paramiko.SSHException, socket.error) as e:
                self.logger.error("Pre-check failed: Unable to successfully establish a connection to remote destination '{}@{}:{}', reason: {}".format(
                    d.user(), d.host(), d.port(), str(e)))
                return False
        return True

    def _rsync_to_remote(self, source_path, dest_cfg, remote_path):
        """
        Perform rsync-based delivery to a remote destination
        :param source_path: Source path to rsync
        :param dest_cfg: Destination host configuration
        :param remote_path: Remote path on destination to deliver to
        :return:
        """
        cmd = "rsync -Pavz --rsync-path='mkdir -p {} && rsync' -e 'ssh -i {} -p {}' {}/ {}@{}:{}/".format(remote_path,
                dest_cfg.auth_key(), dest_cfg.port(), source_path, dest_cfg.user(), dest_cfg.host(), remote_path)

        self.logger.debug("Issuing sync to remote host: {}".format(cmd))
        try:
            process = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
            output = process.communicate()
            rc = process.returncode
            if rc:
                raise Exception("Failed to sync to remote host (FROM: {} TO: {}), Rsync return code {}".format(
                    source_path, remote_path, str(rc)))
        except OSError, error:
            error = str(error)
            raise Exception("Failed to sync to remote host (FROM: {} TO: {}), Error: {}".format(
                source_path, remote_path, error))

    def _apply_environment_substitution(self, orig_path):
        """
        Replace the token %environment% within the supplied string with the
        clouddata-defined environment
        :param orig_path: String to apply replacement to
        :return: String with environment token replaced
        """
        if not 'environment' in self.clouddata_config:
            raise Exception("Missing expected 'environment' key in clouddata.")
        return orig_path.replace('%environment%',self.clouddata_config['environment'])

    def _distribute(self, module_cfg, proc_build_dir, dist_staging_dir):
        """
        Distribute a maxhammer module
        :param module_cfg:
        :param proc_build_dir:
        :param dist_staging_dir:
        :return:
        """
        if self.send_to_remote and 'remote_hosts' in module_cfg:
            # Prepare our distribution staging area, minus any files we need to exclude
            remote_destinations = module_cfg['remote_hosts']

            for remote_destination in remote_destinations:
                remote_alias = remote_destination.get('host')
                dest_path = remote_destination.get('destination')

                if remote_alias is None:
                    self.logger.error('Missing mandatory "host" field in remote_hosts manifest entry')
                if dest_path is None:
                    self.logger.error('Missing mandatory "destination" field in remote_hosts manifest entry')

                dest_path = self._apply_environment_substitution(dest_path)
                dest_cfg = self._destinations.get(remote_alias)
                if dest_cfg is None:
                    self.logger.error('Missing clouddata maxhammer definition for destination "{}"'.format(remote_alias))

                fileutil.clone_with_filter(proc_build_dir, dist_staging_dir, job="distribution")
                self.logger.debug("Initiating remote distribution of {} to {}:{}".format(dist_staging_dir, dest_cfg.host(), dest_path))
                self._rsync_to_remote(dist_staging_dir, dest_cfg, dest_path)

        if self.send_to_local and 'local_destination' in module_cfg:
            local_path = self._apply_environment_substitution(module_cfg['local_destination'])

            try:
                os.makedirs(local_path, mode=0755)
            except OSError as error:
                pass

            try:
                shutil.rmtree(local_path)
                shutil.copytree(proc_build_dir, local_path)
            except Exception as error:
                self.logger.error("Unable to create local destination {}: {}".format(local_path, str(error)))

    def _process_module(self, module_name, module_cfg):
        """
        Pre-process and distribute each manifest module
        :param module_name: name of the module
        :param module_cfg: configuration of the module
        :return:
        """

        if not 'sources' in module_cfg:
            raise Exception("Missing source path(s) in configuration of module: {}".format(module_name))
        if not 'remote_destination' and not 'local_destination' in module_cfg:
            raise Exception("Missing either local_destination or remote_destination path " +
                            "in configuration of module: {}".format(module_name))
        if not 'process_method' in module_cfg:
            raise Exception("Missing required 'process_method' for module {}".format(module_name))

        source_list = [os.path.join(self.source_base, d) for d in module_cfg['sources']]
        process_method = module_cfg['process_method']

        if not process_method in ['ansible', 'overcloud', 'none']:
            raise Exception("Don't understand process_method {} for module {}".format(process_method, module_name))

        for source_path in source_list:

            # Verify the source path exists
            if not os.path.exists(source_path):
                raise Exception("Error in configuration for module {}, source path does not exist: {}".format(module_name, source_path))

            # Create a temporary directory to house our post-processed files
            proc_build_dir = tempfile.mkdtemp(module_name)
            # Create a temporary directory to house our to-be-distributed files
            dist_staging_dir = tempfile.mkdtemp(module_name)

            self.logger.debug("Pre-processing {} with method {} into {}".format(source_path, process_method, proc_build_dir))

            proc = processor.Processor(source_path,logger=self.logger)
            if process_method == "ansible":
                proc.run(self.clouddata_config, proc_build_dir, process_method=processor.ANSIBLE)
            elif process_method == "overcloud":
                proc.run(self.clouddata_config, proc_build_dir, process_method=processor.GENERIC)
            elif process_method == "none":
                # Delete the temp dir because copytree wants it to not exist first
                fileutil.clone_with_filter(source_path,proc_build_dir,job="distribution")

            self.logger.info("Distributing module {} source {}".format(module_name, source_path))
            self._distribute(module_cfg, proc_build_dir, dist_staging_dir)

            # clean out our tmp build directories
            shutil.rmtree(proc_build_dir)
            shutil.rmtree(dist_staging_dir)

    def precheck(self):
        """
        Pre-check that all conditions are met for a successful distribution
        :return: True if successful, false otherwise
        """
        success = True
        if self.send_to_local:
            success = success and self._check_all_local_destinations()

        # if self.send_to_remote:
        #     success = success and self._check_remote_destination()

        return success

    def distribute(self):
        """
        Distribute the config to a
        :return:
        """
        modules = self.config_data['maxhammer']['process_paths']

        for module in modules:
            module_cfg = modules[module]
            self._process_module(module, module_cfg)
