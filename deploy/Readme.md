# Deployment Guide

In order to set up the environment, there are currently four steps, assuming the OpenShift cluster is already up.

1. Deploy MinIO using the `minio-for-lakefs.yaml` file
```
$ oc apply -f minio-for-lakefs.yaml
```
2. Create the lakeFS config file in a configmap using the `lakefs-config-job.yaml` file
```
$ oc apply -f lakefs-config-job.yaml
```
3. Deploy lakeFS using the helm chart
```
$ helm install my-lakefs ./helm/lakefs
```
4. Create the reposotories in lakeFS, which will create the storage buckets in MinIO, using the `lakefs-repos-job.yaml` file
```
$ oc apply -f lakefs-repos-job.yaml
```

