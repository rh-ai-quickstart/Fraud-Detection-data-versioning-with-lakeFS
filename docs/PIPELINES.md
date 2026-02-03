# Data Science Pipelines Guide

[← Back to Main README](../README.md)

This guide provides comprehensive documentation for setting up and using Data Science Pipelines with lakeFS data versioning in the Fraud Detection quickstart.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Available Pipelines](#available-pipelines)
  - [Pipeline 6: Elyra Visual Pipeline](#pipeline-6-elyra-visual-pipeline)
  - [Pipeline 7: Kubeflow Pipelines (KFP)](#pipeline-7-kubeflow-pipelines-kfp)
- [Setup Guide](#setup-guide)
- [Running Pipelines](#running-pipelines)
- [lakeFS Integration](#lakefs-integration)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [References](#references)

## Overview

The Fraud Detection quickstart includes two types of Data Science Pipelines that demonstrate end-to-end ML workflows with lakeFS data versioning:

| Pipeline Type | Tool | Description | Best For |
|--------------|------|-------------|----------|
| **Elyra** | Visual Editor | Chains Jupyter notebooks together | Interactive development, notebook-based workflows |
| **KFP v2** | Python SDK | Compiled YAML pipelines with components | Production workflows, CI/CD integration |

### What These Pipelines Showcase

- **Automated ML Workflows**: End-to-end execution from data retrieval to model upload
- **Data Versioning with lakeFS**: Training data and model artifacts are versioned using lakeFS branches
- **Reproducibility**: Every pipeline run creates traceable data lineage through lakeFS commits
- **Branch-based Experimentation**: Training happens on isolated lakeFS branches (`train01`), keeping the `main` branch clean
- **S3-Compatible Integration**: Seamless integration with lakeFS using standard S3 APIs and credentials

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        OpenShift AI Dashboard                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │
│  │   JupyterLab    │  │ Pipeline Server │  │ Model Registry  │          │
│  │  (Elyra Editor) │  │    (KFP v2)     │  │                 │          │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────┘          │
└───────────┼────────────────────┼────────────────────────────────────────┘
            │                    │
            ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         lakeFS (S3 Gateway)                             |
│   ┌───────────────────────────────────────────────────────────────┐     │
│   │  Repository: my-storage                                       │     │
│   │  ├── main (branch)                                            │     │
│   │  │   └── [production data and models]                         │     │
│   │  └── train01 (branch)                                         │     │
│   │      ├── data/train.csv                                       │     │
│   │      ├── data/validate.csv                                    │     │
│   │      ├── artifact/scaler.pkl                                  │     │
│   │      └── models/fraud/1/model.onnx                            │     │
│   └───────────────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────────────┬─────┘
                                                                    │
                                                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        MinIO (Object Storage)                           │
│   Stores actual bytes for datasets, models, and artifacts               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

Before running pipelines, ensure you have:

### 1. Deployed Infrastructure

The following components must be deployed and running (handled by the Helm chart):

- **Data Science Pipeline Server (DSPA)** - Manages pipeline execution
- **lakeFS** - Provides S3-compatible versioning gateway
- **MinIO** - Backend object storage
- **JupyterLab Notebook** - For Elyra pipeline development

### 2. Required Secrets

Two Kubernetes secrets must exist in your namespace:

| Secret Name | Purpose | Required Keys |
|-------------|---------|---------------|
| `my-storage` | lakeFS connection | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT`, `AWS_S3_BUCKET`, `AWS_DEFAULT_REGION` |
| `pipeline-artifacts` | Pipeline artifact storage | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT`, `AWS_S3_BUCKET`, `AWS_DEFAULT_REGION` |

### 3. lakeFS Repository

A lakeFS repository (e.g., `my-storage`) must be created and accessible. This is automatically created by the Helm chart.

### Verify Prerequisites

```bash
# Check Pipeline Server is running
oc get pods -n fraud-detection | grep ds-pipeline

# Check required secrets exist
oc get secrets -n fraud-detection | grep -E "(my-storage|pipeline-artifacts)"

# Check lakeFS is running
oc get pods -n fraud-detection -l app.kubernetes.io/component=lakefs
```

## Available Pipelines

### Pipeline 6: Elyra Visual Pipeline

**Location:** `demo/pipelines/6 Train Save lakefs.pipeline`

An Elyra visual pipeline that chains two Jupyter notebooks together for training and saving models with lakeFS versioning.

#### Pipeline Structure

```
┌───────────────────────────┐       ┌───────────────────────────┐
│ 1_experiment_train_lakefs │──────▶│   2_save_model_lakefs     │
│        .ipynb             │       │        .ipynb             │
└───────────────────────────┘       └───────────────────────────┘
        │                                    │
        ▼                                    ▼
• Install dependencies              • Connect to lakeFS
• Create lakeFS branch             • Upload model to branch
• Upload training data             • Commit changes
• Train neural network             • List versioned artifacts
• Export model to ONNX
• Test model accuracy
```

#### Notebook 1: Experiment and Train (`1_experiment_train_lakefs.ipynb`)

This notebook performs the following operations:

1. **Install Dependencies**: `onnx`, `onnxruntime`, `tf2onnx`, `lakefs`, `s3fs`
2. **Configure lakeFS Connection**: Sets up S3-compatible storage options
3. **Create Training Branch**: Creates `train01` branch from `main`
4. **Upload Training Data**: Writes `train.csv`, `validate.csv`, `test.csv` to lakeFS
5. **Train Model**: Builds and trains a fully-connected deep neural network
6. **Save Artifacts**: Stores scaler and test data to lakeFS
7. **Export Model**: Saves model as ONNX format
8. **Test Model**: Evaluates accuracy, precision, and recall

#### Notebook 2: Save Model (`2_save_model_lakefs.ipynb`)

This notebook handles model persistence:

1. **Connect to lakeFS**: Establishes S3 connection via boto3
2. **Upload Model**: Uploads ONNX model to `train01` branch
3. **Commit Changes**: Creates immutable snapshot in lakeFS
4. **Verify Upload**: Lists objects in the versioned namespace

For detailed notebook documentation, see [Notebooks Guide](NOTEBOOKS.md).

---

### Pipeline 7: Kubeflow Pipelines (KFP)

**Location:** `demo/pipelines/7_get_data_train_upload_lakefs.yaml`  
**Source:** `demo/scripts/7_get_data_train_upload_lakefs.py`

A Kubeflow Pipelines v2 pipeline with three sequential components for automated training and model upload.

#### Pipeline Structure

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  get-data   │────▶│ train-model  │────▶│ upload-model │
└─────────────┘     └──────────────┘     └──────────────┘
      │                    │                    │
      ▼                    ▼                    ▼
 Download CSVs      • Create branch       Upload model
 from GitHub        • Upload to lakeFS    to lakeFS
                    • Train neural net    (train01 branch)
                    • Export ONNX
```

#### Component Details

| Step | Component | Description | Outputs |
|------|-----------|-------------|---------|
| 1 | **get-data** | Downloads training and validation CSV data from GitHub | `train_data_output_path`, `validate_data_output_path` |
| 2 | **train-model** | Creates lakeFS branch, uploads data, trains model, exports ONNX | `model_output_path` |
| 3 | **upload-model** | Uploads trained ONNX model to lakeFS at `models/fraud/1/model.onnx` | - |

#### Technical Details

**Base Image:**
```
quay.io/modh/runtime-images:runtime-cuda-tensorflow-ubi9-python-3.9-2024a-20240523
```

**Dependencies Installed:**
- `kfp==2.5.0` (Kubeflow Pipelines SDK)
- `onnx`, `onnxruntime`, `tf2onnx` (Model conversion)
- `lakefs==0.7.1` (lakeFS Python SDK)
- `s3fs==2024.10.0` (S3 filesystem interface)
- `boto3`, `botocore` (AWS S3 SDK)

For detailed KFP pipeline documentation, see [KFP Pipeline Reference](PIPELINES_KFP.md).

## Setup Guide

### Enabling Pipelines in Helm Deployment

The Data Science Pipeline Server is enabled via Helm values:

```yaml
# values-openshift.yaml
dataSciencePipelines:
  enabled: true
  name: dspa
  enableSamplePipeline: false
  database:
    name: mlpipeline
  objectStorage:
    bucket: pipeline-artifacts
    host: minio.fraud-detection.svc.cluster.local
    port: "9000"
    scheme: http
    s3CredentialsSecret:
      secretName: pipeline-artifacts
      accessKey: AWS_ACCESS_KEY_ID
      secretKey: AWS_SECRET_ACCESS_KEY
```

### Verify Pipeline Server Status

1. Navigate to **OpenShift AI Dashboard**
2. Go to **Data Science Projects** → Select your project
3. Check that the **Pipeline Server** shows as "Running"

Or via CLI:

```bash
# Check DSPA status
oc get dspa -n fraud-detection

# Check pipeline pods
oc get pods -n fraud-detection -l app=ds-pipeline
```

## Running Pipelines

### Running Pipeline 6 (Elyra)

1. **Open JupyterLab** in your OpenShift AI workbench
2. **Navigate** to the `demo/pipelines` directory
3. **Double-click** `6 Train Save lakefs.pipeline` to open in Elyra editor
4. **Click Run** button in the toolbar
5. **Select** your pipeline runtime configuration
6. **Click OK** to submit the pipeline

### Running Pipeline 7 (KFP)

#### Option A: Import via OpenShift AI Dashboard

1. Navigate to **OpenShift AI Dashboard** → **Data Science Pipelines** → **Pipelines**
2. Click **Import Pipeline**
3. Upload `7_get_data_train_upload_lakefs.yaml`
4. Click on the pipeline and select **Create Run**
5. Configure parameters and click **Create**

#### Option B: Regenerate from Python Source

If you need to modify the pipeline:

```bash
cd demo/scripts

# Install KFP SDK
pip install kfp==2.5.0

# Compile pipeline to YAML
python 7_get_data_train_upload_lakefs.py
```

This generates a new `7_get_data_train_upload_lakefs.yaml` in the `pipelines` directory.

### Monitoring Pipeline Runs

1. Go to **OpenShift AI Dashboard** → **Data Science Pipelines** → **Runs**
2. Select your active or completed run
3. View the pipeline graph to see step status
4. Click on individual steps to view logs and outputs

## lakeFS Integration

### How Pipelines Use lakeFS

1. **Branch Creation**: Pipelines create a `train01` branch from `main`
2. **Data Upload**: Training data is written to versioned paths
3. **Artifact Storage**: Scaler and model artifacts are stored alongside data
4. **Model Upload**: Final ONNX model is uploaded to branch
5. **Commit (optional)**: Changes can be committed for immutable snapshots

### lakeFS Path Structure

```
s3://my-storage/train01/
├── data/
│   ├── train.csv
│   └── validate.csv
├── artifact/
│   └── scaler.pkl
└── models/
    └── fraud/
        └── 1/
            └── model.onnx
```

### Verifying Results in lakeFS

After a successful pipeline run:

1. Open the **lakeFS UI** (via the OpenShift route)
2. Navigate to your repository (e.g., `my-storage`)
3. Switch to the `train01` branch
4. Verify the expected files exist

## Environment Variables

Pipelines use environment variables injected from Kubernetes secrets:

| Variable | Secret | Key | Description |
|----------|--------|-----|-------------|
| `LAKECTL_CREDENTIALS_ACCESS_KEY_ID` | `my-storage` | `AWS_ACCESS_KEY_ID` | lakeFS access key |
| `LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY` | `my-storage` | `AWS_SECRET_ACCESS_KEY` | lakeFS secret key |
| `LAKECTL_SERVER_ENDPOINT_URL` | `my-storage` | `AWS_S3_ENDPOINT` | lakeFS S3 gateway endpoint |
| `LAKEFS_REPO_NAME` | `my-storage` | `AWS_S3_BUCKET` | lakeFS repository name |
| `LAKEFS_DEFAULT_REGION` | `my-storage` | `AWS_DEFAULT_REGION` | AWS region for S3 compatibility |

### Configuring Secrets

The secrets are automatically created by the Helm chart. To verify:

```bash
# Check my-storage secret
oc get secret my-storage -n fraud-detection -o yaml

# Check pipeline-artifacts secret
oc get secret pipeline-artifacts -n fraud-detection -o yaml
```

## Troubleshooting

### Pipeline Server Issues

**Pipeline fails to start**

```bash
# Verify Pipeline Server is running
oc get pods -n fraud-detection | grep ds-pipeline

# Check DSPA status
oc get dspa -n fraud-detection -o yaml

# View Pipeline Server logs
oc logs -n fraud-detection -l app=ds-pipeline-server
```

**Pipeline Server not deploying**

- Ensure `dataSciencePipelines.enabled: true` in Helm values
- Check that required secrets exist
- Verify MinIO is running and accessible

### lakeFS Connection Issues

**Connection errors to lakeFS**

```bash
# Verify lakeFS is running
oc get pods -n fraud-detection -l app.kubernetes.io/component=lakefs

# Check lakeFS logs
oc logs -n fraud-detection -l app.kubernetes.io/component=lakefs

# Verify secret credentials
oc get secret my-storage -n fraud-detection -o jsonpath='{.data.AWS_S3_ENDPOINT}' | base64 -d
```

### Model Upload Issues

**Model upload fails**

- Ensure the lakeFS repository exists
- Verify the branch can be created (check lakeFS permissions)
- Review the `upload-model` step logs for detailed error messages

```bash
# Check lakeFS repository exists
# Access lakeFS UI or use lakectl CLI
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Secret "my-storage" not found` | Missing secret | Verify Helm deployment completed successfully |
| `Connection refused to lakeFS` | lakeFS not running | Check lakeFS pod status |
| `Branch already exists` | Previous run created branch | Pipeline uses `exist_ok=True` - this is expected |
| `Access Denied` | Invalid credentials | Verify secret values match lakeFS credentials |

## References

- [OpenShift AI Pipelines Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/2.25/html/working_with_data_science_pipelines)
- [Kubeflow Pipelines SDK v2](https://www.kubeflow.org/docs/components/pipelines/v2/)
- [lakeFS Python SDK](https://docs.lakefs.io/integrations/python.html)
- [Elyra Pipeline Editor](https://elyra.readthedocs.io/en/latest/getting_started/overview.html)
- [Main README](../README.md)

---

[← Back to Main README](../README.md) | [Notebooks Guide →](NOTEBOOKS.md) | [KFP Reference →](PIPELINES_KFP.md)
