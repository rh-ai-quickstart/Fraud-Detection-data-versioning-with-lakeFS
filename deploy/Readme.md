# Fraud Detection with lakeFS - Deployment Guide

This directory contains the Helm chart and Makefile for deploying the Fraud Detection with lakeFS demo application.

## Prerequisites

- Kubernetes cluster or OpenShift cluster
- `kubectl` or `oc` CLI installed
- Helm 3.x installed
- Sufficient cluster resources (CPU, memory, storage)

## Quick Start

The simplest way to deploy is using the Makefile:

```bash
# Display all available commands
make help

# Deploy everything (creates namespace and installs Helm chart)
make install

# Check the status
make get-pods
```

## Makefile Commands

The Makefile provides a convenient interface for managing the deployment. Run `make help` to see all available commands and current configuration.

### Configuration

The Makefile supports the following environment variables for customization:

| Variable | Default | Description |
|----------|---------|-------------|
| `NAMESPACE` | `fraud-detection` | Kubernetes/OpenShift namespace |
| `RELEASE_NAME` | `fraud-detection` | Helm release name |
| `CHART_DIR` | `helm/fraud-detection` | Path to Helm chart directory |
| `VALUES_FILE` | `values-openshift.yaml` | Values file to use |
| `TIMEOUT` | `10m` | Helm installation timeout |

**Example:** Override defaults:

```bash
make install NAMESPACE=my-namespace TIMEOUT=15m
```

### Platform Detection

The Makefile automatically detects whether you're running on OpenShift or Kubernetes:

- If `oc` CLI is available, it uses OpenShift mode and `values-openshift.yaml`
- Otherwise, it uses Kubernetes mode with the default values file

### Deployment Commands

#### Initial Installation

```bash
# Install the complete stack (recommended for first-time deployment)
make install
```

This command will:
1. Create the namespace if it doesn't exist
2. Install the Helm chart with appropriate values for your platform
3. Wait for all resources to be ready (up to 10 minutes by default)

#### Clean Installation

```bash
# Remove everything and perform a fresh installation
make clean-install
```

This is useful when you want to start fresh, removing all existing resources before reinstalling.

#### Uninstall

```bash
# Remove the Helm release
make uninstall
```

This removes the Helm release and deletes the namespace (including PersistentVolumeClaims).

**Warning:** This will delete all data stored in the application!

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

# View PostgreSQL logs
make logs-postgres

# View Pipeline Server logs
make logs-dspa
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

# 2. Install the application
make install

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
# 1. Uninstall the current version
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
make logs-postgres
make logs-dspa

# Get service endpoints
make get-services
```

### Complete Cleanup

```bash
# Remove everything including the namespace
make clean-all
```

This will prompt for confirmation before deleting the namespace and all resources.

## Components Deployed

The Helm chart deploys the following components:

| Component | Description | Default State |
|-----------|-------------|---------------|
| **lakeFS** | Data version control system with S3-compatible API | Enabled |
| **MinIO** | S3-compatible object storage backend | Enabled |
| **PostgreSQL** | Database for Model Registry metadata storage | Enabled |
| **Jupyter Notebook** | Interactive notebooks for running the fraud detection demo | Enabled |
| **Model Registry** | OpenShift AI Model Registry for ML model lifecycle management | Enabled |
| **Data Science Pipeline Server** | OpenShift AI pipeline server for ML workflows | Enabled |
| **RBAC** | ServiceAccounts and RoleBindings for proper permissions | Enabled |
| **Post-install hooks** | Automated setup of buckets and repositories | Enabled |

## Component Details

### Model Registry

The Model Registry provides centralized management of ML models throughout their lifecycle. It enables versioning, metadata tracking, and governance for trained models.

#### Configuration

The Model Registry is configured in `values-openshift.yaml`:

```yaml
modelRegistry:
  enabled: true
  createService: true
  name: lakefs-model-registry
  namespace: rhoai-model-registries
  
  # Service ports
  grpcPort: 9090
  restPort: 8080
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `enabled` | Enable/disable Model Registry deployment | `true` |
| `createService` | Create the ModelRegistry CR | `true` |
| `name` | Name of the Model Registry instance | `lakefs-model-registry` |
| `namespace` | Target namespace for Model Registry | `rhoai-model-registries` |
| `grpcPort` | gRPC API port | `9090` |
| `restPort` | REST API port | `8080` |

#### PostgreSQL Backend

The Model Registry uses PostgreSQL for metadata storage:

```yaml
postgres:
  enabled: true
  name: postgres
  namespace: fraud-detection
  user: postgres_user
  password: postgres_password
  database: model_registry
  port: 5432
  
  persistence:
    enabled: true
    size: 1Gi
```

#### Accessing the Model Registry

Once deployed, the Model Registry is accessible via:

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

The DSPA is configured in `values-openshift.yaml`:

```yaml
dataSciencePipelines:
  enabled: true
  name: dspa
  enableSamplePipeline: false
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

#### Using the Pipeline Server

After deployment, you can:

1. **Access via OpenShift AI Dashboard**: Navigate to **Data Science Pipelines** in your project
2. **Import Pipelines**: Upload compiled pipeline YAML files
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
# Check your permissions
kubectl auth can-i create deployments --namespace=fraud-detection
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
make logs-postgres
make logs-dspa
```

### Model Registry Not Appearing in OpenShift AI

1. Ensure the `rhoai-model-registries` namespace exists
2. Check that the ModelRegistry CR was created:
   ```bash
   oc get modelregistry -n rhoai-model-registries
   ```
3. Verify PostgreSQL is running and accessible:
   ```bash
   make logs-postgres
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
modelRegistry:
  enabled: false

dataSciencePipelines:
  enabled: false
```

Then deploy:

```bash
make install VALUES_FILE=custom-values.yaml
```

### Helm Command Equivalent

The Makefile simplifies Helm commands. Here's what happens under the hood:

```bash
# make install is equivalent to:
helm install fraud-detection helm/fraud-detection \
  --namespace fraud-detection \
  --values helm/fraud-detection/values-openshift.yaml \
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
