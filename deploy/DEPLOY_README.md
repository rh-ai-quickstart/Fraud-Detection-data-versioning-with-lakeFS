# Fraud Detection with lakeFS - Deployment Guide

This directory contains the Helm charts and Makefile for deploying the Fraud Detection with lakeFS demo application.

The deployment uses **two Helm charts**:

| Chart | Directory | Namespace | Requires | Deploys |
|-------|-----------|-----------|----------|---------|
| `fraud-detection-admin` | `helm/fraud-detection-admin` | `rhoai-model-registries` | **cluster-admin** | PostgreSQL, Model Registry, DSC patch, RBAC |
| `fraud-detection` | `helm/fraud-detection` | `fraud-detection` | namespace **admin** | lakeFS, MinIO, Jupyter notebook, Data Science Pipeline Server |

## Prerequisites

- OpenShift cluster (or Kubernetes cluster for the user chart only)
- `oc` (OpenShift) or `kubectl` (Kubernetes) CLI installed
- Helm 3.x installed
- Sufficient cluster resources (CPU, memory, storage)
- **cluster-admin** for the admin chart; namespace **admin** for the user chart

## Quick Start

The simplest way to deploy is using the Makefile:

```bash
# Display all available commands
make help

# Deploy both charts (requires cluster-admin)
make install-all

# Check the status
make get-pods
```

If you only need the core lakeFS demo (no Model Registry), you can skip the admin chart:

```bash
make install
```

## Makefile Commands

The Makefile provides a convenient interface for managing the deployment. Run `make help` to see all available commands and current configuration.

### Configuration

The Makefile supports the following environment variables for customization:

**User chart variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `NAMESPACE` | `fraud-detection` | Namespace for the user chart |
| `RELEASE_NAME` | `fraud-detection` | Helm release name for the user chart |
| `CHART_DIR` | `helm/fraud-detection` | Path to user Helm chart directory |
| `VALUES_FILE` | `values-openshift.yaml` | Values file (used on Kubernetes only; OpenShift auto-selects) |
| `TIMEOUT` | `10m` | Helm installation timeout |

**Admin chart variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_NAMESPACE` | `rhoai-model-registries` | Namespace for the admin chart |
| `ADMIN_RELEASE_NAME` | `fraud-detection-admin` | Helm release name for the admin chart |
| `ADMIN_CHART_DIR` | `helm/fraud-detection-admin` | Path to admin Helm chart directory |

**Example:** Override defaults:

```bash
make install NAMESPACE=my-namespace TIMEOUT=15m
make install-admin ADMIN_NAMESPACE=my-model-registries
```

### Platform Detection

The Makefile automatically detects whether you're running on OpenShift or Kubernetes:

- If `oc` CLI is available, it uses OpenShift mode and applies both `values-openshift.yaml` and `values-openshift-no-registry.yaml` (disabling Model Registry in the user chart since it is managed by the admin chart)
- Otherwise, it uses Kubernetes mode with the `VALUES_FILE` value

### Deployment Commands

#### Full Installation (both charts)

```bash
# Install admin chart first, then user chart (requires cluster-admin)
make install-all
```

This runs `install-admin` followed by `install` (the order is flexible).

#### Admin Chart Only

```bash
# Deploy PostgreSQL + Model Registry + DSC patch + RBAC (requires cluster-admin)
make install-admin
```

This command will:
1. Create the `rhoai-model-registries` namespace if it doesn't exist
2. Deploy PostgreSQL and Model Registry
3. Patch the DataScienceCluster to enable Model Registry
4. Set up RBAC so configured users and projects can access the registry

#### User Chart Only

```bash
# Deploy lakeFS, MinIO, notebooks, pipelines (namespace admin)
make install
```

This command will:
1. Create the namespace as an OpenShift project (or Kubernetes namespace)
2. Install the Helm chart with appropriate values for your platform
3. Run post-install hooks to create MinIO buckets, lakeFS repositories, and upload the pipeline
4. Wait for all resources to be ready (up to 10 minutes by default)

#### Clean Installation

```bash
# Remove the user chart and perform a fresh installation
make clean-install
```

This is useful when you want to start fresh, removing all existing resources before reinstalling.

#### Uninstall

```bash
# Remove the user chart and delete its namespace
make uninstall

