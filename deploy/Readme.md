# Fraud Detection with LakeFS - Helm Chart

This Helm chart deploys a complete fraud detection environment with LakeFS for data versioning and MinIO for object storage.

## Overview

This chart includes:
- **MinIO** - S3-compatible object storage (v0.5.2 from ai-architecture-charts)
- **LakeFS** - Git-like data versioning system
- **Automated Setup** - Buckets and repositories created automatically via Helm hooks
- **Jupyter Notebooks** - Optional OpenShift AI integration with pre-configured notebooks (see [NOTEBOOKS.md](NOTEBOOKS.md))

### Chart Dependencies

This chart uses the published [ai-architecture-charts](https://github.com/rh-ai-quickstart/ai-architecture-charts) MinIO chart as a dependency:

```yaml
dependencies:
  - name: minio
    version: 0.5.2
    repository: https://rh-ai-quickstart.github.io/ai-architecture-charts
    condition: minio.enabled
```

## Prerequisites

- Kubernetes 1.19+ or OpenShift 4.12+
- Helm 3.x
- kubectl or oc CLI configured
- PersistentVolume provisioner support (for MinIO storage)
- **For Jupyter Notebooks**: OpenShift AI or Open Data Hub installed (OpenShift only)

## Documentation
- **[values-openshift.yaml](values-openshift.yaml)** - OpenShift-specific overrides
- **[README.md](README.md) ** Guide for using make file and deploying the projects

## Quick Start

### Deploy on OpenShift

Note all deployments can be handled with the make file. 
The Idea is to use values-openshift.yaml to configure and make commands
to deploy. 

**install** `make install`: Install chart based on values-openshift.yaml
**uninstall** `make uninstall`: Uninstall Chart in namespace.

**Clean Install** `make clean-install` : Uninstall, remove namespace, and install

## Deployment Sequence

The chart manages dependencies automatically using Helm hooks and init containers:

1. **Dependency Download**: `helm dependency update` downloads MinIO chart (v0.5.2)
2. **Pre-install Hook** (weight: -10): Create ServiceAccounts and RBAC
3. **MinIO Secret**: Static credentials created from values
4. **MinIO StatefulSet**: Starts with persistent storage (volumeClaimTemplates)
5. **LakeFS Init Container**: Waits for MinIO to be ready
6. **LakeFS ConfigMap**: Configuration created from values
7. **LakeFS Deployment**: Starts after init container succeeds
8. **Post-install Hook** (weight: 3): Create S3 buckets in MinIO
9. **Post-install Hook** (weight: 5): Create repositories in LakeFS

Total deployment time: 5-10 minutes

## What Gets Deployed

### MinIO (Object Storage)
- **Chart**: Published ai-architecture-charts MinIO v0.5.2
- **Deployment**: StatefulSet (single replica)
- **Storage**: 10Gi via volumeClaimTemplates (configurable)
- **Ports**: API (9000), Console (9090)
- **Credentials**: Static credentials from values (stored in secret `minio`)
- **Buckets**: 3 buckets created automatically via parent chart hook
  - `pipeline-artifacts`
  - `my-storage`
  - `quickstart`

### LakeFS (Data Versioning)
- **Deployment**: Single replica (configurable)
- **Database**: Local (ephemeral) - can be configured for PostgreSQL
- **Storage Backend**: MinIO S3
- **Admin Credentials**: Configured in values
- **Repositories**: 2 repositories created automatically
  - `quickstart` (with sample data)
  - `my-storage` (empty)

### Jupyter Notebook (OpenShift AI Integration)
- **Enabled**: Only on OpenShift with `values-openshift.yaml` (disabled by default)
- **Custom Resource**: Kubeflow Notebook CR for OpenShift AI/Open Data Hub
- **Image**: ODH Minimal Notebook (Python 3.9+)
- **Storage**: 20Gi PVC for notebook workspace
- **Pre-configured**: LakeFS and MinIO connection details via environment variables
- **Git Sync**: Automatically clones demo notebooks from repository
- **Notebooks Included**: 6 fraud detection notebooks with LakeFS integration
  - `1_experiment_train_lakefs.ipynb`
  - `2_save_model_lakefs.ipynb`
  - `3_rest_requests_multi_model_lakefs.ipynb`
  - `4_grpc_requests_multi_model_lakefs.ipynb`
  - `5_rest_requests_single_model_lakefs.ipynb`
  - `8_distributed_training_lakefs.ipynb`

## Accessing Services

### Get Service URLs (OpenShift)

```bash
# LakeFS UI
oc get route lakefs -n fraud-detection -o jsonpath='{.spec.host}'

# MinIO Console
oc get route minio-console -n fraud-detection -o jsonpath='{.spec.host}'
```

### Accessing Notebooks (OpenShift AI)

When deployed on OpenShift with `values-openshift.yaml`, notebooks are automatically available in the OpenShift AI dashboard:

1. Navigate to the OpenShift AI dashboard
2. Go to the **Data Science Projects** section
3. Select the `fraud-detection` project
4. Click on the notebook server to access JupyterLab
5. The demo notebooks will be automatically cloned into the `demo/notebooks/` directory

Alternatively, get the notebook URL directly:

```bash
# Get the notebook route
oc get notebook fraud-detection-notebook -n fraud-detection \
  -o jsonpath='{.metadata.annotations.notebooks\.opendatahub\.io/last-activity}'
```

**Pre-configured Environment Variables:**
- `LAKEFS_ENDPOINT`: LakeFS API endpoint
- `LAKEFS_ACCESS_KEY_ID`: LakeFS access key
- `LAKEFS_SECRET_ACCESS_KEY`: LakeFS secret key
- `AWS_S3_ENDPOINT`: MinIO S3 endpoint
- `AWS_ACCESS_KEY_ID`: MinIO access key
- `AWS_SECRET_ACCESS_KEY`: MinIO secret key

### Port Forwarding (Kubernetes)

```bash
# LakeFS UI
kubectl port-forward svc/lakefs 8000:80 -n fraud-detection
# Access at http://localhost:8000

# MinIO Console
kubectl port-forward svc/minio 9090:9090 -n fraud-detection
# Access at http://localhost:9090
```

## Default Credentials

### LakeFS
- **Username**: `admin`
- **Access Key ID**: `something` ⚠️ Change in production!
- **Secret Access Key**: `simple` ⚠️ Change in production!

To change, edit `values.yaml`:
```yaml
lakefs:
  adminCredentials:
    accessKeyId: your-secure-key
    secretAccessKey: your-secure-secret
```

### MinIO
Default credentials are set in `values.yaml`. To retrieve deployed credentials:

```bash
# Get username
kubectl get secret minio -n fraud-detection \
  -o jsonpath='{.data.user}' | base64 -d

# Get password
kubectl get secret minio -n fraud-detection \
  -o jsonpath='{.data.password}' | base64 -d
```

To change credentials, edit `values.yaml`:
```yaml
minio:
  secret:
    user: your-username
    password: your-secure-password
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `minio.enabled` | Enable MinIO dependency | `true` |
| `minio.volumeClaimTemplates[0].spec.resources.requests.storage` | MinIO storage size | `10Gi` |
| `minio.secret.user` | MinIO username | `minio_fraud_user` |
| `minio.secret.password` | MinIO password | `minio_fraud_password` |
| `minio.resources.requests.memory` | MinIO memory request | `1Gi` |
| `minio.buckets.create` | Auto-create buckets | `true` |
| `lakefs.image.tag` | LakeFS version | `1.73.0` |
| `lakefs.adminCredentials.accessKeyId` | LakeFS admin access key | `something` |
| `lakefs.adminCredentials.secretAccessKey` | LakeFS admin secret | `simple` |
| `repositories.create` | Auto-create repositories | `true` |
| `openshift.enabled` | Enable OpenShift features | `false` |
| `openshift.routes.enabled` | Create OpenShift routes | `false` |
| `notebook.enabled` | Enable Jupyter notebook | `false` |
| `notebook.storage.size` | Notebook storage size | `20Gi` |
| `notebook.resources.limits.memory` | Notebook memory limit | `8Gi` |
| `notebook.gitSync.enabled` | Auto-clone notebooks from git | `false` |

### Customizing Notebook Configuration

The notebook feature is designed for OpenShift AI integration. To customize:

```yaml
notebook:
  enabled: true
  username: "your-username"
  
  # Notebook image (ODH/RHODS compatible)
  image:
    repository: quay.io/modh/odh-minimal-notebook-image-n
    tag: "2024.2"
  
  # Resource limits
  resources:
    limits:
      cpu: "4"
      memory: "16Gi"
  
  # Storage for notebooks and data
  storage:
    size: 50Gi
    storageClassName: "gp3"
  
  # Automatically clone demo notebooks
  gitSync:
    enabled: true
    repo: "https://github.com/rh-aiservices-bu/Fraud-Detection-data-versioning-with-lakeFS.git"
    branch: "main"
```

### Customizing Repositories

Edit `values.yaml`:

```yaml
repositories:
  create: true
  repos:
    - name: my-custom-repo
      storageNamespace: s3://my-custom-repo/
      defaultBranch: main
      sampleData: false
```

### Customizing Buckets

Edit `values.yaml`:

```yaml
minio:
  buckets:
    create: true
    names:
      - my-bucket-1
      - my-bucket-2
      - my-bucket-3
```

### Using External S3

To use external S3 instead of MinIO:

```yaml
minio:
  enabled: false

lakefs:
  config:
    blockstore:
      type: s3
      s3:
        endpoint: https://s3.amazonaws.com
        region: us-east-1
        forcePathStyle: false
        # Set credentials via environment variables in deployment
```

### Resource Configuration

OpenShift production settings in `values-openshift.yaml`:

```yaml
minio:
  resources:
    limits:
      cpu: "2"
      memory: 2Gi
    requests:
      cpu: 200m
      memory: 1Gi

lakefs:
  resources:
    limits:
      cpu: "2"
      memory: 2Gi
    requests:
      cpu: 500m
      memory: 1Gi
```

## Support

- [LakeFS Documentation](https://docs.lakefs.io/)
- [MinIO Documentation](https://min.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)

## Chart Dependencies

This chart uses published dependencies from ai-architecture-charts:

- **MinIO v0.5.2**: S3-compatible object storage with StatefulSet deployment

To update dependencies:
```bash
# Update to latest versions in Chart.yaml
helm dependency update

# View current dependencies
helm dependency list
```

Dependency files:
- `Chart.yaml` - Dependency definitions
- `Chart.lock` - Locked versions (committed to git)
- `charts/minio-0.5.2.tgz` - Downloaded chart (not committed to git)

## Contributing

When making changes to this chart:

1. Update dependencies if Chart.yaml changed: `helm dependency update`
2. Test with `helm lint .`
3. Test template rendering: `helm template test . --values values.yaml`
4. Test on both Kubernetes and OpenShift
5. Update this README with any configuration changes
6. Commit `Chart.lock` but not `charts/*.tgz`

## License

See main project LICENSE file.

