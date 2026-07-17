# UI-Based Demo Suggestions

[← Back to Main README](../README.md)

This document summarizes the purpose and functionality of the **Fraud Detection data versioning with lakeFS** quickstart, and proposes five approaches for converting it into a UI-based demo.

## Project Purpose and Functionality

**Fraud Detection data versioning with lakeFS** is a Red Hat OpenShift AI quickstart that demonstrates how **lakeFS acts as a Git-like data control plane** on top of S3-compatible object storage (MinIO) for an ML fraud-detection workflow.

### Core Idea

The project intentionally separates responsibilities across two layers:

| Layer | Component | Role |
|-------|-----------|------|
| **Data plane** | MinIO | Stores raw bytes (CSVs, models, pipeline artifacts) |
| **Control plane** | lakeFS | Adds branches, commits, merges, and lineage on top of that storage |
| **ML platform** | OpenShift AI | Workbenches, pipelines, model serving, model registry |

lakeFS exposes an S3-compatible API, so notebooks and pipelines use standard S3 paths like `s3://my-storage/train01/data/train.csv` while gaining versioning semantics.

### What the Demo Actually Does

1. **Deploys infrastructure** via Helm/Makefile: lakeFS, MinIO, Jupyter workbench, Data Science Pipeline Server, and optional Model Registry.
2. **Trains a fraud classifier** on transaction features (distance from last transaction, price ratio, chip/PIN/online flags → fraud label).
3. **Versions data and models in lakeFS**:
   - Create branch `train01` from `main`
   - Upload `train.csv`, `validate.csv`, `test.csv`
   - Train a Keras DNN, export ONNX
   - Upload model artifacts and **commit** for an immutable snapshot
   - Optionally merge to `main` to promote approved data/models
4. **Runs workflows through multiple interfaces today**:
   - **Notebooks** (`demo/notebooks/`) — primary path
   - **Elyra pipeline** — chains train + save notebooks
   - **Kubeflow pipeline** — get-data → train → upload
   - **REST inference notebook** — test served model
5. **Answers MLOps questions** such as: which dataset version trained this model, what changed between v1 and v2, can we reproduce or roll back?

### Current UX Gap

The story is powerful but **fragmented**: users move between Makefile/CLI, OpenShift AI dashboard, Jupyter notebooks, lakeFS UI, and pipeline runs. There is no single guided UI that tells the versioning narrative end-to-end.

---

## Five Suggestions to Convert This to a UI-Based Demo

### 1. Guided "Data Versioning Story" Web App (Streamlit or Gradio)

Deploy a lightweight Python app (Streamlit fits the existing stack) as a new Helm component with an OpenShift Route.

**UI flow:**

- **Step 1 — Environment check** (replaces notebook `0_quickstart-readiness-check`)
- **Step 2 — Branch & upload** — create `train01`, show a branch diagram (`main` → `train01`)
- **Step 3 — Train** — trigger training (call existing `train_tf_cpu_lakefs.py` or notebook logic), show live metrics and confusion matrix
- **Step 4 — Commit & compare** — commit artifacts, side-by-side metrics vs. a prior commit
- **Step 5 — Promote or revert** — merge to `main` or reset branch

**Why it works:** Minimal new backend code — wrap the lakeFS Python SDK and training scripts you already have. One URL, one narrative, no Jupyter required for presenters.

**Implementation notes:**

- Add a `demo/ui/` directory with Streamlit app and `requirements.txt`
- Extend `deploy/helm/fraud-detection` with Deployment, Service, and Route templates
- Inject lakeFS credentials from the existing `my-storage` secret

---

### 2. "Fraud Lab" React/FastAPI Portal with Embedded lakeFS Lineage

Add a small FastAPI service plus a React frontend that becomes the demo entry point.

**Key screens:**

- **Repository explorer** — tree view of `main` vs `train01` objects (data, scaler, ONNX model)
- **Experiment runner** — one button to run the KFP pipeline; poll run status via KFP API
- **Lineage panel** — commit SHA → dataset version → model metrics → inference endpoint
- **Live inference form** — enter transaction features, call the model-serving REST API (from notebook `5_rest_requests_single_model_lakefs`)