# Remove the admin chart
make uninstall-admin

# Remove both charts
make uninstall-all
```

**Warning:** `make uninstall` will delete the namespace and all data (including PersistentVolumeClaims).

### Namespace Management

```bash
# Create the namespace manually (usually not needed, done automatically by install)
make create-namespace

# Delete the namespace and ALL its resources
make delete-namespace
```

The `delete-namespace` command will prompt for confirmation before proceeding.

### Monitoring and Status

#### View Resources

```bash
# List all pods in the namespace
make get-pods

# List all resources (pods, services, deployments, etc.)
make get-all

# Get detailed information about all resources
make describe
```

#### View Logs

Monitor logs from specific components:

```bash
# View lakeFS logs (follows log output)
make logs-lakefs

# View MinIO logs
make logs-minio

# View Jupyter notebook logs
make logs-notebook
```

For components not covered by Makefile targets, use `oc` directly:

```bash
# View PostgreSQL logs (admin namespace)
oc logs -n rhoai-model-registries -l app=model-registry-db --tail=100 -f

# View Pipeline Server logs
oc logs -n fraud-detection -l app.kubernetes.io/name=data-science-pipelines-operator --tail=100 -f

# View admin chart RBAC setup job logs
oc logs job/lakefs-model-registry-rbac-setup -n rhoai-model-registries -f
```

Press `Ctrl+C` to stop following logs.

### Access and URLs

```bash
# Get all services and their endpoints
make get-services

# Get OpenShift routes (OpenShift only)
make get-routes
```

## Typical Deployment Workflow

### First-Time Deployment

```bash
# 1. Review the configuration
make help

# 2. Install both charts (or just 'make install' for user chart only)
make install-all

# 3. Monitor the deployment
make get-pods

# 4. Check the logs if needed
make logs-lakefs

# 5. Get access URLs
make get-routes    # OpenShift
make get-services  # Kubernetes
```

### Updating the Deployment

```bash
# 1. Uninstall the current user chart
make uninstall

# 2. Reinstall with latest changes
make install
```

Or use the combined command:

```bash
make clean-install
```

### Troubleshooting

```bash
# Check pod status
make get-pods

# View detailed resource information
make describe

# Check component logs
make logs-lakefs
make logs-minio
make logs-notebook

# Check admin chart pods
oc get pods -n rhoai-model-registries

# Get service endpoints
make get-services
```

### Complete Cleanup

```bash
# Remove both charts and delete namespaces
make clean-all
```

This will uninstall both Helm releases and prompt for confirmation before deleting the namespace.

## Components Deployed

### User Chart (`fraud-detection`)

| Component | Description | Default State |
|-----------|-------------|---------------|
| **lakeFS** | Data version control system with S3-compatible API | Enabled |
| **MinIO** | S3-compatible object storage backend | Enabled |
| **Jupyter Notebook** | Interactive notebooks for running the fraud detection demo | Enabled |
| **Data Science Pipeline Server** | OpenShift AI pipeline server for ML workflows | Enabled |
| **RBAC** | ServiceAccounts and RoleBindings for proper permissions | Enabled |
| **Post-install hooks** | Automated setup of MinIO buckets, lakeFS repositories, and pipeline upload | Enabled |

### Admin Chart (`fraud-detection-admin`)

| Component | Description | Default State |
|-----------|-------------|---------------|
| **PostgreSQL** | Database for Model Registry metadata storage | Enabled |
| **Model Registry** | OpenShift AI Model Registry (`ModelRegistry` CR) for ML model lifecycle | Enabled |
| **DSC Patch** | Post-install hook to enable Model Registry in the DataScienceCluster | Enabled |
| **RBAC Setup** | Post-install job to grant users/groups/projects access to the registry | Enabled |

## Component Details

### Model Registry (Admin Chart)

The Model Registry provides centralized management of ML models throughout their lifecycle. It enables versioning, metadata tracking, and governance for trained models.

> [!IMPORTANT]
> The Model Registry and its PostgreSQL backend are deployed by the **admin chart** (`fraud-detection-admin`), not the user chart. See [fraud-detection-admin/README.md](helm/fraud-detection-admin/README.md) for full configuration details.

#### Configuration

The Model Registry is configured in `helm/fraud-detection-admin/values.yaml`:

```yaml
modelRegistry:
  enabled: true
  name: lakefs-model-registry
  namespace: rhoai-model-registries
  grpcPort: 9090
  restPort: 8080
  access:
    users: ["user1"]
    groups: []
    projects: ["fraud-detection"]
