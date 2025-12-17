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

- **lakeFS**: Data version control system
- **MinIO**: S3-compatible object storage
- **Jupyter Notebook**: Interactive notebooks for running the fraud detection demo
- **RBAC**: ServiceAccounts and RoleBindings for proper permissions
- **Post-install hooks**: Automated setup of buckets and repositories

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
make logs-lakefs    # or logs-minio, logs-notebook
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

- [Helm Chart Documentation](helm/fraud-detection/README.md)
- [Demo Notebooks](../demo/notebooks/)
- [Main Project README](../README.md)

## Support

For issues or questions, please refer to the main project repository or documentation.

