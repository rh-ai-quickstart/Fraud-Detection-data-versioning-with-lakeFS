# Fraud Detection with LakeFS - Helm Chart

This Helm chart deploys a complete fraud detection environment with LakeFS for data versioning and MinIO for object storage.

## Overview

This chart includes:
- **MinIO** - S3-compatible object storage (v0.5.2 from ai-architecture-charts)
- **LakeFS** - Git-like data versioning system
- **Automated Setup** - Buckets and repositories created automatically via Helm hooks

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

## Quick Start

### Deploy on OpenShift

```bash
# Create namespace
oc create namespace fraud-detection

# Update dependencies (downloads MinIO chart)
helm dependency update

# Deploy with OpenShift-specific settings
helm install fraud-detection . \
  --namespace fraud-detection \
  --values values-openshift.yaml \
  --wait \
  --timeout 10m
```

### Deploy on Kubernetes

```bash
# Create namespace
kubectl create namespace fraud-detection

# Update dependencies (downloads MinIO chart)
helm dependency update

# Deploy with default settings
helm install fraud-detection . \
  --namespace fraud-detection \
  --wait \
  --timeout 10m
```

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

## Accessing Services

### Get Service URLs (OpenShift)

```bash
# LakeFS UI
oc get route fraud-detection-lakefs -n fraud-detection -o jsonpath='{.spec.host}'

# MinIO Console
oc get route fraud-detection-minio-console -n fraud-detection -o jsonpath='{.spec.host}'
```

### Port Forwarding (Kubernetes)

```bash
# LakeFS UI
kubectl port-forward svc/fraud-detection-lakefs 8000:80 -n fraud-detection
# Access at http://localhost:8000

# MinIO Console
kubectl port-forward svc/fraud-detection-minio 9090:9090 -n fraud-detection
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

## Upgrading

```bash
# Update dependencies if MinIO version changed
helm dependency update

# Update configuration in values file, then:
helm upgrade fraud-detection . \
  --namespace fraud-detection \
  --values values-openshift.yaml \
  --wait
```

**Note**: Post-install hooks (bucket/repo creation) only run on install, not upgrade.

### Updating MinIO Version

To use a newer MinIO chart version:

```yaml
# Edit Chart.yaml
dependencies:
  - name: minio
    version: 0.5.3  # Update version
    repository: https://rh-ai-quickstart.github.io/ai-architecture-charts
    condition: minio.enabled
```

Then run:
```bash
helm dependency update
helm upgrade fraud-detection . --values values-openshift.yaml
```

## Rollback

```bash
# Rollback to previous version
helm rollback fraud-detection -n fraud-detection

# Rollback to specific revision
helm rollback fraud-detection 1 -n fraud-detection
```

## Uninstalling

```bash
# Remove all resources
helm uninstall fraud-detection --namespace fraud-detection

# Optional: Delete PVCs (data loss!)
kubectl delete pvc -l app.kubernetes.io/instance=fraud-detection -n fraud-detection

# Optional: Delete namespace
kubectl delete namespace fraud-detection
```

## Monitoring Deployment

### Watch Pod Status
```bash
kubectl get pods -n fraud-detection -w
```

### Check Hook Jobs
```bash
# List all jobs
kubectl get jobs -n fraud-detection

# Check specific job logs
kubectl logs -n fraud-detection job/fraud-detection-minio-create-buckets
kubectl logs -n fraud-detection job/fraud-detection-lakefs-create-repos
```

### Follow LakeFS Logs
```bash
kubectl logs -n fraud-detection -l app.kubernetes.io/name=lakefs -f
```

### Check All Resources
```bash
kubectl get all -n fraud-detection
```

## Troubleshooting

### MinIO Pod Not Starting

Check StatefulSet and PVC status:
```bash
# Check StatefulSet
kubectl get statefulset fraud-detection-minio -n fraud-detection

# Check PVC (auto-created by StatefulSet)
kubectl get pvc -n fraud-detection
kubectl describe pvc minio-data-fraud-detection-minio-0 -n fraud-detection
```

### LakeFS Stuck in Init State

Check if MinIO is running:
```bash
kubectl get pods -n fraud-detection -l app.kubernetes.io/name=minio
kubectl logs -n fraud-detection deployment/fraud-detection-lakefs -c wait-for-minio
```

### Repositories Not Created

Check if the job ran:
```bash
kubectl get jobs -n fraud-detection
kubectl logs -n fraud-detection job/fraud-detection-lakefs-create-repos
```

Manually create repositories if needed:
```bash
LAKEFS_URL=$(oc get route fraud-detection-lakefs -n fraud-detection -o jsonpath='{.spec.host}')

curl -k -u "something:simple" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"quickstart","storage_namespace":"s3://quickstart/","default_branch":"main","sample_data":true}' \
  https://${LAKEFS_URL}/api/v1/repositories
```

### Permission Denied Errors

On OpenShift, ensure proper security context constraints:
```bash
# Check pod security
kubectl get pods -n fraud-detection -o yaml | grep -A 10 securityContext
```

The chart is designed to work with OpenShift's restricted SCC.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Helm Chart (fraud-detection)              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Dependency: MinIO v0.5.2 (ai-architecture-charts)    │ │
│  │  Downloaded to: charts/minio-0.5.2.tgz                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Pre-install Hooks (RBAC)                              │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────┐  ┌──────────────────────────────────┐│
│  │ MinIO Chart      │  │   LakeFS Main Chart              ││
│  │ (Published 0.5.2)│  │                                  ││
│  │                  │  │  ┌──────────────────────────────┐││
│  │  ┌────────────┐  │  │  │ Init: Wait for MinIO         │││
│  │  │StatefulSet │  │  │  │                              │││
│  │  │            │◄─┼──┼──┤ Deployment                   │││
│  │  │ PVC (10Gi) │  │  │  │   - ConfigMap                │││
│  │  │volumeClaim │  │  │  │   - Service                  │││
│  │  │Templates   │  │  │  │   - Route (OpenShift)        │││
│  │  └────────────┘  │  │  └──────────────────────────────┘││
│  │  ┌────────────┐  │  │                                  ││
│  │  │ Secret:    │  │  └──────────────────────────────────┘│
│  │  │   minio    │  │                                       │
│  │  └────────────┘  │                                       │
│  │  ┌────────────┐  │                                       │
│  │  │  Service   │  │                                       │
│  │  │  Routes    │  │                                       │
│  │  └────────────┘  │                                       │
│  └──────────────────┘                                       │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Post-install Hooks (Parent Chart)                    │ │
│  │  - Create Buckets (weight: 3)                         │ │
│  │  - Create LakeFS Repos (weight: 5)                    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Comparison with Legacy deploy.sh

| Feature | deploy.sh | Helm Chart |
|---------|-----------|------------|
| Deployment | `./deploy.sh lakefs` | `helm install fraud-detection .` |
| MinIO | Embedded manifests | Published chart dependency |
| Wait Strategy | Fixed sleeps (100s) | Init containers + hooks |
| Platform | OpenShift only | Any Kubernetes |
| Rollback | Manual | `helm rollback` |
| Upgrades | Re-run script | `helm upgrade` |
| Configuration | Multiple files | Single values file |
| Idempotency | Partial | Full |
| Dependencies | Manual | `helm dependency update` |

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

