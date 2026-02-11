# Fraud Detection with lakeFS - Makefile
# This Makefile simplifies deployment and management of the fraud-detection Helm chart

# Configuration Variables
NAMESPACE ?= fraud-detection
RELEASE_NAME ?= fraud-detection
CHART_DIR ?= helm/fraud-detection
VALUES_FILE ?= values-openshift.yaml
TIMEOUT ?= 10m

# Admin chart (PostgreSQL + Model Registry – requires cluster admin)
ADMIN_NAMESPACE ?= rhoai-model-registries
ADMIN_RELEASE_NAME ?= fraud-detection-admin
ADMIN_CHART_DIR ?= helm/fraud-detection-admin

# Detect if we're on OpenShift or Kubernetes
KUBECTL := $(shell command -v oc 2> /dev/null)
ifndef KUBECTL
	KUBECTL := kubectl
	PLATFORM := kubernetes
else
	PLATFORM := openshift
endif

.PHONY: help
help: ## Display this help message
	@echo "Fraud Detection with lakeFS - Makefile Commands"
	@echo "================================================"
	@echo ""
	@echo "Detected Platform: $(PLATFORM)"
	@echo "Using CLI: $(KUBECTL)"
	@echo ""
	@echo "Configuration:"
	@echo "  NAMESPACE=$(NAMESPACE)"
	@echo "  RELEASE_NAME=$(RELEASE_NAME)"
	@echo "  VALUES_FILE=$(VALUES_FILE)"
	@echo "  ADMIN_NAMESPACE=$(ADMIN_NAMESPACE)"
	@echo "  ADMIN_RELEASE_NAME=$(ADMIN_RELEASE_NAME)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Namespace Management

.PHONY: create-namespace
create-namespace: ## Create the namespace for fraud-detection
	@echo "Creating namespace: $(NAMESPACE)"
	@$(KUBECTL) create namespace $(NAMESPACE) || echo "Namespace $(NAMESPACE) already exists"

.PHONY: delete-namespace
delete-namespace: ## Delete the namespace (WARNING: This will delete all resources in the namespace)
	@echo "WARNING: This will delete namespace $(NAMESPACE) and all its resources!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(KUBECTL) delete namespace $(NAMESPACE); \
		echo "Namespace $(NAMESPACE) deleted"; \
	else \
		echo "Cancelled"; \
	fi

##@ Helm Chart Management

.PHONY: install-admin
install-admin: ## Install admin chart (PostgreSQL + Model Registry + RBAC; requires cluster-admin)
	@echo "Creating namespace $(ADMIN_NAMESPACE) if needed..."
	@$(KUBECTL) create namespace $(ADMIN_NAMESPACE) 2>/dev/null || true
	@echo "Installing $(ADMIN_RELEASE_NAME) in namespace $(ADMIN_NAMESPACE)..."
	@helm upgrade --install $(ADMIN_RELEASE_NAME) $(ADMIN_CHART_DIR) \
		--namespace $(ADMIN_NAMESPACE) \
		--wait \
		--timeout $(TIMEOUT)
	@echo ""
	@echo "Admin chart installed (PostgreSQL + Model Registry)."
	@echo "  Monitor RBAC setup: oc logs job/lakefs-model-registry-rbac-setup -n $(ADMIN_NAMESPACE) -f"

.PHONY: uninstall-admin
uninstall-admin: ## Uninstall the fraud-detection-admin chart
	@echo "Uninstalling $(ADMIN_RELEASE_NAME) from namespace $(ADMIN_NAMESPACE)..."
	@helm uninstall $(ADMIN_RELEASE_NAME) --namespace $(ADMIN_NAMESPACE) 2>/dev/null || echo "Release $(ADMIN_RELEASE_NAME) not found"
	@echo "Admin chart uninstall complete!"

.PHONY: clean-install
clean-install: uninstall install ## Clean install the fraud-detection Helm chart

.PHONY: install
install: ## Install the fraud-detection Helm chart (MinIO, lakeFS, notebooks, pipelines)
	@echo "Installing $(RELEASE_NAME) in namespace $(NAMESPACE)..."
	@oc new-project $(NAMESPACE) || echo "Project $(NAMESPACE) already exists"
	@if [ "$(PLATFORM)" = "openshift" ]; then \
		echo "Using OpenShift values..."; \
		helm upgrade --install $(RELEASE_NAME) $(CHART_DIR) \
			--namespace $(NAMESPACE) \
			--values $(CHART_DIR)/values-openshift.yaml \
			--values $(CHART_DIR)/values-openshift-no-registry.yaml \
			--wait \
			--timeout $(TIMEOUT); \
	else \
		echo "Using default Kubernetes values..."; \
		helm upgrade --install $(RELEASE_NAME) $(CHART_DIR) \
			--namespace $(NAMESPACE) \
			--values $(CHART_DIR)/$(VALUES_FILE) \
			--wait \
			--timeout $(TIMEOUT); \
	fi
	@echo "Installation complete!"

.PHONY: install-all
install-all: install-admin install ## Install both charts (admin first, then user – order is flexible)
	@echo ""
	@echo "Both charts installed."
	@echo "  oc get pods -n $(ADMIN_NAMESPACE)"
	@echo "  oc get pods -n $(NAMESPACE)"

.PHONY: uninstall 
uninstall:
	@echo "Uninstalling $(RELEASE_NAME) from namespace $(NAMESPACE)..."
	# This will delete the release and the namespace becuase there is persistent volume claims in the namespace
	@helm uninstall $(RELEASE_NAME) --namespace $(NAMESPACE) || echo "Release $(RELEASE_NAME) not found"
	@oc delete namespace $(NAMESPACE) || echo "Namespace $(NAMESPACE) not found so skipping deletion"
	@echo "Uninstall complete!"

.PHONY: uninstall-all
uninstall-all: uninstall uninstall-admin ## Uninstall both charts

##@ Status and Information
.PHONY: get-pods
get-pods: ## Get all pods in the namespace
	@$(KUBECTL) get pods -n $(NAMESPACE)

.PHONY: get-all
get-all: ## Get all resources in the namespace
	@$(KUBECTL) get all -n $(NAMESPACE)

.PHONY: describe
describe: ## Describe all resources in the namespace
	@$(KUBECTL) describe all -n $(NAMESPACE)

##@ Logs and Debugging

.PHONY: logs-lakefs
logs-lakefs: ## Show lakeFS logs
	@$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/component=lakefs --tail=100 -f

.PHONY: logs-minio
logs-minio: ## Show MinIO logs
	@$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/component=minio --tail=100 -f

.PHONY: logs-notebook
logs-notebook: ## Show Jupyter notebook logs
	@$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/component=notebook --tail=100 -f

##@ Access and URLs

.PHONY: get-routes
get-routes: ## Get OpenShift routes (OpenShift only)
	@if [ "$(PLATFORM)" = "openshift" ]; then \
		$(KUBECTL) get routes -n $(NAMESPACE); \
	else \
		echo "Routes are only available on OpenShift"; \
	fi

.PHONY: get-services
get-services: ## Get all services
	@$(KUBECTL) get services -n $(NAMESPACE)

.PHONY: clean
clean: uninstall ## Uninstall the chart (alias for uninstall)

.PHONY: clean-all
clean-all: uninstall-all delete-namespace ## Uninstall both charts and delete the namespace
	@echo "Complete cleanup finished!"
