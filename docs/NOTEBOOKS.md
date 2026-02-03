# Notebooks Guide

[← Back to Main README](../README.md) | [← Back to Pipelines Guide](PIPELINES.md)

This guide provides detailed documentation for the Jupyter notebooks used in the Fraud Detection quickstart with lakeFS data versioning.

## Table of Contents

- [Overview](#overview)
- [Notebook Inventory](#notebook-inventory)
- [Getting Started](#getting-started)
- [Notebook Details](#notebook-details)
  - [0. Quickstart Readiness Check](#0-quickstart-readiness-check)
  - [1. Experiment and Train with lakeFS](#1-experiment-and-train-with-lakefs)
  - [2. Save Model to lakeFS](#2-save-model-to-lakefs)
  - [5. REST Requests Single Model](#5-rest-requests-single-model)
  - [8. Distributed Training with lakeFS](#8-distributed-training-with-lakefs)
- [lakeFS Integration Patterns](#lakefs-integration-patterns)
- [Environment Setup](#environment-setup)
- [References](#references)

## Overview

The notebooks in this quickstart demonstrate the integration of lakeFS data versioning with OpenShift AI for fraud detection model training and serving. Each notebook is designed to run in a JupyterLab environment within OpenShift AI.

## Notebook Inventory

| Notebook | Purpose | lakeFS Integration |
|----------|---------|-------------------|
| `0_quickstart-readiness-check.ipynb` | Verify environment setup | Connection test |
| `1_experiment_train_lakefs.ipynb` | Train fraud detection model | Branch creation, data versioning |
| `2_save_model_lakefs.ipynb` | Upload model to storage | Model artifact versioning |
| `5_rest_requests_single_model_lakefs.ipynb` | Test model serving | Read from versioned storage |
| `8_distributed_training_lakefs.ipynb` | Multi-worker training | Distributed data access |

**Location:** `demo/notebooks/`

## Getting Started

### Accessing the Notebooks

1. **Via OpenShift AI Dashboard:**
   - Navigate to **Data Science Projects** → your project
   - Click on your **Workbench** (JupyterLab)
   - Navigate to the cloned repository folder

2. **Via Git Clone (if not auto-cloned):**
   ```bash
   git clone https://github.com/rh-ai-quickstart/Fraud-Detection-data-versioning-with-lakeFS.git
   cd Fraud-Detection-data-versioning-with-lakeFS/demo/notebooks
   ```

### Required Data Connections

Ensure these data connections are configured in your workbench:

| Data Connection | Secret Name | Purpose |
|-----------------|-------------|---------|
| lakeFS Storage | `my-storage` | Access lakeFS S3 gateway |
| Pipeline Artifacts | `pipeline-artifacts` | Store pipeline outputs |

## Notebook Details

### 0. Quickstart Readiness Check

**File:** `0_quickstart-readiness-check.ipynb`

Verifies that your environment is properly configured before running other notebooks.

#### What It Checks

- Python environment and package availability
- lakeFS connection and credentials
- S3/MinIO connectivity
- Required environment variables

#### Usage

Run all cells to validate your setup. Green checkmarks indicate successful configuration.

---

### 1. Experiment and Train with lakeFS

**File:** `1_experiment_train_lakefs.ipynb`

The primary training notebook that demonstrates the full ML workflow with lakeFS data versioning.

#### Workflow Steps

1. **Install Dependencies**
   ```python
   !pip install onnx onnxruntime tf2onnx lakefs==0.7.1 s3fs==2024.10.0
   ```

2. **Configure lakeFS Connection**
   ```python
   lakefs_storage_options = {
       "key": os.environ.get('LAKECTL_CREDENTIALS_ACCESS_KEY_ID'),
       "secret": os.environ.get('LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY'),
       "client_kwargs": {
           "endpoint_url": os.environ.get('LAKECTL_SERVER_ENDPOINT_URL')
       }
   }
   
   repo = lakefs.Repository(os.environ.get('LAKEFS_REPO_NAME'))
   ```

3. **Create Training Branch**
   ```python
   mainBranch = "main"
   trainingBranch = "train01"
   
   branchTraining = repo.branch(trainingBranch).create(
       source_reference=mainBranch, 
       exist_ok=True
   )
   ```

4. **Upload Training Data to lakeFS**
   ```python
   obj = branchTraining.object(path='data/train.csv')
   with open('data/train.csv', mode='rb') as reader, \
        obj.writer(mode='wb', metadata={'source': 'Fraud Detection Demo'}) as writer:
       writer.write(reader.read())
   ```

5. **Load Data via S3 Interface**
   ```python
   df = pd.read_csv(
       f"s3://{repo_name}/{trainingBranch}/data/train.csv",
       storage_options=lakefs_storage_options
   )
   ```

6. **Train Model**
   ```python
   model = Sequential()
   model.add(Dense(32, activation='relu', input_dim=5))
   model.add(Dropout(0.2))
   # ... additional layers
   model.add(Dense(1, activation='sigmoid'))
   
   model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
   model.fit(X_train, y_train, epochs=2, validation_data=(X_val, y_val), ...)
   ```

7. **Export Model to ONNX**
   ```python
   model_proto, _ = tf2onnx.convert.from_keras(model)
   onnx.save(model_proto, "models/fraud/1/model.onnx")
   ```

8. **Test Model**
   ```python
   sess = rt.InferenceSession("models/fraud/1/model.onnx")
   y_pred = sess.run([output_name], {input_name: X_test})
   ```

#### Model Output

After running, you should see:
- Model accuracy, precision, and recall metrics
- Confusion matrix visualization
- Local model file at `models/fraud/1/model.onnx`

---

### 2. Save Model to lakeFS

**File:** `2_save_model_lakefs.ipynb`

Uploads the trained model to lakeFS for versioned storage and creates an immutable commit.

#### Workflow Steps

1. **Install Dependencies**
   ```python
   !pip install boto3 botocore lakefs==0.7.1
   ```

2. **Configure S3 Client for lakeFS**
   ```python
   session = boto3.session.Session(
       aws_access_key_id=os.environ.get('LAKECTL_CREDENTIALS_ACCESS_KEY_ID'),
       aws_secret_access_key=os.environ.get('LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY')
   )
   
   s3_resource = session.resource(
       's3',
       config=botocore.client.Config(signature_version='s3v4'),
       endpoint_url=os.environ.get('LAKECTL_SERVER_ENDPOINT_URL'),
       region_name=os.environ.get('LAKEFS_DEFAULT_REGION')
   )
   
   bucket = s3_resource.Bucket(os.environ.get('LAKEFS_REPO_NAME'))
   ```

3. **Upload Model Directory**
   ```python
   def upload_directory_to_s3(local_directory, s3_prefix):
       for root, dirs, files in os.walk(local_directory):
           for filename in files:
               file_path = os.path.join(root, filename)
               relative_path = os.path.relpath(file_path, local_directory)
               s3_key = os.path.join(s3_prefix, relative_path)
               bucket.upload_file(file_path, s3_key)
   
   upload_directory_to_s3("models", f"{trainingBranch}/models")
   ```

4. **Commit Changes to lakeFS**
   ```python
   branchTraining = repo.branch(trainingBranch)
   ref = branchTraining.commit(message='Uploaded data, artifacts and model')
   print(ref.get_commit())
   ```

#### lakeFS Commit Output

```
Commit ID: abc123def456...
Message: Uploaded data, artifacts and model
Committer: admin
Date: 2026-02-02T10:30:00Z
```

---

### 5. REST Requests Single Model

**File:** `5_rest_requests_single_model_lakefs.ipynb`

Demonstrates how to make inference requests to a model served via OpenShift AI Model Serving.

#### Key Operations

1. **Configure Model Endpoint**
   ```python
   model_url = "https://fraud-model-fraud-detection.apps.cluster.example.com/v2/models/fraud/infer"
   ```

2. **Prepare Inference Request**
   ```python
   payload = {
       "inputs": [{
           "name": "dense_input",
           "shape": [1, 5],
           "datatype": "FP32",
           "data": [0.31, 1.94, 1.0, 0.0, 0.0]
       }]
   }
   ```

3. **Send Request**
   ```python
   response = requests.post(model_url, json=payload, verify=False)
   prediction = response.json()
   ```

---

### 8. Distributed Training with lakeFS

**File:** `8_distributed_training_lakefs.ipynb`

Demonstrates distributed training patterns using lakeFS for consistent data access across workers.

#### Key Concepts

- **Data Consistency**: All workers read from the same lakeFS branch/commit
- **Reproducibility**: Commit SHA ensures exact data version is used
- **Scalability**: lakeFS S3 gateway handles concurrent access

## lakeFS Integration Patterns

### Pattern 1: Branch-Based Experimentation

```python
# Create experiment branch
experiment_branch = repo.branch("exp-001").create(source_reference="main", exist_ok=True)

# Make changes
experiment_branch.object("data/new_features.csv").upload("local_file.csv")

# If successful, merge to main
experiment_branch.merge_into("main")
```

### Pattern 2: Commit-Based Reproducibility

```python
# Pin to specific commit for reproducibility
commit_sha = "abc123"
df = pd.read_csv(
    f"s3://my-storage/{commit_sha}/data/train.csv",
    storage_options=lakefs_storage_options
)
```

### Pattern 3: Metadata Tracking

```python
# Add metadata to objects for provenance
obj = branch.object("models/model.onnx")
with obj.writer(mode='wb', metadata={
    'training_commit': current_commit_sha,
    'accuracy': '0.95',
    'created_by': 'notebook-1'
}) as writer:
    writer.write(model_bytes)
```

## Environment Setup

### Required Environment Variables

| Variable | Description | Source |
|----------|-------------|--------|
| `LAKECTL_CREDENTIALS_ACCESS_KEY_ID` | lakeFS access key | `my-storage` secret |
| `LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY` | lakeFS secret key | `my-storage` secret |
| `LAKECTL_SERVER_ENDPOINT_URL` | lakeFS S3 endpoint URL | `my-storage` secret |
| `LAKEFS_REPO_NAME` | lakeFS repository name | `my-storage` secret |
| `LAKEFS_DEFAULT_REGION` | AWS region for S3 compatibility | `my-storage` secret |

### Verifying Environment

```python
import os

required_vars = [
    'LAKECTL_CREDENTIALS_ACCESS_KEY_ID',
    'LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY',
    'LAKECTL_SERVER_ENDPOINT_URL',
    'LAKEFS_REPO_NAME',
    'LAKEFS_DEFAULT_REGION'
]

for var in required_vars:
    value = os.environ.get(var)
    status = "✓ Set" if value else "✗ Missing"
    print(f"{var}: {status}")
```

### Installing Dependencies

All notebooks require these packages:

```bash
pip install \
    onnx \
    onnxruntime \
    tf2onnx \
    lakefs==0.7.1 \
    s3fs==2024.10.0 \
    boto3 \
    botocore \
    pandas \
    numpy \
    scikit-learn \
    tensorflow
```

## References

- [lakeFS Python SDK Documentation](https://docs.lakefs.io/integrations/python.html)
- [lakeFS S3 Gateway](https://docs.lakefs.io/integrations/aws_sdk.html)
- [OpenShift AI Workbenches](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/2.25/html/working_with_workbenches)
- [TensorFlow to ONNX Conversion](https://github.com/onnx/tensorflow-onnx)
- [Main README](../README.md)

---

[← Back to Main README](../README.md) | [← Back to Pipelines Guide](PIPELINES.md)
