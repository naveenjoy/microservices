#!/usr/bin/env python
################################################################################
#Author: Naveen Joy
#Return the floating ip for the server
#Usage: get_floating_ip.py <server_name>
##############################################################################
from __future__ import print_function
import sys, os
from inventory import Inventory

def get_floating_ip(server_name):
    intry = Inventory()
    return intry.getFloatingIpFromServerForNetwork(server_name)

def main(args):
    try:
        server_name = str(args[1]).strip()
        floating_ip = get_floating_ip(server_name)
        docker_cert_path = os.environ.get('DOCKER_CERT_PATH')
        with open("%s.env"% server_name, 'wt') as f:
            f.write("export DOCKER_HOST=tcp://%s:2376\n" % floating_ip)
            f.write("export DOCKER_TLS_VERIFY=1\n")
            if docker_cert_path:
                f.write("export DOCKER_CERT_PATH=%s\n" % docker_cert_path)
    except IndexError:
        print("Usage: get_floating_ip <server_name>")

if __name__ == "__main__":
    main(sys.argv)