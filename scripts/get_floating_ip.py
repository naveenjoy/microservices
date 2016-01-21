#!/usr/bin/env python
################################################################################
#Author: Naveen Joy
#Return the floating ip for the server
#Usage: get_floating_ip.py <server_name>
##############################################################################
from __future__ import print_function
import sys
from inventory import Inventory

def main(args):
    try:
        intry = Inventory()
        server_name = str(args[1]).strip()
        print(intry.getFloatingIpFromServerForNetwork(server_name))
    except IndexError:
        print("Usage: get_floating_ip <server_name>")
    
if __name__ == "__main__":
    main(sys.argv)