**Why it works:** Feels like a product demo rather than a tutorial. Separates concerns cleanly (FastAPI = lakeFS/KFP clients; React = visualization). Good for sales/engineering audiences who should not open notebooks.

**Implementation notes:**

- FastAPI backend wraps lakeFS SDK, boto3, and KFP REST client
- React frontend served as static assets or via a separate container
- Reuse existing pipeline YAML and training scripts as backend orchestration targets

---

### 3. Interactive "Branch Playground" Inside the Existing lakeFS UI Workflow

Instead of building everything from scratch, **enhance the demo around lakeFS's native UI** and add thin glue.

**Additions:**

- A **demo landing page** (static site or small app) with deep links into lakeFS: repo, branch, commit diff
- Pre-seed **two dataset variants** (e.g., `main` vs `train01` with label drift) so the lakeFS diff view is meaningful
- A **companion inference widget** (iframe or separate Route) that accepts a commit/branch selector and runs fraud scoring against the model at that ref

**Why it works:** Highlights lakeFS as the hero product. Lower build cost. The UI story becomes: "see the data change in lakeFS → retrain → compare → merge."

**Implementation notes:**

- Extend Helm post-install hooks to seed baseline and experiment branches
- Add a lightweight inference microservice that reads model path from a selected lakeFS ref
- Provide a single demo URL that links out to lakeFS UI at the right repo/branch context

---

### 4. One-Click Pipeline Dashboard (OpenShift AI–Native)

Keep execution on OpenShift AI but replace notebook steps with a **pipeline-centric UI**.

**Implementation:**

- Extend the Helm chart to deploy a simple dashboard that uses the **KFP REST API** and **OpenShift AI project APIs**
- Single page: **Run pipeline** → live DAG (get-data → train → upload) → links to lakeFS branch and Model Registry entry
- Add **run comparison**: overlay accuracy/precision/recall from two runs tied to different lakeFS commits
- Optional: "Simulate bad data update" button that creates a branch with corrupted labels and shows failed validation before merge

**Why it works:** Stays aligned with OpenShift AI Pipelines messaging. Reuses Pipeline 7 (`7_get_data_train_upload_lakefs.yaml`) with almost no ML code changes — mostly orchestration and visualization.

**Implementation notes:**

- Dashboard polls KFP run status from `demo/pipelines/7_get_data_train_upload_lakefs.yaml`
- Link completed runs to lakeFS commit metadata stored as object tags or run annotations
- Leverage existing auto-upload pipeline hook in the Helm chart

---

### 5. Conversational / Scenario-Driven Demo (Chainlit or Similar)

Build a chat-style UI that walks a presenter through scenarios:

- *"Train a model on the current main dataset"*
- *"Create an experiment branch with updated fraud labels"*
- *"Show me what changed between commits"*
- *"Which model is in production and what data trained it?"*
- *"Score this transaction as fraud or not"*

Each intent maps to backend actions (lakeFS SDK, pipeline trigger, inference call) with rich cards: branch graphs, metric tables, commit metadata.

**Why it works:** Excellent for live demos and conferences — the presenter asks natural questions instead of clicking through five UIs. Python-native and easy to wire to your existing scripts.

**Implementation notes:**

- Chainlit or similar framework with tool functions wrapping existing Python modules
- Predefined scenario scripts for repeatable conference demos
- Optional: this Route alongside the Jupyter workbench in the Helm chart

---

## Recommendation

For the fastest path with the highest demo impact, start with **#1 (Streamlit guided wizard)** or **#4 (pipeline dashboard)**:

| Option | Best when the audience cares most about… |
|--------|------------------------------------------|
| **#1 Streamlit wizard** | The **lakeFS versioning story** |
| **#4 Pipeline dashboard** | **OpenShift AI + MLOps pipelines** |

Both reuse existing scripts and Helm infrastructure with relatively small additions.

---

## Related Documentation

| Guide | Description |
|-------|-------------|
| [Main README](../README.md) | Project overview and deployment |
| [Notebooks Guide](NOTEBOOKS.md) | Jupyter notebook workflows |
| [Pipelines Guide](PIPELINES.md) | Elyra and KFP pipeline documentation |
| [Deployment Guide](../deploy/DEPLOY_README.md) | Helm and Makefile deployment |
