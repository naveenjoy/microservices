#!/bin/bash

# Copyright 2014 The Kubernetes Authors All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# The business logic for whether a given object should be created
# was already enforced by salt, and /etc/kubernetes/addons is the
# managed result is of that. Start everything below that directory.
# Updated by: Naveen Joy

KUBECTL=${KUBECTL_BIN:-/usr/local/bin/kubectl}
token_auth_file=${TOKEN_AUTH_FILE:-/srv/kubernetes/known_tokens.csv}
CONTEXT_NAME=cluster1
CA_CERT=${CA_CERT:-}
CLIENT_CERT=${CLIENT_CERT:-}
CLIENT_KEY=${CLIENT_KEY:-}
CLUSTER_NAME=${CLUSTER_NAME:-ClusterOne}
CONFIG_DIR=${CONFIG_DIR:-/srv/kubernetes}
NAMESPACE=${NAMESPACE:-}
MASTER_IP=${MASTER_IP:-192.168.1.1}
MASTER_SECURE_PORT=${MASTER_SECURE_PORT:-8443}

function create-kubeconfig() {
  local -r token=$1
  local -r username=$2
  local -r server=$3
  local -r safe_username=$(tr -s ':_' '--' <<< "${username}")
  if [[ -n "${CA_CERT}" ]]; then
    # If the CA cert and Client Cert is available, put it into the config rather than using
    # insecure-skip-tls-verify.
    read -r -d '' kubeconfig <<EOF
apiVersion: v1
kind: Config
users:
- name: ${username}
  user:
    client-certificate-data: ${CLIENT_CERT}
    client-key-data: ${CLIENT_KEY}
    token: ${token}
clusters:
- name: ${CLUSTER_NAME}
  cluster:
     server: ${server}
     certificate-authority-data: ${CA_CERT}
contexts:
- context:
    cluster: ${CLUSTER_NAME}
    user: ${username}
    namespace: ${NAMESPACE} 
  name: ${CONTEXT_NAME}
current-context: ${CONTEXT_NAME}
EOF
  else
    read -r -d '' kubeconfig <<EOF
apiVersion: v1
kind: Config
users:
- name: ${username}
  user:
    token: ${token}
clusters:
- name: ${CLUSTER_NAME}
  cluster:
     server: ${server}
     insecure-skip-tls-verify: true
contexts:
- context:
    cluster: ${CLUSTER_NAME}
    user: ${username}
    namespace: ${NAMESPACE}
  name: ${CONTEXT_NAME}
current-context: ${CONTEXT_NAME}
EOF
 fi

echo "${kubeconfig}"

}

while read line; do
  IFS=',' read -a parts <<< "${line}"
  token=${parts[0]}
  username=${parts[1]}
  if [[ ! -z "${username}" ]]; then
     create-kubeconfig "${token}" "${username}" "https://${MASTER_IP}:${MASTER_SECURE_PORT}" > "${CONFIG_DIR}/kubeconfig"
  fi
done < "${token_auth_file}"  #Limited to single user only
