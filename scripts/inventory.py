#!/usr/bin/env python
################################################################################
# Dynamic inventory generation for Ansible
# Author lukas.pustina@codecentric.de
#
# This Python script generates a dynamic inventory based on OpenStack instances.
#
# The script is passed via -i <script name> to ansible-playbook. Ansible
# recognizes the execute bit of the file and executes the script. It then
# queries nova via the novaclient module and credentials passed via environment
# variables -- see below.
#
# The script iterates over all instances of the given tenant and checks if the
# instances' metadata have set keys OS_METADATA_KEY -- see below. These keys shall
# contain all Ansible host groups comma separated an instance shall be part of,
# e.g., u'ansible_host_groups': u'admin_v_infrastructure,apt_repos'.
# It is also possible to set Ansible host variables, e.g.,
# u'ansible_host_vars': u'dns_server_for_domains->domain1,domain2;key2->value2'
# Values with a comma will be transformed into a list.
#
# Metadata of an instance may be set during boot, e.g.,
# > nova boot --meta <key=value>
# , or to a running instance, e.g.,
# nova meta <instance name> set <key=value>
#
# *** Requirements ***
# * Python: novaclient module be installed which is part of the nova ubuntu
# package.
# * The environment variables OS_USERNAME, OS_PASSWORD, OS_TENANT_NAME,
# OS_AUTH_URL must be set according to nova.
#
################################################################################
#Updated by: Naveen Joy
################################################################################

from __future__ import print_function
from novaclient import client
import os, sys, json, yaml

#The settings file is one level above the current directory
script_dir = os.path.dirname(os.path.abspath(__file__))
settings_file = os.path.join(os.path.dirname(script_dir), "settings.yaml")

with open(settings_file, "r") as stream:
    settings = yaml.load(stream)


OS_METADATA_KEY = {
    'host_groups': settings['ansible_host_groups_key'],
    'host_vars': settings['ansible_host_vars_key']
}
OS_NETWORK_NAME = settings['os_cloud_profile']['os_network_name']
#If environment variables are not set the credentials are picked up from the settings.yaml file
CREDENTIALS = {
     'VERSION': settings['os_cloud_profile']['os_compute_api_version'],
     'USERNAME': settings['os_cloud_profile']['os_username'],
     'PASSWORD': settings['os_cloud_profile']['os_password'],
     'TENANT_NAME': settings['os_cloud_profile']['os_tenant_name'],
     'AUTH_URL': settings['os_cloud_profile']['os_auth_url']
}

 
class Inventory:
    def __init__(self):
        self.inventory = {}
        self.inventory['_meta'] = { 'hostvars': {} }
        self.credentials = self.getOsCredentialsFromEnvironment()
        self.novaClient = client.Client(self.credentials['VERSION'], self.credentials['USERNAME'], 
                                                        self.credentials['PASSWORD'], 
                                                        self.credentials['TENANT_NAME'], 
                                                        self.credentials['AUTH_URL'], 
                                                        service_type="compute")
    
    
    def getOsCredentialsFromEnvironment(self):
        credentials = {}
        try:
            credentials['VERSION'] = os.environ.get('OS_COMPUTE_API_VERSION', CREDENTIALS['VERSION'])
            credentials['USERNAME'] = os.environ.get('OS_USERNAME', CREDENTIALS['USERNAME'])
            credentials['PASSWORD'] = os.environ.get('OS_PASSWORD', CREDENTIALS['PASSWORD'])
            credentials['TENANT_NAME'] = os.environ.get('OS_TENANT_NAME', CREDENTIALS['TENANT_NAME'])
            credentials['AUTH_URL'] = os.environ.get('OS_AUTH_URL', CREDENTIALS['AUTH_URL'])
        except KeyError as e:
            print("ERROR: environment variable %s is not defined" % e, file=sys.stderr)
            sys.exit(-1)
        return credentials
    
   
    def get_inventory(self):
        for server in self.novaClient.servers.list():
            floatingIp = self.getFloatingIpFromServerForNetwork(server, OS_NETWORK_NAME)
            if floatingIp:
                for group in self.getAnsibleHostGroupsFromServer(server.id):
                    self.addServerToHostGroup(group, floatingIp)
                host_vars = self.getAnsibleHostVarsFromServer(server.id)
                if host_vars:
                    self.addServerHostVarsToHostVars(host_vars, floatingIp)
        self.dumpInventoryAsJson()


    def getAnsibleHostGroupsFromServer(self, serverId):
        metadata = self.getMetaDataFromServer(serverId, OS_METADATA_KEY['host_groups'])
        if metadata:
            return metadata.split(',')
        else:
            return []

    def getMetaDataFromServer(self, serverId, key):
        return self.novaClient.servers.get(serverId).metadata.get(key, None)

    def getAnsibleHostVarsFromServer(self, serverId):
        metadata = self.getMetaDataFromServer(serverId, OS_METADATA_KEY['host_vars'])
        if metadata:
            host_vars = {}
            for kv in metadata.split(';'):
                key, values = kv.split('->')
                values = values.split(',')
                #If length > 1 use the list notation else use the string notation
                host_vars[key] = values if len(values) > 1 else str(values[0])
            return host_vars
        else:
            return None

    def getFloatingIpFromServerForNetwork(self, server, network=OS_NETWORK_NAME):
        try:
            if isinstance(server, str):
                server = self.novaClient.servers.list(search_opts={'name':server})[0]
        except IndexError as e:
            print("ERROR {0}: server name {1} is not found".format(e, server))
            sys.exit(-1)
        
        for addr in server.addresses.get(network):
            if addr.get('OS-EXT-IPS:type') == 'floating':
                return addr['addr']
        return None

    def addServerToHostGroup(self, group, floatingIp):
        host_group = self.inventory.get(group, {})
        hosts = host_group.get('hosts', [])
        hosts.append(floatingIp)
        host_group['hosts'] = hosts
        self.inventory[group] = host_group

    def addServerHostVarsToHostVars(self, host_vars, floatingIp):
        inventory_host_vars = self.inventory['_meta']['hostvars'].get(floatingIp, {})
        inventory_host_vars.update(host_vars)
        self.inventory['_meta']['hostvars'][floatingIp] = inventory_host_vars

    def dumpInventoryAsJson(self):
        print(json.dumps(self.inventory, indent=4))


if __name__ == "__main__":
    inventory = Inventory()
    inventory.get_inventory()
