# fraud-detection-admin

Cluster-admin Helm chart that deploys the **OpenShift AI Model Registry** and its **PostgreSQL** backend in a shared namespace (default: `rhoai-model-registries`). It also patches the **DataScienceCluster** to enable the Model Registry component and sets up **RBAC** so configured users and projects can access the registry.

This chart requires **cluster-admin** privileges.

## What This Chart Deploys

| Component | Description |
|-----------|-------------|
| **PostgreSQL** | Database backend for Model Registry metadata (deployed in the same namespace) |
| **Model Registry** | `ModelRegistry` CR, supporting Secret and ConfigMap |
| **DSC Patch** | Post-install hook that patches the `DataScienceCluster` to set `modelregistry.managementState: Managed` |
| **RBAC Setup** | Post-install job that waits for the operator to create the registry group/role, then grants access to configured users, groups, and projects |

## Quick Start

### Install

```bash
# Install with defaults (PostgreSQL + Model Registry + DSC patch + RBAC)
helm install fraud-detection-admin ./fraud-detection-admin \
  -n rhoai-model-registries --create-namespace
```

Or use the Makefile from the `deploy/` directory:

```bash
make install-admin
```

### Uninstall

```bash
helm uninstall fraud-detection-admin -n rhoai-model-registries
# or
make uninstall-admin
```

## Workflow

1. **Install the admin chart** (requires cluster-admin) to create PostgreSQL, Model Registry, and RBAC:

   ```bash
   make install-admin
   ```

2. **Install the main fraud-detection chart** (namespace admin only) with Model Registry disabled:

   ```bash
   make install
   ```

   On OpenShift, `make install` automatically applies both `values-openshift.yaml` and `values-openshift-no-registry.yaml`, which disables Model Registry in the user chart (since the admin chart manages it).

3. Or **install both at once**:

   ```bash
   make install-all
   ```

## Configuration

All configuration is in `values.yaml`. Key sections:

### PostgreSQL

PostgreSQL is deployed **in the same namespace** as the Model Registry (the release namespace, default `rhoai-model-registries`). The Model Registry connects to it using the in-namespace service name.

```yaml
postgres:
  enabled: true
  name: model-registry-db        # Service/deployment name
  user: postgres_user
  password: postgres_password
  database: model_registry
  port: 5432
  persistence:
    enabled: true
    size: 1Gi
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgres.enabled` | Deploy PostgreSQL alongside the Model Registry | `true` |
| `postgres.name` | Name for the PostgreSQL deployment/service | `model-registry-db` |
| `postgres.user` | Database username | `postgres_user` |
| `postgres.password` | Database password | `postgres_password` |
| `postgres.database` | Database name | `model_registry` |
| `postgres.port` | PostgreSQL port | `5432` |
| `postgres.persistence.enabled` | Enable persistent storage | `true` |
| `postgres.persistence.size` | PVC size | `1Gi` |

### Model Registry

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

| Parameter | Description | Default |
|-----------|-------------|---------|
| `modelRegistry.enabled` | Enable the Model Registry CR | `true` |
| `modelRegistry.name` | Name of the Model Registry instance | `lakefs-model-registry` |
| `modelRegistry.namespace` | Namespace for the Model Registry CR | `rhoai-model-registries` |
| `modelRegistry.grpcPort` | gRPC API port | `9090` |
| `modelRegistry.restPort` | REST API port | `8080` |
| `modelRegistry.access.users` | OpenShift users to grant registry access | `["user1"]` |
| `modelRegistry.access.groups` | OpenShift groups to grant registry access | `[]` |
| `modelRegistry.access.projects` | Namespaces whose service accounts get access | `["fraud-detection"]` |

### RBAC Setup Job

The RBAC post-install job waits for the OpenShift AI operator to create the auto-generated group and role for the registry, then adds the configured users/groups/projects.

```yaml
modelRegistry:
  rbacSetup:
    image: image-registry.openshift-image-registry.svc:5000/openshift/cli:latest
    maxRetries: 30       # 30 x 10s = 5 min max wait
    backoffLimit: 5
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `modelRegistry.rbacSetup.image` | Container image for the RBAC setup job | OpenShift CLI |
| `modelRegistry.rbacSetup.maxRetries` | Max polling attempts (10s each) | `30` |
| `modelRegistry.rbacSetup.backoffLimit` | Kubernetes job backoff limit | `5` |

### DataScienceCluster Patch

A post-install hook patches the `DataScienceCluster` CR to set `modelregistry.managementState` to `Managed`, which tells the OpenShift AI operator to reconcile Model Registry resources.

```yaml
dataScienceCluster:
  patchEnabled: true
  name: default-dsc
  managementState: Managed
  image: image-registry.openshift-image-registry.svc:5000/openshift/cli:latest
  maxRetries: 30
  backoffLimit: 3
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `dataScienceCluster.patchEnabled` | Enable the DSC patch hook | `true` |
| `dataScienceCluster.name` | Name of the DataScienceCluster CR to patch | `default-dsc` |
| `dataScienceCluster.managementState` | Desired management state for model registry | `Managed` |
| `dataScienceCluster.maxRetries` | Max polling attempts waiting for DSC | `30` |
| `dataScienceCluster.backoffLimit` | Kubernetes job backoff limit | `3` |

## Granting Access to the Model Registry

The `modelRegistry.access` section controls who can see and use the registry in the OpenShift AI dashboard.

- **users**: OpenShift users who can register, view, edit, version, deploy, and delete models.
- **projects**: Namespaces whose service accounts get access (e.g. so DSPA and workbenches in `fraud-detection` can use the registry).
- **groups**: OpenShift groups that get the same access as users.

### Example: Custom access

```bash
helm install fraud-detection-admin ./fraud-detection-admin \
  -n rhoai-model-registries --create-namespace \
  --set 'modelRegistry.access.users[0]=user1' \
  --set 'modelRegistry.access.users[1]=user2' \
  --set 'modelRegistry.access.projects[0]=fraud-detection' \
  --set 'modelRegistry.access.projects[1]=another-project'
```

Or use a values file override:

```yaml
modelRegistry:
  access:
    users: ["user1", "user2"]
    groups: ["data-scientists"]
    projects: ["fraud-detection", "another-project"]
```

## Monitoring

```bash
# Check pods in the admin namespace
oc get pods -n rhoai-model-registries

# Check the RBAC setup job
oc logs job/lakefs-model-registry-rbac-setup -n rhoai-model-registries -f

# Verify the DSC was patched
oc get datasciencecluster default-dsc -o jsonpath='{.spec.components.modelregistry.managementState}'

# Check PostgreSQL logs
oc logs -n rhoai-model-registries -l app=model-registry-db --tail=100

# Verify the Model Registry CR
oc get modelregistry -n rhoai-model-registries
```

## Troubleshooting

### RBAC setup job fails

The job waits for the operator to create the group `lakefs-model-registry-users` and role `registry-user-lakefs-model-registry`. If these never appear:

1. Verify the DSC patch succeeded: `oc get datasciencecluster default-dsc -o yaml`
2. Check the OpenShift AI operator logs
3. Ensure the `ModelRegistry` CR was created: `oc get modelregistry -n rhoai-model-registries`

### PostgreSQL not starting

1. Check PVC was created: `oc get pvc -n rhoai-model-registries`
2. Check pod events: `oc describe pod -n rhoai-model-registries -l app=model-registry-db`
3. Verify the ImageStream exists (OpenShift): `oc get is -n rhoai-model-registries`