```

The admin chart also deploys PostgreSQL in the same namespace:

```yaml
postgres:
  enabled: true
  name: model-registry-db
  user: postgres_user
  password: postgres_password
  database: model_registry
  port: 5432
  persistence:
    enabled: true
    size: 1Gi
```

#### Accessing the Model Registry

Once deployed via `make install-admin`, the Model Registry is accessible via:

- **REST API**: `http://lakefs-model-registry-rest.rhoai-model-registries.svc:8080`
- **gRPC API**: `lakefs-model-registry-grpc.rhoai-model-registries.svc:9090`

In OpenShift AI, the Model Registry will appear in the dashboard under **Model Registry** and can be used to:
- Register trained models
- Track model versions
- Store model metadata and artifacts
- Manage model deployment lifecycle

### Data Science Pipeline Server (DSPA)

The Data Science Pipeline Server enables orchestration of ML workflows using Kubeflow Pipelines. It allows you to define, run, and monitor multi-step ML pipelines.

#### Configuration

The DSPA is configured in `helm/fraud-detection/values-openshift.yaml`:

```yaml
dataSciencePipelines:
  enabled: true
  name: dspa
  enableSamplePipeline: false
  uploadPipeline: true
  uploadPipelineUrl: "https://raw.githubusercontent.com/.../7_get_data_train_upload_lakefs.yaml"
  uploadPipelineName: "7-get-data-train-upload-lakefs"
  database:
    name: mlpipeline
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 1Gi
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

| Parameter | Description | Default |
|-----------|-------------|---------|
| `enabled` | Enable/disable DSPA deployment | `true` |
| `name` | Name of the DSPA instance | `dspa` |
| `enableSamplePipeline` | Deploy sample pipeline | `false` |
| `uploadPipeline` | Auto-upload the lakeFS pipeline via post-install hook | `true` |
| `uploadPipelineName` | Display name for the uploaded pipeline | `7-get-data-train-upload-lakefs` |
| `database.name` | Pipeline database name | `mlpipeline` |
| `objectStorage.bucket` | S3 bucket for pipeline artifacts | `pipeline-artifacts` |
| `objectStorage.host` | S3-compatible storage host | `minio.fraud-detection.svc.cluster.local` |
| `objectStorage.port` | Storage port | `9000` |

#### DSPA Components

When enabled, the DSPA deploys:

- **API Server**: REST/gRPC API for pipeline management
- **Persistence Agent**: Tracks pipeline run status and metadata
- **Scheduled Workflow**: Manages scheduled/recurring pipeline runs
- **MariaDB**: Stores pipeline metadata and run history

#### Automatic Pipeline Upload

When `uploadPipeline: true` (the default), a post-install hook automatically:
1. Waits for the DSPA API server to become ready
2. Downloads the compiled pipeline YAML from GitHub
3. Uploads it to the pipeline server using the KFP SDK

The pipeline appears in the OpenShift AI dashboard as **7-get-data-train-upload-lakefs** without any manual import.

#### Using the Pipeline Server

After deployment, you can:

1. **Access via OpenShift AI Dashboard**: Navigate to **Data Science Pipelines** in your project
2. **Import Pipelines**: Upload compiled pipeline YAML files (or use the auto-uploaded one)
3. **Create Runs**: Execute pipelines with parameters
4. **Monitor Progress**: View run status, logs, and artifacts

Example pipeline execution from a notebook:

```python
from kfp import Client

# Connect to the pipeline server
client = Client(host='https://ds-pipeline-dspa.fraud-detection.svc:8443')

# List existing pipelines
pipelines = client.list_pipelines()

# Create a run
run = client.create_run_from_pipeline_func(
    my_pipeline,
    arguments={'param1': 'value1'}
)
```

For detailed pipeline examples, see [demo/pipelines/PipelinesReadMe.md](../demo/pipelines/PipelinesReadMe.md).

### MinIO Object Storage

MinIO provides S3-compatible object storage for:
- Training data
- Model artifacts
- Pipeline artifacts

#### Configuration

```yaml
minio:
  enabled: true
  buckets:
    create: true
    names:
      - pipeline-artifacts
      - my-storage
      - quickstart
