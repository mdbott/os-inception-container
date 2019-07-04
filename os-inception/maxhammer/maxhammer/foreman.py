import yaml
import json
import re
import os
import yaml
from jinja2 import Template, Environment, FileSystemLoader
from zenlog import logging
from foremanapi import foreman


class Foreman:
    """
    Class for creating an openstack Puppet-driven deployment environment within Foreman
    """

    def __init__(self, clouddata_config, hostgroup_config_path, logger=None):
        """
        :param clouddata_config: de-serialized YAML of clouddata configuration
        :param hostgroup_config: de-serialized YAML of hostgroup configuration
        :return:
        """
        self.clouddata = clouddata_config
        self.hostgroup_config_path = hostgroup_config_path
        self.foremanapi = foreman.ForemanAPI(clouddata_config['buildserver'], 'hammer', 'hammer')
        self.logger = logger or logging.getLogger(__name__)


    def _load_config_from_foreman(self):
        """
        Query the build server to pull back its current knowledge of the cloud environment
        :return:
        """

        # All of these structures represent a map of name to id
        self.hostgroups = self.foremanapi.get_hostgroups()
        self.environments = self.foremanapi.get_environments()
        self.proxyfeatures = self.foremanapi.get_smart_proxy_features()
        self.puppetclasses = self.foremanapi.get_puppetclasses()
        self.domains = self.foremanapi.get_domains()
        self.subnets = self.foremanapi.get_subnets()
        self.realms = self.foremanapi.get_realms()
        self.architectures = self.foremanapi.get_architectures()
        self.operatingsystems = self.foremanapi.get_operatingsystems()
        self.media = self.foremanapi.get_media()
        self.ptables = self.foremanapi.get_ptables()


    def _delete_hostgroups(self):
        """
        Delete any currently-existing versions of the cloud environment hostgroups from the build server
        :return:
        """
        for hostgroup in self.hostgroups:
            if re.match('^' + self.clouddata['name']+'/.*', hostgroup):
                self.logger.info("Deleting hostgroup: %s" % hostgroup)
                self.foremanapi.delete_hostgroup(self.hostgroups[hostgroup])
        if self.clouddata['name'] in self.hostgroups:
            self.logger.info("Deleting base hostgroup: %s" % self.clouddata['name'])
            self.foremanapi.delete_hostgroup(self.hostgroups[self.clouddata['name']])


    def _create_hostgroup_parameters(self, hostgroup_id, hostgroup_config):
        """
        Create hostgroup-specific parameters in Foreman for any listed in the hostgroup template
        :param hostgroup_name: name of the hostgroup as it appears in foreman
        :param hostgroup_config: hostgroup configuration
        :return:
        """
        if not 'hostgroup_parameters' in hostgroup_config or hostgroup_config['hostgroup_parameters'] is None:
            self.logger.debug("No parameters to apply for hostgroup id '{}'".format(hostgroup_id))
            return

        hostgroup_parameters = hostgroup_config['hostgroup_parameters']
        for parameter in hostgroup_parameters:
            self.logger.debug("Setting hostgroup '{}' param {}={}".format(hostgroup_id,
                                                                                  parameter,
                                                                                  hostgroup_parameters[parameter]))
            self.foremanapi.create_hostgroup_parameter(parameter, hostgroup_id, hostgroup_parameters[parameter])


    def _apply_parameter_overrides(self, hostgroup_name, hostgroup_config):
        """
        Apply any puppetclass parameter overrides associated with the hostgroup
        :param hostgroup_name: name of the hostgroup as it appears in foreman
        :param hostgroup_config: hostgroup configuration
        :return:
        """
        if not 'parameterconfig' in hostgroup_config or hostgroup_config['parameterconfig'] is None:
            self.logger.debug("No puppetclass parameters to apply for hostgroup '{}'".format(hostgroup_name))
            return
        hostgroup_parameters = hostgroup_config['parameterconfig']


        if 'puppetclasses' in hostgroup_config:
            hostgroup_puppetclasses = hostgroup_config['puppetclasses']
        else:
            self.logger.warning("No puppetclasses found for hostgroup '{}'".format(hostgroup_name))
            hostgroup_puppetclasses = []

        # build up our list of puppetclass ids corresponding to our configured puppetclasses
        puppetclass_ids = map(lambda puppetclass: self.puppetclasses[puppetclass], hostgroup_puppetclasses)

        # get the smart class parameters assigned against those puppetclass ids in foreman
        smart_class_params = self.foremanapi.get_puppetclass_smart_class_parameters(puppetclass_ids)

        for puppetclass in hostgroup_parameters:
            for parameter in hostgroup_parameters[puppetclass]:
                if parameter not in smart_class_params[puppetclass]['smart_class_parameters']:
                    self.logger.warning(
                            "Parameter '{}' not found for hostgroup '{}' in Foreman".format(parameter,hostgroup_name))
                    raise Exception("Creating of hostgroup '{}' parameters failed.".format(hostgroup_name))

                self.foremanapi.create_parameter_override(hostgroup_name,
                                                          smart_class_params[puppetclass]['smart_class_parameters'][parameter],
                                                          hostgroup_parameters[puppetclass][parameter])


    def process_config(self):
        """
        Build up the hostgroup configuration based on the union of hostgroup templates and
        clouddata configuration
        :param Cloud:
        :param Config:
        :return:
        """

        # Load the current Foreman config
        self._load_config_from_foreman()

        final_docs = {}
        # Iterate over each file found in the hostgroup
        for rootdir, subdirList, fileList in os.walk(self.hostgroup_config_path):
            environ = Environment(loader=FileSystemLoader(rootdir))
            for fname in fileList:

                self.logger.debug("Processing file %s" % fname)

                template = environ.get_template(fname)
                loaded_hostgroups = yaml.load(template.render(cloud=self.clouddata))

                # For each hostgroup we've loaded, move the internal parameterconfig contents
                # out into the base tree of the hostgroup
                for hostgroup in loaded_hostgroups:
                    final_docs[hostgroup] = loaded_hostgroups[hostgroup]

        hostgroupconfig = {'hostgroups': final_docs}
        CloudConfig = dict(hostgroupconfig.items() + self.clouddata.items())
        return CloudConfig


    def cloud_create(self, cloudconfig):
        """
        Create the cloud deployment configuration within foreman
        :param cloudconfig:
        :return:
        """

        # Check if our environment already exists, if so, get its ID
        if not cloudconfig['environment'] in self.environments:
            raise Exception("No cloud environment with name %s exists. Import it into Foreman first."
                            % cloudconfig['environment'])
        environment_id = self.environments[cloudconfig['environment']]
        if environment_id is None:
            raise Exception("Could not find environment ID associated with environment %s." % cloudconfig['environment'])

        # If an environment did exist, check if any hosts in a hostgroup need to be temporarily migrated out
        active_hosts = self.foremanapi.get_hosts_for_environment(environment_id)
        for host in active_hosts:
            # We have hosts to temporarily migrate out prior to deletion
            self.logger.debug("Temporarily clearing hostgroup of host %s" % host['name'])
            hostid =  host['id']
            result = self.foremanapi.set_hostgroup(hostid, hostgroup_id=None)
            if 'error' in result:
                self.logger.error("Unable to clear hostgroup for host %s: %s" %
                                          (host['name'], json.dumps(result['error'])))

        # Delete currently-existing hostgroups, they'll be recreated in the next step
        self._delete_hostgroups()

        # Create the base hostgroup
        basehostgroup = cloudconfig['name']

        # Verify we loaded a Base hostgroup, which is mandatory
        if 'Base' not in cloudconfig['hostgroups']:
            self.logger.error("Missing mandatory Base hostgroup (check for a Base configuration file in %s".format(self.hostgroup_config_path))
            raise Exception("Cloud configuration read error.")

        basepuppetclass_ids = map(lambda basepuppetclass: self.puppetclasses[basepuppetclass], cloudconfig['hostgroups']['Base']['puppetclasses'])
        self.logger.info("Creating the Base Hostgroup: %s" % basehostgroup)

        cloud_hostgroup = self.foremanapi.create_hostgroup(name=basehostgroup,
                                                      environment_id=self.environments[cloudconfig['environment']],
                                                      domain_id=self.domains[cloudconfig['domain']],
                                                      subnet_id=self.subnets[cloudconfig['subnet']],
                                                      realm_id=self.realms[cloudconfig['realm']],
                                                      architecture_id=self.architectures[cloudconfig['architecture']],
                                                      operatingsystem_id=self.operatingsystems[cloudconfig['operatingsystem']],
                                                      media_id=self.media[cloudconfig['media']],
                                                      ptable_id=self.ptables[cloudconfig['ptable']],
                                                      puppet_proxy=self.proxyfeatures[cloudconfig['buildserver']]['id'],
                                                      puppet_ca=self.proxyfeatures[cloudconfig['buildserver']]['id'],
                                                      puppetclass_ids=basepuppetclass_ids)
        parent = cloud_hostgroup['id']
        # apply the smart class parameter overrides for the base hostgroup
        self.logger.debug("Applying the parameter overrides for Hostgroup %s" % basehostgroup)
        self._apply_parameter_overrides(cloudconfig['name'], cloudconfig['hostgroups']['Base'])
        self._create_hostgroup_parameters(parent, cloudconfig['hostgroups']['Base'])

        # We'll treat all hostgroups as a child of 'Base', but..
        # ..TODO: maybe infer parental hierachy based on directory structure of hostgroup files instead?
        child_hostgroups = {hostgroup: cloudconfig['hostgroups'][hostgroup] for hostgroup in cloudconfig['hostgroups'] if hostgroup != 'Base'}
        for hostgroup in child_hostgroups:
            puppetclass_ids = map(lambda puppetclass: self.puppetclasses[puppetclass], child_hostgroups[hostgroup]['puppetclasses'])

            # Create the child hostgroups
            fullhostgroupname = basehostgroup+'/'+hostgroup
            self.logger.info("Creating Hostgroup: %s" % fullhostgroupname)
            child_hostgroup = self.foremanapi.create_hostgroup(name=hostgroup,
                                  parent_id=parent,
                                  puppetclass_ids=puppetclass_ids)

            # apply the smart class parameter overrides
            self.logger.debug("Applying the parameter overrides for Hostgroup %s/%s" % (cloudconfig['name'], hostgroup))
            self._apply_parameter_overrides(fullhostgroupname, child_hostgroups[hostgroup])
            self._create_hostgroup_parameters(child_hostgroup['id'], child_hostgroups[hostgroup])

        # Lastly we want to reassign any previously-assigned hosts back to their rightful hostgroup
        for host in active_hosts:
            # Foreman seems to be smart enough to assign the correct hostgroup id if we supply just the name, so
            # we don't need to do any id lookup
            if 'hostgroup_name' in host:
                self.logger.debug("Restoring hostgroup of host %s to %s" % (host['name'], host['hostgroup_name']))
                self.foremanapi.set_hostgroup(host['id'], hostgroup_name=host['hostgroup_name'])
