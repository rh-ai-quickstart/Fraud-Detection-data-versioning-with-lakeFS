# Deployment Guide

In order to set up the environment, there are currently four steps, assuming the OpenShift cluster is already up.

# Pre-requisites
1. OpenShift cluster is deployed
2. The `lakefs` project is created (it can be created with `oc new-project lakefs`)
3. User has `admin` permissions in the `lakefs`namespace

# Deployment Process
The process is very simple. Just follow the steps below. The details of what the script does are explained below.

1. Clone the repo
2. cd to `deploy` directory
3. Make sure you have the cluster API URL and your authentication token handy, as the script will prompt for them
4. Make sure `deploy.sh` is executable and run it

# Cleanup
The `lakefs` project can be deleted, which will delete all of the resources in it, including deployments, secrets, pods, configmaps, etc.
```
oc delete project lakefs
```

# Detailed steps of deploy.sh

1. Prompt user for cluster API URL and authentication token
2. Log `oc` in to the cluster
3. Change to the `lakefs` project
4. Deploy MinIO using the `minio-for-lakefs.yaml` file. This manifest file, when applied to the cluster, will deploy MinIO and create a random root username and password. After this step, you should be able to log into the MinIO console using the `minio-console` route and the generated crendentials stored in the secret.
```
$ oc apply -f minio-for-lakefs.yaml
```
5. Create the lakeFS config file in a configmap using the `lakefs-config-job.yaml` file. This manifest file, when applied to the cluster, will create the config map used to store the *lakeFS* configuration, which is used when it is brought up. This configuration will include the login credentials to the lakeFS console, accessible from its route, and the configuration and credentials lakeFS will use to access the backend MinIO object storage.
```
$ oc apply -f lakefs-config-job.yaml
```
6. Deploy lakeFS using the helm chart. The chart will deploy the lakeFS application and a route to access it.
```
$ helm install my-lakefs ./helm/lakefs
```
7. Create the reposotories in lakeFS, which will create the storage buckets in MinIO, using the `lakefs-repos-job.yaml` file.
```
$ oc apply -f lakefs-repos-job.yaml
```

