import requests
import json
import logging
import urllib

class ForemanAPI:
    """
    Class for interacting with Foreman's API
    """

    def __init__(self, server, auth_user, auth_passwd, version='v2', use_ssl=True):
        """
        Initialize the class
        :param server: foreman API host
        :param version: API version
        :param use_ssl: use SSL for API calls
        :return:
        """
        if use_ssl:
            self.api_url = "https://" + server + "/api/" + version + "/"
        else:
            self.api_url = "http://" + server + "/api/" + version + "/"
        self.auth_user = auth_user
        self.auth_passwd = auth_passwd

        # Disable the spammy insecure-request warning
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


    def _foreman_api_get(self, url_extension, parameters={}):
        """
        Perform a Foreman API GET
        :param url_extension: call to make on to the foreman web service
        :return:
        """

        # add on additional mandatory parameters
        parameters['per_page'] = '10000'
        param_str = urllib.urlencode(parameters)

        # build our calling URL
        url = self.api_url + url_extension + "?" + param_str

        logging.getLogger().debug("Making API call to URL: %s" % url)
        headers = {'accept': 'version=2,application/json'}
        response = requests.get(url, headers=headers, verify=False, auth=(self.auth_user, self.auth_passwd))
        try:
            response.raise_for_status
        except requests.exceptions.HTTPError as e:
            logging.getLogger().error("HTTP Request status code error: ", e.message)
        result = response.json()
        return result


    def _foreman_api_post(self, url_extension, payload, parameters={}):
        """
        Perform a Foreman API POST
        :param url_extension: call to make on the foreman web service
        :param payload: payload to POST to service
        :return:
        """

        # add on additional mandatory parameters
        parameters['per_page'] = '10000'
        param_str = urllib.urlencode(parameters)

        # build our calling URL
        url = self.api_url + url_extension + "?" + param_str
        headers = {'Content-Type': 'application/json'}

        logging.getLogger().debug("Submitting POST to {0}: {1}".format(url,json.dumps(payload)))
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(self.auth_user, self.auth_passwd))
        try:
            response.raise_for_status
        except requests.exceptions.HTTPError as e:
            logging.getLogger().error("HTTP Request status code error: ", e.message)
        result = response.json()
        return result


    def _foreman_api_put(self, url_extension, payload):
        """
        Perform a Foreman API PUT
        :param url_extension: call to make on the foreman web service
        :param payload: payload to POST to service
        :return:
        """
        url = self.api_url + url_extension
        headers = {'Content-Type': 'application/json'}

        logging.getLogger().debug("Submitting PUT to {0}: {1}".format(url,json.dumps(payload)))
        response = requests.put(url, data=json.dumps(payload), headers=headers, verify=False, auth=(self.auth_user, self.auth_passwd))
        try:
            response.raise_for_status
        except requests.exceptions.HTTPError as e:
            logging.getLogger().error("HTTP Request status code error: ", e.message)
        result = response.json()
        return result


    def _foreman_api_delete(self, url_extension, payload):
        """
        Perform a Foreman API delete
        :param url_extension:
        :param payload:
        :return:
        """
        url = self.api_url + url_extension
        headers = {'accept': 'version=2,application/json'}
        response = requests.delete(url, data=json.dumps(payload), headers=headers, verify=False, auth=(self.auth_user, self.auth_passwd))
        result = response.json()
        return result


    def get_hosts_for_environment(self,environment_id):
        """
        Retrieve the list of hosts assigned to an environment
        :param environment_id: id of environment
        :return:
        """
        environment_path = "environments/{0}/hosts".format(environment_id)
        hostlist = self._foreman_api_get(environment_path)
        result = dict()
        if 'results' in hostlist:
            return hostlist['results']
        elif 'error' in hostlist:
            raise Exception("An error occurred finding hosts for environment {0}".format(environment_id))
        else:
            return []


    def get_hosts_for_hostgroup(self,hostgroup_id):
        """
        Retrieve the list of hosts assigned to a hostgroup
        :param hostgroup_id: foreman internal id of hostgroup
        :return:
        """
        hostlist = self._foreman_api_get('hosts',{'hostgroup_id':hostgroup_id})
        result = dict()
        for x in hostlist:
            result.update({x['name']: x['id']})
        return result


    def get_hostgroups(self):
        hostgrouplist = self._foreman_api_get('hostgroups')['results']
        result = dict()
        for x in hostgrouplist:
            result.update({x['title']: x['id']})
        return result


    def get_environments(self):
        environmentlist = self._foreman_api_get('environments')['results']
        result = dict()
        for x in environmentlist:
            result.update({x['name']: x['id']})
        return result


    def get_puppetclasses(self):
        puppetclasslist = self._foreman_api_get('puppetclasses')['results']
        result = dict()
        for x in puppetclasslist:
            for y in puppetclasslist[x]:
                result.update({y['name']: y['id']})
        return result


    def get_domains(self):
        domainlist = self._foreman_api_get('domains')['results']
        result = dict()
        for x in domainlist:
            result.update({x['name']: x['id']})
        return result


    def get_subnets(self):
        subnetlist = self._foreman_api_get('subnets')['results']
        result = dict()
        for x in subnetlist:
            result.update({x['name']: x['id']})
        return result


    def get_realms(self):
        realmlist = self._foreman_api_get('realms')['results']
        result = dict()
        for x in realmlist:
            result.update({x['name']: x['id']})
        return result


    def get_architectures(self):
        architecturelist = self._foreman_api_get('architectures')['results']
        result = dict()
        for x in architecturelist:
            result.update({x['name']: x['id']})
        return result


    def get_operatingsystems(self):
        operatingsystemlist = self._foreman_api_get('operatingsystems')['results']
        result = dict()
        for x in operatingsystemlist:
            result.update({x['description']: x['id']})
        return result


    def get_media(self):
        medialist = self._foreman_api_get('media')['results']
        result = dict()
        for x in medialist:
            result.update({x['name']: x['id']})
        return result


    def get_ptables(self):
        ptablelist = self._foreman_api_get('ptables')['results']
        result = dict()
        for x in ptablelist:
            result.update({x['name']: x['id']})
        return result


    def get_smart_proxy_features(self):
        smartproxylist = self._foreman_api_get('smart_proxies')['results']
        result = dict()
        for x in smartproxylist:
            proxydict = dict()
            for y in x['features']:
                proxydict.update({y['name']: y['id']})
            result.update({x['name']: {'id': x['id'], 'features': proxydict}})
        return result


    def get_hostgroup_puppetclasses(self, hostgroup_id):
        puppetclasslist = self._foreman_api_get('hostgroups/'+str(hostgroup_id)+'/puppetclasses')['results']
        result = dict()
        for x in puppetclasslist:
            for y in puppetclasslist[x]:
                result.update({y['name']: y['id']})
        return result


    def get_puppetclass_smart_class_parameters(self, puppetclass_id_array):
        result = dict()
        for puppetclass_id in puppetclass_id_array:
            puppetclass = self._foreman_api_get('/puppetclasses/'+str(puppetclass_id))
            smart_parameter_list = puppetclass['smart_class_parameters']
            paramresult = dict()
            for x in smart_parameter_list:
                paramresult.update({x['parameter']: x['id']})
            result.update({puppetclass['name']: {'smart_class_parameters': paramresult}})
        return result


    def get_parameter_override(self, hostgroup, smart_class_parameter_id):
        overridelist = self._foreman_api_get('smart_class_parameters/' +
                                       str(smart_class_parameter_id) + '/override_values')['results']
        result = None
        for override in overridelist:
            if override['match'] == 'hostgroup='+hostgroup:
                result = override['value']
        return result


    def create_parameter_override(self, hostgroup, smart_class_parameter_id, value):
        url = 'smart_class_parameters/' + str(smart_class_parameter_id) + '/override_values'
        data = {'override_value': {'match':     'hostgroup=' + hostgroup,
                                   'value':    value}}
        result = self._foreman_api_post(url, data)
        return result


    def create_hostgroup_parameter(self, parameter, hostgroup_id, value):
        url = 'hostgroups/' + str(hostgroup_id) + '/parameters'
        data = {'parameter': {'name':     parameter,
                              'value':     value}}
        result = self._foreman_api_post(url, data)
        return result


    def update_host(self, host_id, params):
        url = 'hosts/' + str(host_id)
        data = {'host': params }
        result = self._foreman_api_put(url, data)
        return result


    def set_hostgroup(self, host_id, hostgroup_id=None, hostgroup_name=None):
        # Reject submissions that have both an ID and a Name, in case they conflict
        if hostgroup_id is not None and hostgroup_name is not None:
            raise Exception("Supply either a hostgroup ID or a Name, using both is not supported")

        # Handling the case where we want to clear the hostgroup
        if hostgroup_id is None and hostgroup_name is None:
            return self.update_host(host_id, {"hostgroup_id": None})

        # Otherwise update based on whichever value is set
        if hostgroup_id is not None:
            return self.update_host(host_id, {"hostgroup_id": hostgroup_id})
        elif hostgroup_name is not None:
            return self.update_host(host_id, {"hostgroup_name": hostgroup_name})


    def update_smart_class_parameter(self, smartclassparameterid, smartclassoverrideid, hostgroup, overridevalue ):
        url = "smart_class_parameters" + smartclassparameterid + "/override_values/" + smartclassoverrideid
        payload = {'override_value': {'match': 'hostgroup=' + hostgroup, 'value': overridevalue}}
        result = self._foreman_api_put(url, payload)
        return result


    def create_hostgroup(self, name, parent_id=None, environment_id=None, puppet_proxy=None, puppet_ca=None,
                         domain_id=None, subnet_id=None, realm_id=None, architecture_id=None, operatingsystem_id=None,
                         media_id=None, ptable_id=None, puppetclass_ids=None):
        url = "hostgroups"
        data = {'hostgroup': {'name':               name,
                              'environment_id':     environment_id,
                              'puppet_proxy_id':    puppet_proxy,
                              'puppet_ca_proxy_id': puppet_ca,
                              'parent_id':          parent_id,
                              'domain_id':          domain_id,
                              'subnet_id':          subnet_id,
                              'realm_id':           realm_id,
                              'architecture_id':    architecture_id,
                              'operatingsystem_id': operatingsystem_id,
                              'medium_id':          media_id,
                              'ptable_id':          ptable_id,
                              'puppetclass_ids':    puppetclass_ids}}
        result = self._foreman_api_post(url, data)
        return result


    def delete_hostgroup(self, hostgroup_id):
        try:
            url = "hostgroups/" + str(hostgroup_id)
            payload = {'id': str(hostgroup_id)}
            result = self._foreman_api_delete(url, payload)
            return result
        except Exception as error:
            logging.getLogger().error("Hostgroup id " + str(hostgroup_id) + "does not exist: " + str(error))

