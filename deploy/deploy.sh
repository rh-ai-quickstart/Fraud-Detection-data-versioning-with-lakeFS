#1/bin/bash

# Get cluster access URL and login credential
read -p "Enter the URL for the cluster API (ie. https://api.my-cluster.my-org.com:6443): " api
read -s -p "Enter your access token from the OpenShift cluster: " token

# Log in to the cluster
oc login --token=${token} --server=${api}

# Change to the lakefs project. It must be created prior to running this script
oc project lakefs

# Deploy minio
oc apply -f ./minio-for-lakefs.yaml
sleep 30

# Create lakeFS config and storage in a config map
oc apply -f ./lakefs-config-job.yaml
sleep 10

# Deploy lakeFS
helm install my-lakefs ./helm/lakefs
sleep 30

# Create repos in lakeFS, thereby creating storage buckets in Minio
oc apply -f ./lakefs-repos-job.yaml
sleep 30

