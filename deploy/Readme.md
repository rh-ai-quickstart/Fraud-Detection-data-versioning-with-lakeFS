# Detailed steps of deploy.sh

ARG 1: project to install to

1. Check if project already exists. If it does, switch to it. If it doesn't, create it.
2. Change to the `lakefs` project
3. Deploy MinIO using the `minio-for-lakefs.yaml` file. This manifest file, when applied to the cluster, will deploy MinIO, create the required storage buckets and create a random root username and password. After this step, you should be able to log into the MinIO console using the `minio-console` route and the generated crendentials stored in the secret.
```
$ oc apply -f minio-for-lakefs.yaml
```
4. Create the lakeFS config file in a configmap using the `lakefs-config-job.yaml` file. This manifest file, when applied to the cluster, will create the config map used to store the *lakeFS* configuration, which is used when it is brought up. This configuration will include the login credentials to the lakeFS console, accessible from its route, and the configuration and credentials lakeFS will use to access the backend MinIO object storage. 
```
$ oc apply -f lakefs-config-job.yaml
```
5. Deploy lakeFS using the helm chart. The chart will deploy the lakeFS application and a route to access it.
```
$ helm install my-lakefs ./helm/lakefs
```
6. Create the reposotories in lakeFS, which will associate to the storage buckets in MinIO, using the `lakefs-repos-job.yaml` file.
```
$ oc apply -f lakefs-repos-job.yaml
```

