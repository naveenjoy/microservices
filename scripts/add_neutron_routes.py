#! /usr/bin/env python
################################################################################
# Author: Naveen Joy
# Update routes on the Neutron L3 gateway to enable POD connectivity
# Routes are added with a destination_CIDR == NODE_POD_CIDR
# and next_hop == NODE_ETHERNET_ADDRESS, attached to the openstack network
# specified in the settings file. Any existing incorrect next-hop addresses are updated
# All existing routes to other destinations are preserved

# Author Naveen Joy
# Requires the python-novaclient and python-neutronclient packages
################################################################################
from __future__ import print_function
from novaclient import client as nova
from neutronclient.v2_0 import client as neutron
import os, sys, json, yaml
from netaddr import IPNetwork

#The settings file is one level above the current directory
settings_file = os.environ.get('SETTINGS_FILE')

with open(settings_file, "r") as stream:
    settings = yaml.load(stream)

#Nodename to POD CIDR mapping
node_pod_cidr = settings['node_pod_cidr']
tenant_router_name = settings['os_cloud_profile']['os_tenant_router_name']
network_name = settings['os_cloud_profile']['os_network_name']
CREDENTIALS = {
    'VERSION': settings['os_cloud_profile']['os_compute_api_version'],
    'USERNAME': settings['os_cloud_profile']['os_username'],
    'PASSWORD': settings['os_cloud_profile']['os_password'],
    'TENANT_NAME': settings['os_cloud_profile']['os_tenant_name'],
    'AUTH_URL': settings['os_cloud_profile']['os_auth_url']
}
#Assumes Neutron client v2.0 API
class UpdateRoutes:
    def __init__(self):
        self.credentials = self.getOsCredentialsFromEnvironment()
        self.neutron = self.get_neutron_client()
        self.nova = self.get_nova_client()

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

    def get_neutron_client(self):
        "return a neutron client object"
        return neutron.Client(username=self.credentials['USERNAME'],
                              password=self.credentials['PASSWORD'],
                              tenant_name=self.credentials['TENANT_NAME'],
                              auth_url=self.credentials['AUTH_URL'])

    def get_nova_client(self):
        "Get the nova client object"
        return nova.Client(self.credentials['VERSION'], self.credentials['USERNAME'], 
                                                        self.credentials['PASSWORD'], 
                                                        self.credentials['TENANT_NAME'], 
                                                        self.credentials['AUTH_URL'], 
                                                        service_type="compute")

    def get_node_interface_address(self, node_name):
        "Get the interface address of the node attached to the network os_network_name"
        try:
            server = self.nova.servers.list(search_opts={'name':node_name})[0]
        except IndexError as e:
            print("ERROR {0}: server name {1} is not found".format(e, node_name))
            sys.exit(-1)
        
        for addr in server.addresses.get(network_name):
            if addr.get('OS-EXT-IPS:type') == 'fixed':
                return addr['addr']
        return None

    def get_router(self):
        "Return the tenant router object"
        try:
            router = self.neutron.list_routers(name=tenant_router_name)['routers'][0]
            return router
        except IndexError as e:
            print("ERROR {0}: router name {1} is not found".format(e, tenant_router_name))
            sys.exit(-1)

    def get_routes(self):
        "Return the routes object present in the tenant_router"
        router = self.get_router()
        return router['routes']

    def get_router_id(self):
        "Get the tenant router ID"
        router = self.get_router()
        return router['id']
                
    def get_node_name_to_network_map(self):
        "Create a map of nodename to network CIDR"
        return {nodename: str(IPNetwork(cidrIP).cidr) 
                                    for nodename, cidrIP in node_pod_cidr.items() } 


    def compute_routes(self):
        """
        Compute the route list locally with the updated next-hop info for POD CIDRs
        and return the modified routes
        """
        routes = self.get_routes()
        #All existing CIDR values in the route table
        existing_cidrs = []
        #CIDR mapping to node name
        nodeNetMap = self.get_node_name_to_network_map()
        podCidr2NodeName = {cidr:node_name for node_name, cidr in nodeNetMap.items() }
        #Modify existing route to POD destinations
        for route in routes:
            dest = route['destination']
            existing_cidrs.append(dest)
            if dest in nodeNetMap.values():
                route['nexthop'] = self.get_node_interface_address(podCidr2NodeName[dest])
        #Add new routes if POD CIDR routes do not exist in existing routes
        for cidr in nodeNetMap.values():
            if cidr not in existing_cidrs:
                routes.append({ u'destination':cidr,
                                u'nexthop':self.get_node_interface_address(podCidr2NodeName[cidr]) })
        return routes
            
    def update_routes(self):
        "Update the router with the modified routes"
        router_id = self.get_router_id()
        routes = self.compute_routes()
        self.neutron.update_router(router_id, {u'router':{u'routes':routes}})


if __name__ == "__main__":
    updateRoutes = UpdateRoutes()
    updateRoutes.update_routes()