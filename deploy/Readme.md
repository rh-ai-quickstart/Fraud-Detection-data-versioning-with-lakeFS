# Deployment Guide

In order to set up the environment, there are currently four steps, assuming the OpenShift cluster is already up.

# Pre-requisites
1. OpenShift cluster is deployed
2. The `lakefs` project is created
3. User has `admin` permissions in the `lakefs`namespace

# Steps

1. Deploy MinIO using the `minio-for-lakefs.yaml` file. This manifest file, when applied to the cluster, will deploy MinIO and create a random root username and password. After this step, you should be able to log into the MinIO console using the `minio-console` route and the generated crendentials stored in the secret.

```
$ oc apply -f minio-for-lakefs.yaml
```

2. Create the lakeFS config file in a configmap using the `lakefs-config-job.yaml` file. This manifest file, when applied to the cluster, will create the config map used to store the *lakeFS* configuration, which is used when it is brought up. This configuration will include the login credentials to the lakeFS console, accessible from its route, and the configuration and credentials lakeFS will use to access the backend MinIO object storage.
```
$ oc apply -f lakefs-config-job.yaml
```

3. Deploy lakeFS using the helm chart. The chart will deploy the lakeFS application and a route to access it.
```
$ helm install my-lakefs ./helm/lakefs
```

4. Create the reposotories in lakeFS, which will create the storage buckets in MinIO, using the `lakefs-repos-job.yaml` file.
```
$ oc apply -f lakefs-repos-job.yaml
```

