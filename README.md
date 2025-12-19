# Fraud Detection data versioning with lakeFS (OpenShift AI)

This AI quickstart demonstrates how to use **lakeFS as an AI data control plane** for Red Hat OpenShift AI using the fraud-detection tutorial workflow.

You will deploy MinIO (object storage) and lakeFS, run the fraud-detection notebooks in OpenShift AI, and then repeat the workflow on a *new version of the data* to show how lakeFS enables reproducibility, safe experimentation, and governed promotion of AI data and model artifacts.

---

## Data plane vs control plane

This quickstart intentionally separates responsibilities:

- **Data plane (object storage)**  
  MinIO / S3 stores the bytes: datasets, models, and pipeline artifacts.

- **Control plane (lakeFS)**  
  lakeFS adds Git-like semantics (branch, commit, merge, revert) and lineage metadata *on top of* the data in object storage.

- **Compatibility**  
  lakeFS exposes an **S3-compatible API**, so OpenShift AI and S3-native tools can use it as a drop-in endpoint without code changes.

After running this quickstart you can answer questions like:

- “Which exact dataset version trained the model that’s currently served?”
- “What changed between the dataset used for model v1 and v2?”
- “Can we reproduce last month’s metrics exactly?”
- “Can we roll back immediately if a bad data update ships?”

---

## Table of contents

- [Detailed description](#detailed-description)
  - [See it in action](#see-it-in-action)
  - [Architecture diagrams](#architecture-diagrams)
- [Requirements](#requirements)
  - [Minimum hardware requirements](#minimum-hardware-requirements)
  - [Minimum software requirements](#minimum-software-requirements)
  - [Required user permissions](#required-user-permissions)
- [Deploy](#deploy)
  - [Pre-requisites](#pre-requisites)
  - [Deployment steps](#deployment-steps)
  - [Access lakeFS UI](#access-lakefs-ui)
  - [Delete](#delete)
- [References](#references)
- [Technical details](#technical-details)
- [Tags](#tags)

## Detailed description

The purpose of this AI quickstart is to highlight the benefits of data versioning, provided by lakeFS, in an AI/ML environment. lakeFS allows the data engineer to manage the lifecycle of data using the same workflow a developer uses to manage source code, using git. This means that, like source code, data can be versioned, branched, merged and pulled from a git repository, although the data is actually stored in a backend object storage.

The quickstart will allow a demonstrator to quickly deploy both object storage, using MinIO, and lakeFS to serve as a git-like gateway that data engineers can interface with for data access. The following steps can be run very quickly:

### What you’ll do (and what lakeFS adds)

1. Deploy MinIO (object storage) and lakeFS (S3-compatible versioning gateway)
2. Configure OpenShift AI to use **lakeFS as its S3 endpoint** (data connection)
3. Run the fraud-detection notebooks to:
   - load training data from lakeFS
   - train a model
   - write the model artifact back to lakeFS
4. Create a **lakeFS branch** for a data change (e.g., updated labels / new transactions)
5. Write updated training data to the branch, **commit** it, and retrain
6. Compare results across versions, then **merge** the branch to promote (or revert/discard)
7. (Optional) Run a pipeline that reads/writes through lakeFS so pipeline outputs are also versioned

### See it in action 

TODO: create an arcade?

### Architecture diagrams

![alt text](docs/images/lakefs-arch.png "lakeFS architecture")


## Requirements

This quickstart was developed and test on an OpenShift cluster with the following components and resources. This can be considered the minimum requirements.

### Minimum hardware requirements 

| Node Type           | Qty  | vCPU   | Memory (GB) |
| --------------------|------|-------|--------------|
| Control Plane       | 3    | 8     | 16           |
| Worker              | 3    | 8     | 16           |

> [!NOTE]
> A GPU is not required for this quickstart

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

4. Make sure `deploy.sh` is executable and run it, passing it the name of the project in which to install. It can be an existing or new project. In this example, it will deploy to the `lakefs` project.
```
# Make script executable
$ chmod + deploy.sh

# Run script passing it the project in which to install
$ ./deploy.sh lakefs
```

### Access lakeFS UI

Use the route to access the lakeFS browser-base UI. 

1. Leave the username set to `admin`
2. Enter your email address (or a bogus email address)
3. Download the `access_key_id` and `secret_access_key` displayed on the new page, as they will not be accessible later on
4. Go back to the login page and log in using those credentials.

### Delete

The project the apps were installed in can be deleted, which will delete all of the resources in it, including deployments, secrets, pods, configmaps, etc.
```
oc delete project lakefs
```

## References 

* lakeFS documentation [v1.73](https://docs.lakefs.io/v1.73/)
* OpenShift AI documentatin [v2.25](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/2.25)
* OpenShift AI Fraud Detection [example](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/2.25/html/openshift_ai_tutorial_-_fraud_detection_example)

## Technical details

lakeFS exposes an S3-compatible API. In S3 terms:

- **Bucket = lakeFS repository**
- **First path segment = branch**
- Object paths follow:

  s3://[REPOSITORY]/[BRANCH]/PATH/TO/OBJECT

Example:
- Training data:  s3://fraud/main/data/transactions.parquet
- Experiment data: s3://fraud/exp-01/data/transactions.parquet
- Model artifact:  s3://fraud/exp-01/models/fraud/1/model.onnx

In real AI platforms, the point isn’t just versioning—it’s controlled promotion:

- Protect `main` so changes only arrive via merges
- Add pre-merge hooks (Actions) to enforce data quality checks (schema, format, PII scanning)
- Merge = “publish” approved data/model artifacts to consumers

## Tags

* Product: OpenShift AI
* Partner: lakeFS
* Partner product: lakeFS
* Business challenge: Fraud detection
