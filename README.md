# Data versioning for Fraud Detectin with lakeFS

<!-- CONTRIBUTOR TODO: update title ^^

*replace the H1 title above with your quickstart title*

TITLE requirements:
	* MAX CHAR: 64 
	* Industry use case, ie: Protect patient data with LLM guardrails

TITLE will be extracted for publication.

-- > 



<!-- CONTRIBUTOR TODO: short description 

*ADD a SHORT DESCRIPTION of your use case between H1 title and next section*

SHORT DESCRIPTION requirements:
	* MAX CHAR: 160
	* Describe the INDUSTRY use case 

SHORT DESCRIPTION will be extracted for publication.

--> 


## Table of contents

<!-- Table of contents is optional, but recommended. 

REMEMBER: to remove this section if you don't use a TOC.

-->

## Detailed description

The purpose of this AI quickstart is to highlight the benefits of data versioning, provided by lakeFS, in an AI/ML environment. lakeFS allows the data engineer to manage the lifecycle of data using the same workflow a developer uses to manage source code, using git. This means that, like source code, data can be versioned, branched, merged and pulled from a git repository, although the data is actually stored in a backend object storage.

The quickstart will allow a demonstrator to quickly deploy both object storage, using MinIO, and lakeFS to serve as a git-like gateway that data engineers can interface with for data access. The following steps should be able to be run very quickly:

1. Deploy Minio for on-premesis object storage, running on the local OpenShift cluster
2. Deploy an instance of lakeFS for git-like management of data and data versioning
3. Deploy an fraud detection notebook in OpenShift AI
4. Create and train a model using the notebook and data
5. Serve the trained model
6. Perform fraud detection on sample transactions data
7. Update the training data and retrain the model using the new data version
8. Perform fraud detection on a new version of the sample transaction data
9. Show how OpenShift AI pipelines can be used to retrain and/or perform detection on new versions of training and sample data


### See it in action 

<!-- 

*This section is optional but recommended*

Arcades are a great way to showcase your quickstart before installation.

-->

### Architecture diagrams

![alt text](.docs/images/lakefs-arch.png "lakeFS architecture")


## Requirements


### Minimum hardware requirements 

<!-- CONTRIBUTOR TODO: add minimum hardware requirements

*Section is required.* 

Be as specific as possible. DON'T say "GPU". Be specific.

List minimum hardware requirements.

--> 

### Minimum software requirements

<!-- CONTRIBUTOR TODO: add minimum software requirements

*Section is required.*

Be specific. Don't say "OpenShift AI". Instead, tested with OpenShift AI 2.22

If you know it only works in a specific version, say so. 

-->
This quickstart was tested with the following software versions:

| Software                           | Version  |
| ---------------------------------- |:---------|
| Red Hat OpenShift                  | 4.20.5   |
| Red Hat OpenShift Service Mesh     | 2.5.11-0 |
| Red Hat OpenShift Serverless       | 1.37.0   |
| Red Hat OpenShift AI               | 2.25     |
| helm                               | 3.17.1   |
| lakeFS                             | 1.73.0   |


### Required user permissions

<!-- CONTRIBUTOR TODO: add user permissions

*Section is required. Describe the permissions the user will need. Cluster
admin? Regular user?*

--> 


## Deploy

<!-- CONTRIBUTOR TODO: add installation instructions 

*Section is required. Include the explicit steps needed to deploy your
quickstart. 

Assume user will follow your instructions EXACTLY. 

If screenshots are included, remember to put them in the
`docs/images` folder.*

-->
The following steps assume the following pre-requisite products and components are deployed and functional, in the following order:

1. Red Hat OpenShift Container Platform
2. Red Hat OpenShift Service Mesh
3. Red Hat OpenShift Serverless
4. Red Hat OpenShift AI

Login to the OpenShift cluster:
```
$ oc login --token=<user_token> --server=https://api.<openshift_cluster_fqdn>:6443
```

Create a project for the lakeFS application:
```
$ oc new-project lakefs
```

Add the `lakefs` helm repo and verify the `my-lakefs` release available:
```
$ helm repo add lakefs https://charts.lakefs.io

$ helm repo list
NAME  	URL                     
lakefs	https://charts.lakefs.io

$ helm list 
NAME     	NAMESPACE        	REVISION	UPDATED                                	STATUS  	CHART        	APP VERSION
my-lakefs	3c47b24f-lakefsai	1       	2025-12-05 13:45:59.323482412 -0500 EST	deployed	lakefs-1.7.12	1.73.0     
```

Deploy `my-lakefs` to the `lakefs` project:
```
$ helm install my-lakefs lakefs/lakefs
```

ISSUE: For now, we have to make the following modification to the `my-lakefs` deployment. Use the command below to edit the deployment and add the volume and volume mount below to the exiting configuration.
```
$ oc edit deploy/my-lakefs

volumeMounts:
  - name: lakefs-volume
    mountpath: /lakefs

volumes:
  - name: lakefs-volume
    emptyDir:
     sizeLimit: 100Mi
```

Verify the `my-lakefs` applicaton is running:
```
$ oc get all
Warning: apps.openshift.io/v1 DeploymentConfig is deprecated in v4.14+, unavailable in v4.10000+
NAME                             READY   STATUS    RESTARTS   AGE
pod/my-lakefs-55486ff445-pshwj   1/1     Running   0          40m

NAME                TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)   AGE
service/my-lakefs   ClusterIP   172.30.200.142   <none>        80/TCP    92m

NAME                        READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/my-lakefs   1/1     1            1           92m

NAME                                   DESIRED   CURRENT   READY   AGE
replicaset.apps/my-lakefs-55486ff445   1         1         1       40m
replicaset.apps/my-lakefs-78c5f7d794   0         0         0       92m
```

Create a `route` for the `my-lakefs` instance so that it can be accessed from outside the cluster:
```
$ oc create route edge my-lakefs --service my-lakefs --port 8000 --hostname lakefs.apps.<cluster_fqdn>
route.route.openshift.io/my-lakefs created

$ oc get route
NAME        HOST/PORT                           PATH       SERVICES    PORT   TERMINATION   WILDCARD
my-lakefs   lakefs.apps.<cluster_fqdn>                     my-lakefs   8000   edge          None
```

Use the route to access the lakeFS browser-base UI. 

1. Leave the username set to `admin`
2. Enter your email address (or a bogus email address)
3. Download the `access_key_id` and `secret_access_key` displayed on the new page, as they will not be accessible later on
4. Go back to the login page and log in using those credentials.

### Delete

<!-- CONTRIBUTOR TODO: add uninstall instructions

*Section required. Include explicit steps to cleanup quickstart.*

Some users may need to reclaim space by removing this quickstart. Make it easy.

-->

## References 

<!-- 

*Section optional.* Remember to remove if do not use.

Include links to supporting information, documentation, or learning materials.

--> 

## Technical details

<!-- 

*Section is optional.* 

Here is your chance to share technical details. 

Welcome to add sections as needed. Keep additions as structured and consistent as possible.

-->

## Tags

<!-- CONTRIBUTOR TODO: add metadata and tags for publication

TAG requirements: 
	* Title: max char: 64, describes quickstart (match H1 heading) 
	* Description: max char: 160, match SHORT DESCRIPTION above
	* Industry: target industry, ie. Healthcare OR Financial Services
	* Product: list primary product, ie. OpenShift AI OR OpenShift OR RHEL 
	* Use case: use case descriptor, ie. security, automation, 
	* Contributor org: defaults to Red Hat unless partner or community
	
Additional MIST tags, populated by web team.

-->
