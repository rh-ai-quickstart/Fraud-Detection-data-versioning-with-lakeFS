# Data versioning for Fraud Detectin with lakeFS

Fraud detection is a critical part of any business. Discover how data management and versioning with lakeFS enables repeatable, version-controlled data sets, using familiar workflows and processes, while reducing storage costs for generative and predictive AI applications.

## Table of contents

<!-- Table of contents is optional, but recommended. 

REMEMBER: to remove this section if you don't use a TOC.

-->

## Detailed description

The purpose of this AI quickstart is to highlight the benefits of data versioning, provided by lakeFS, in an AI/ML environment. lakeFS allows the data engineer to manage the lifecycle of data using the same workflow a developer uses to manage source code, using git. This means that, like source code, data can be versioned, branched, merged and pulled from a git repository, although the data is actually stored in a backend object storage.

The quickstart will allow a demonstrator to quickly deploy both object storage, using MinIO, and lakeFS to serve as a git-like gateway that data engineers can interface with for data access. The following steps can be run very quickly:

1. Deploy Minio for on-premesis object storage, running on the local OpenShift cluster
2. Deploy an instance of lakeFS for git-like management of data and data versioning
3. Deploy fraud detection notebooks in OpenShift AI
4. Create and train a model using the notebooks and data
5. Serve the trained model
6. Perform fraud detection on sample transactions data
7. Update the training data and retrain the model using the new data version
8. Perform fraud detection on a new version of the sample transaction data
9. Show how OpenShift AI pipelines can be used to retrain and/or perform detection on new versions of training and sample data


### See it in action 

TODO: create an arcade?

### Architecture diagrams

![alt text](docs/images/lakefs-arch.png "lakeFS architecture")


## Requirements


### Minimum hardware requirements 

<!-- CONTRIBUTOR TODO: add minimum hardware requirements

*Section is required.* 

Be as specific as possible. DON'T say "GPU". Be specific.

List minimum hardware requirements.

--> 

### Minimum software requirements

This quickstart was tested with the following software versions:

| Software                           | Version  |
| ---------------------------------- |:---------|
| Red Hat OpenShift                  | 4.20.5   |
| Red Hat OpenShift Service Mesh     | 2.5.11-0 |
| Red Hat OpenShift Serverless       | 1.37.0   |
| Red Hat OpenShift AI               | 2.25     |
| helm                               | 3.17.1   |
| lakeFS                             | 1.73.0   |
| MinIO                              | TBD      |


### Required user permissions

The user performing this quickstart should have the ability to create a project in OpenShift and OpenShift AI. This requires the cluster role of `admin` (does not require `cluster-admin`)


## Deploy

The process is very simple. Just follow the steps below.

### Pre-requisites

The steps assume the following pre-requisite products and components are deployed and functional with required permissions on the cluster:

1. Red Hat OpenShift Container Platform
2. Red Hat OpenShift Service Mesh
3. Red Hat OpenShift Serverless
4. Red Hat OpenShift AI
5. User has `admin` permissions in the cluster

### Deployment Steps

1. Clone this repo
```
$ git clone https://github.com/rh-ai-quickstart/Fraud-Detection-data-versioning-with-lakeFS.git
```

2. cd to `deploy` directory
```
$ cd Fraud-Detection-data-versioning-with-lakeFS/deploy
```

3. Login to the OpenShift cluster:
```
$ oc login --token=<user_token> --server=https://api.<openshift_cluster_fqdn>:6443
```

4. Create the `lakefs` project. The script requires this project name. If the project already exists, just make sure you have `admin` permissions in the project, then skip this step.
```
$ oc new-project lakefs
```

5. Make sure `deploy.sh` is executable and run it
```
$ chmod + deploy.sh
$ ./deploy.sh
```

### Access lakeFS UI

Use the route to access the lakeFS browser-base UI. 

1. Leave the username set to `admin`
2. Enter your email address (or a bogus email address)
3. Download the `access_key_id` and `secret_access_key` displayed on the new page, as they will not be accessible later on
4. Go back to the login page and log in using those credentials.

### Delete

The `lakefs` project can be deleted, which will delete all of the resources in it, including deployments, secrets, pods, configmaps, etc.
```
oc delete project lakefs
```

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
