#!/bin/bash
#This script sets up a microservices environment based on the definitions in settings.yaml
#Author: Naveen Joy

#Usage: 
#./setup.sh                    # execute all playbooks resulting in launching instances, deploying docker and kubernetes
#./setup.sh --tags "instances" # execute launch instances playbook section
#./setup.sh --tags "docker"    # execute docker playbook section
#./setup.sh --tags "kube"      # execute kubernetes playbook section
#./setup.sh --tags "iptables"  # execute iptables playbook section
#./setup.sh --tags "ntp"       # execute ntp playbook section


set -o xtrace
TOP_DIR=$(cd $(dirname "$0") && pwd)


if [[ ! -r ${TOP_DIR}/settings.yaml ]]; then
    echo "missing $TOP_DIR/settings.yaml - cannot proceed"
    exit 1
fi

if [[ ! -r ${TOP_DIR}/hosts ]]; then
    echo "missing $TOP_DIR/hosts - cannot proceed"
    exit 1
fi

packages=( 
    'ansible>=2.0' 
    'python-neutronclient' 
    'python-novaclient' 
    'netaddr' 
    )

for package in "${packages[@]}"; do
    IFS='>=' read -r -a pkg <<< "$package"
    pip freeze | grep -q "${pkg[0]}" || { echo "${pkg[0]} not found. Run: 'sudo pip install ${package}'" >&2 ; exit 1; }
    if [[ -n "${pkg[1]}" ]]; then
        pip freeze | grep -q "${pkg[1]}" || { echo "${pkg[0]} has incorrect version. Run: 'sudo pip install ${package}'" >&2 ; exit 1; }
    fi
done

echo "Launching Instances"
if ansible-playbook -i hosts launch-instances.yml $@; then
#Wait for the instances to boot up
    echo "Waiting for instances to boot"
    sleep 30
    echo "Deploying Docker"
    if ansible-playbook -i ${TOP_DIR}/scripts/inventory.py deploy-docker.yml $@; then
        echo "Deploying Kubernetes"
        ansible-playbook -i ${TOP_DIR}/scripts/inventory.py deploy-kubernetes.yml $@ || { exit 1; }
        if  { [[ -n "$@" ]]  && echo "$@" | grep -q "kube"; } || [[ ! -n "$@" ]]; then
            echo "Validating Cluster"
            ${TOP_DIR}/scripts/validate-cluster.sh
        fi
    fi
fi
