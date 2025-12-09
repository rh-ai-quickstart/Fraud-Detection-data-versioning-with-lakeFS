#1/bin/bash

# Get cluster access URL and login credential
# read -p "Enter the URL for the cluster API (ie. https://api.my-cluster.my-org.com:6443): " api
# read -s -p "Enter your access token from the OpenShift cluster: " token

# Log in to the cluster
# echo "Logging in to the cluster"
# oc login --token=${token} --server=${api}
# echo

# Change to the lakefs project. It must be created prior to running this script
echo "Setting project to lakefs"
oc project lakefs
echo

# Deploy minio
echo "Deploying MinIO and creating storage buckets"
oc apply -f ./minio-for-lakefs.yaml
sleep 30
echo

# Create lakeFS config and storage in a config map
echo "Creating configmap with lakeFS configuration"
oc apply -f ./lakefs-config-job.yaml
sleep 10
echo

# Deploy lakeFS
echo "Deploying lakeFS with configuration in configmap"
helm install my-lakefs ./helm/lakefs
sleep 30
echo

# Create repos in lakeFS, thereby creating storage buckets in Minio
echo "Creating data repos in lakeFS"
oc apply -f ./lakefs-repos-job.yaml
sleep 30
echo
echo "Done!"
