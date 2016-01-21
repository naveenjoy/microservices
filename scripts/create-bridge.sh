#!/bin/bash
#Author: Naveen Joy
#Remove docker0 and create the container bridge "cbr0" if it does not exist
#Address cbr0 with the NODE_POD_CIDR

NODE_POD_CIDR=$1
#Flush iptables
iptables -t nat -F

#If docker0 exists remove it
if [[ "$(brctl show | grep docker0 | awk '{print $1}')" == "docker0" ]]; then
  ifconfig docker0 down
  brctl delbr docker0
fi

#Add cbr0 is it does not exist
if [[ "$(brctl show | grep cbr0 | awk '{print $1}')" != "cbr0" ]]; then
   brctl addbr cbr0
fi

#Bring up cbr0 interface
ifconfig cbr0 down
ifconfig cbr0 $NODE_POD_CIDR
ifconfig cbr0 up