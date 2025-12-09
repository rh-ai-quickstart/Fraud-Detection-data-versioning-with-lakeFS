#1/bin/bash

# Function: print usage and exit
usage_and_exit () {
    echo
    echo $1
    echo
    echo "Usage: deploy.sh <project_name>"
    echo
    echo "Example: deploy.sh lakefs"
    echo
    exit 1
}

# Validate a project name is included
if [ $# -lt 1 ]; then
    usage_and_exit "Must include project to deploy to"
elif [ $# -gt 1 ]; then
    usage_and_exit "Too many arguments"
fi

# Create the project if it doesn't already exist
oc get project $1 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "$1 project already exists. Switching to it."
    oc project lakefs
else
    echo "Creating new project $1 and switching to it."
    oc new-project $1
fi
echo

# Deploy minio
echo "Deploying MinIO and creating storage buckets"
echo
oc apply -f ./manifests/minio-for-lakefs.yaml
sleep 30
echo

# Create lakeFS config and storage in a config map
echo "Creating configmap with lakeFS configuration"
echo
oc apply -f ./manifests/lakefs-config-job.yaml
sleep 10
echo

# Deploy lakeFS
echo "Deploying lakeFS with configuration in configmap"
echo
helm install my-lakefs ./helm/lakefs
sleep 30
echo

# Create repos in lakeFS
echo "Creating data repos in lakeFS"
echo
oc apply -f ./manifests/lakefs-repos-job.yaml
sleep 30
echo
echo "Done!"
exit 0
