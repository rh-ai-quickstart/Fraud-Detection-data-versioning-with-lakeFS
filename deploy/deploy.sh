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

error_and_exit () {
    echo
    echo $1
    echo
    echo "To clean up for another attempt, use:"
    echo
    echo "oc delete project $1"
    echo
    exit 1
}

# Validate a project name, and only that, is included
if [ $# -lt 1 ]; then
    usage_and_exit "Must include project to deploy to"
elif [ $# -gt 1 ]; then
    usage_and_exit "Too many arguments"
fi

project=$1

# Create the project if it doesn't already exist
oc get project $project > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "$project project already exists. Switching to it."
    oc project lakefs
else
    echo "Creating new project $project and switching to it."
    oc new-project $project
fi
echo

# Deploy minio
echo "Deploying MinIO and creating storage buckets"
echo
oc apply -f ./manifests/minio-for-lakefs.yaml
if [ $? -ne 0 ]; then
    error_and_exit $project "Error: Failed to apply minio-for-lakefs.yaml"
fi
sleep 30
echo

# Create lakeFS config and storage in a config map
echo "Creating configmap with lakeFS configuration"
echo
oc apply -f ./manifests/lakefs-config-job.yaml
if [ $? -ne 0 ]; then
    error_and_exit $project "Error: Failed to apply lakefs-config-job.yaml"
fi
sleep 10
echo

# Deploy lakeFS
echo "Deploying lakeFS with configuration in configmap"
echo
helm install my-lakefs ./helm/lakefs
if [ $? -ne 0 ]; then
    error_and_exit $project "Error: Failed to install my-lakefs helm chart"
fi
sleep 30
echo

# Create repos in lakeFS
echo "Creating data repos in lakeFS"
echo
oc apply -f ./manifests/lakefs-repos-job.yaml
if [ $? -ne 0 ]; then
    error_and_exit $project "Error: Failed to apply lakefs-repos-job.yaml"
fi
sleep 30
echo
echo "Done!"
exit 0
