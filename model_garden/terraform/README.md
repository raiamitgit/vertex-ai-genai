# Vertex AI Model Garden Deployment & Teardown Guide

This directory provides enterprise-ready configurations for deploying Model Garden foundation models via Terraform, paired with stateful teardown automation.

---

## 1. Service Agent Pre-Provisioning

Ensure the AI Platform Service Agent (P4SA) exists in your project so automated IAM policy bindings succeed:

```bash
gcloud beta services identity create --service=aiplatform.googleapis.com --project="YOUR_PROJECT_ID"
```

*(This is handled automatically when calling `./deploy.sh`).*

---

## 2. Declarative Deployment (`deploy.sh`)

Deploy using parameterized environment variables or `terraform.tfvars`:

```bash
export PROJECT_ID="YOUR_PROJECT_ID"
export REGION="us-central1"

./deploy.sh
```

---

## 3. Declarative Teardown (`undeploy.sh`)

To spin down dedicated compute nodes, undeploy models, and delete the endpoint via `terraform destroy`:

```bash
export PROJECT_ID="YOUR_PROJECT_ID"

./undeploy.sh
```
