# fraud-detection-admin

Creates **only** the OpenShift AI Model Registry (`ModelRegistry` CR and supporting Secret/ConfigMap). This chart requires **cluster admin** privileges because the Model Registry is typically installed in a shared namespace (e.g. `rhoai-model-registries`).

## Workflow

1. **Install the admin chart (with cluster admin)** to create the Model Registry:
   ```bash
   helm install fraud-detection-admin ./fraud-detection-admin \
     -n rhoai-model-registries --create-namespace
   ```
   Override `postgres.*` if your PostgreSQL is in another namespace or external (see below).

2. **Install the main fraud-detection chart** (no cluster admin) with the registry disabled:
   ```bash
   helm install fraud-detection ../fraud-detection \
     -f ../fraud-detection/values-openshift.yaml \
     -f ../fraud-detection/values-openshift-no-registry.yaml \
     -n fraud-detection --create-namespace
   ```

## Configuration

- **postgres**: Connection to the PostgreSQL used by the Model Registry. If you run the main fraud-detection chart in namespace `fraud-detection` (with Postgres enabled), use the default `postgres.host`: `postgres.fraud-detection.svc.cluster.local`, and ensure `postgres.user`, `postgres.password`, and `postgres.database` match the main chart's `postgres` values.
- **modelRegistry.namespace**: Namespace where the ModelRegistry CR is created (e.g. `rhoai-model-registries`). Must exist or use `--create-namespace`.
- **modelRegistry.access**: Optional RBAC so users and projects can use the registry. OpenShift AI creates the role `registry-users-<modelRegistry.name>` in the model registry namespace; this chart can create a RoleBinding that grants that role to:
  - **users**: list of OpenShift user names (e.g. `["user1"]`)
  - **groups**: list of OpenShift group names
  - **projects**: list of project/namespace names; all service accounts in each project get access (e.g. `["fraud-detection"]` for DSPA and notebooks in that project)

## Example: matching the main chart's Postgres

If the main chart is installed with `values-openshift.yaml` in namespace `fraud-detection`, use the same credentials when installing the admin chart:

```bash
helm install fraud-detection-admin ./fraud-detection-admin \
  -n rhoai-model-registries --create-namespace \
  --set postgres.host=postgres.fraud-detection.svc.cluster.local \
  --set postgres.user=postgres_user \
  --set postgres.password=postgres_password \
  --set postgres.database=model_registry
```

Or install the main chart first (with `modelRegistry.enabled=false` and `postgres.enabled=true`), then install the admin chart with the defaults in `values.yaml` (which point to `postgres.fraud-detection.svc.cluster.local` and the same credentials as in `values-openshift.yaml`).

### Granting access to the model registry

To allow users and the fraud-detection project to use the model registry, set `modelRegistry.access` when installing the admin chart:

```bash
helm install fraud-detection-admin ./fraud-detection-admin \
  -n rhoai-model-registries --create-namespace \
  --set postgres.host=postgres.fraud-detection.svc.cluster.local \
  --set postgres.password=postgres_password \
  --set 'modelRegistry.access.users[0]=user1' \
  --set 'modelRegistry.access.projects[0]=fraud-detection'
```

Or use a values file:

```yaml
modelRegistry:
  access:
    users: ["user1"]
    projects: ["fraud-detection"]
```

- **users**: OpenShift users who can register, view, edit, version, deploy, and delete models.
- **projects**: Namespaces whose service accounts get access (e.g. so DSPA and workbenches in `fraud-detection` can use the registry).
- **groups**: OpenShift groups that get the same access as users.