```

#### Default Buckets

| Bucket | Purpose |
|--------|---------|
| `pipeline-artifacts` | Stores DSPA pipeline artifacts and intermediate outputs |
| `my-storage` | Default bucket for notebook data connections |
| `quickstart` | lakeFS repository storage namespace |

## Common Issues

### Installation Timeout

If the installation times out, increase the timeout value:

```bash
make install TIMEOUT=20m
```

### Permission Errors

Ensure you have sufficient permissions in your cluster:

```bash
# Check namespace-level permissions (user chart)
oc auth can-i create deployments --namespace=fraud-detection

# The admin chart requires cluster-admin
oc auth can-i create clusterrole
```

### Pod Failures

Check the logs of failed pods:

```bash
# List all pods
make get-pods

# View logs for specific component
make logs-lakefs
make logs-minio
make logs-notebook

# View PostgreSQL logs in the admin namespace
oc logs -n rhoai-model-registries -l app=model-registry-db --tail=100
```

### Model Registry Not Appearing in OpenShift AI

1. Ensure the admin chart was installed: `helm list -n rhoai-model-registries`
2. Check that the DataScienceCluster was patched to enable Model Registry:
   ```bash
   oc get datasciencecluster default-dsc -o jsonpath='{.spec.components.modelregistry.managementState}'
   # Should return "Managed"
   ```
3. Check that the ModelRegistry CR was created:
   ```bash
   oc get modelregistry -n rhoai-model-registries
   ```
4. Verify PostgreSQL is running:
   ```bash
   oc get pods -n rhoai-model-registries -l app=model-registry-db
   ```
5. Check the RBAC setup job completed:
   ```bash
   oc logs job/lakefs-model-registry-rbac-setup -n rhoai-model-registries
   ```

### Pipeline Server Issues

1. Check DSPA status:
   ```bash
   oc get dspa -n fraud-detection
   ```
2. Verify the `pipeline-artifacts` bucket exists in MinIO
3. Check MariaDB pod status:
   ```bash
   oc get pods -n fraud-detection | grep mariadb
   ```
4. If the auto-uploaded pipeline is missing, check the upload job:
   ```bash
   oc get jobs -n fraud-detection | grep upload-pipeline
   oc logs job/fraud-detection-upload-pipeline -n fraud-detection
   ```

## Advanced Usage

### Using Custom Values Files

```bash
make install VALUES_FILE=my-custom-values.yaml
```

### Deploying to Multiple Namespaces

```bash
# Deploy to dev environment
make install NAMESPACE=fraud-detection-dev RELEASE_NAME=fraud-dev

# Deploy to production environment
make install NAMESPACE=fraud-detection-prod RELEASE_NAME=fraud-prod
```

### Disabling Components

To deploy without certain components, create a custom values file:

```yaml
# custom-values.yaml
dataSciencePipelines:
  enabled: false

notebook:
  enabled: false
```

Then deploy:

```bash
make install VALUES_FILE=custom-values.yaml
```

### Helm Command Equivalents

The Makefile simplifies Helm commands. Here's what happens under the hood:

```bash
# make install (on OpenShift) is equivalent to:
oc new-project fraud-detection
helm upgrade --install fraud-detection helm/fraud-detection \
  --namespace fraud-detection \
  --values helm/fraud-detection/values-openshift.yaml \
  --values helm/fraud-detection/values-openshift-no-registry.yaml \
  --wait \
  --timeout 10m

# make install-admin is equivalent to:
oc create namespace rhoai-model-registries
helm upgrade --install fraud-detection-admin helm/fraud-detection-admin \
  --namespace rhoai-model-registries \
  --wait \
  --timeout 10m
```

## Additional Resources

- [Demo Notebooks](../demo/notebooks/)
- [Pipeline Examples](../demo/pipelines/PipelinesReadMe.md)
- [Main Project README](../README.md)
- [lakeFS Documentation](https://docs.lakefs.io/)
- [OpenShift AI Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/)

## Support

For issues or questions, please refer to the main project repository or documentation.
