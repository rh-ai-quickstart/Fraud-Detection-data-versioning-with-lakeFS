# Pipelines

## Overview

This document explains how to interact with and use the Data Science Pipeline feature in OpenShift AI to train fraud detection models with lakeFS data versioning.

## What This Showcases

These pipelines demonstrate the integration of **lakeFS data versioning** with **OpenShift AI Data Science Pipelines**. Key capabilities showcased include:

- **Automated ML Workflows**: End-to-end pipeline execution from data retrieval to model upload
- **Data Versioning with lakeFS**: Training data and model artifacts are versioned using lakeFS branches
- **Reproducibility**: Every pipeline run creates traceable data lineage through lakeFS commits
- **Branch-based Experimentation**: Training happens on isolated lakeFS branches (`train01`), keeping the `main` branch clean
- **S3-Compatible Integration**: Seamless integration with lakeFS using standard S3 APIs and credentials

## Available Pipelines

### Pipeline 6: Train Save lakeFS (Elyra Pipeline)

**File:** `6 Train Save lakefs.pipeline`

An Elyra visual pipeline that chains two Jupyter notebooks together:

1. **`1_experiment_train_lakefs.ipynb`** - Trains the fraud detection model using data from lakeFS
2. **`2_save_model_lakefs.ipynb`** - Saves the trained model back to lakeFS

This pipeline is designed for use with the Elyra pipeline editor in JupyterLab.

### Pipeline 7: Get Data, Train, Upload lakeFS (KFP Pipeline)

**File:** `7_get_data_train_upload_lakefs.yaml`  
**Source:** `../scripts/7_get_data_train_upload_lakefs.py`

A Kubeflow Pipelines (KFP) v2 pipeline with three sequential components:

| Step | Component | Description |
|------|-----------|-------------|
| 1 | **get-data** | Downloads training and validation CSV data from GitHub |
| 2 | **train-model** | Creates a lakeFS branch (`train01`), uploads data to lakeFS, trains a neural network model, and exports to ONNX format |
| 3 | **upload-model** | Uploads the trained ONNX model to lakeFS at `models/fraud/1/model.onnx` |

## How It Works

### Pipeline 7 Workflow

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  get-data   │────▶│ train-model  │────▶│ upload-model │
└─────────────┘     └──────────────┘     └──────────────┘
      │                    │                    │
      ▼                    ▼                    ▼
 Download CSVs      • Create branch       Upload model
 from GitHub        • Upload to lakeFS    to lakeFS
                    • Train neural net
                    • Export ONNX
```

### lakeFS Integration Details

1. **Branch Creation**: The pipeline creates a `train01` branch from `main` in the lakeFS repository
2. **Data Upload**: Training and validation data are written to `data/train.csv` and `data/validate.csv` on the training branch
3. **Artifact Storage**: The scaler artifact is saved to `artifact/scaler.pkl`
4. **Model Upload**: The final ONNX model is uploaded to `models/fraud/1/model.onnx`

### Model Architecture

The fraud detection model is a fully connected deep neural network:

- **Input Layer**: 5 features (distance from last transaction, ratio to median purchase price, used chip, used PIN, online order)
- **Hidden Layers**: 3 layers with 32 neurons each, BatchNormalization, ReLU activation, and 20% Dropout
- **Output Layer**: 1 neuron with sigmoid activation for binary classification (fraud/not fraud)

## Setup

### Prerequisites

Before running pipelines in OpenShift AI, ensure you have:

1. **Pipeline Server Deployed**: The Data Science Pipeline Server must be running in your project. This is automatically deployed by the Helm chart if `dataSciencePipelines.enabled: true` is set.

2. **Data Connections Configured**: The following secrets must exist in your namespace:
   - `my-storage` - lakeFS connection credentials
   - `pipeline-artifacts` - Pipeline artifact storage credentials

3. **lakeFS Repository**: A lakeFS repository (e.g., `my-storage`) must be created and accessible.

### Verify Pipeline Server Status

1. Navigate to OpenShift AI Dashboard
2. Go to **Data Science Projects** → Select your project
3. Check that the **Pipeline Server** shows as "Running"

## How to Run

### Running Pipeline 6 (Elyra Pipeline)

1. Open JupyterLab in your OpenShift AI workbench
2. Navigate to the `demo/pipelines` directory
3. Double-click `6 Train Save lakefs.pipeline` to open in the Elyra pipeline editor
4. Click the **Run** button in the toolbar
5. Select your pipeline runtime configuration
6. Click **OK** to submit the pipeline

### Running Pipeline 7 (KFP Pipeline)

#### Option A: Import via OpenShift AI Dashboard

1. Navigate to **OpenShift AI Dashboard** → **Data Science Pipelines** → **Pipelines**
2. Click **Import Pipeline**
3. Upload `7_get_data_train_upload_lakefs.yaml`
4. Once imported, click on the pipeline and select **Create Run**
5. Configure any parameters and click **Create**

#### Option B: Upload via Pipeline Server API

```bash
# Get the pipeline server route
oc get routes -n fraud-detection | grep ds-pipeline

# Use the route to upload the pipeline via the KFP SDK or API
```

#### Option C: Regenerate and Upload

If you need to modify the pipeline, edit the Python source and recompile:

```bash
cd demo/scripts
python 7_get_data_train_upload_lakefs.py
```

This generates a new `7_get_data_train_upload_lakefs.yaml` file that can be imported.

### Monitoring Pipeline Runs

1. Go to **OpenShift AI Dashboard** → **Data Science Pipelines** → **Runs**
2. Select your active or completed run
3. View the pipeline graph to see step status
4. Click on individual steps to view logs and outputs

### Verifying Results in lakeFS

After a successful pipeline run:

1. Open the **lakeFS UI** (via the OpenShift route)
2. Navigate to your repository (e.g., `my-storage`)
3. Switch to the `train01` branch
4. Verify the following files exist:
   - `data/train.csv`
   - `data/validate.csv`
   - `artifact/scaler.pkl`
   - `models/fraud/1/model.onnx`

## Environment Variables

The pipelines use the following environment variables (injected from Kubernetes secrets):

| Variable | Secret | Description |
|----------|--------|-------------|
| `LAKECTL_CREDENTIALS_ACCESS_KEY_ID` | `my-storage` | lakeFS access key |
| `LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY` | `my-storage` | lakeFS secret key |
| `LAKECTL_SERVER_ENDPOINT_URL` | `my-storage` | lakeFS S3 gateway endpoint |
| `LAKEFS_REPO_NAME` | `my-storage` | lakeFS repository name |
| `LAKEFS_DEFAULT_REGION` | `my-storage` | AWS region for S3 compatibility |

## Troubleshooting

### Pipeline fails to start

- Verify the Pipeline Server is running: `oc get pods -n fraud-detection | grep ds-pipeline`
- Check that required secrets exist: `oc get secrets -n fraud-detection`

### Connection errors to lakeFS

- Verify the lakeFS service is running: `oc get pods -n fraud-detection -l app.kubernetes.io/component=lakefs`
- Check the `my-storage` secret has correct credentials

### Model upload fails

- Ensure the lakeFS repository exists
- Verify the branch can be created (check lakeFS permissions)
- Review the upload-model step logs for detailed error messages

## References

- [OpenShift AI Pipelines Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/2.25/html/working_with_data_science_pipelines)
- [Kubeflow Pipelines SDK](https://www.kubeflow.org/docs/components/pipelines/v2/)
- [lakeFS Python SDK](https://docs.lakefs.io/integrations/python.html)
- [Elyra Pipeline Editor](https://elyra.readthedocs.io/en/latest/getting_started/overview.html)
