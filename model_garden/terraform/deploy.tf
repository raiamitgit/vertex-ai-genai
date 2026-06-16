terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0.0"
    }
  }

  # Production Best Practice: Use a remote Cloud Storage (GCS) backend for state persistence
  # backend "gcs" {
  #   bucket = "YOUR_TERRAFORM_STATE_BUCKET"
  #   prefix = "terraform/state/model_garden"
  # }
}

variable "project_id" {
  type        = string
  description = "The Google Cloud Project ID"
  default     = "YOUR_PROJECT_ID"
}

variable "region" {
  type        = string
  description = "The Google Cloud Region (e.g., us-central1)"
  default     = "us-central1"
}

variable "publisher_model_name" {
  type        = string
  description = "The Model Garden Publisher Model Identifier"
  default     = "publishers/google/models/YOUR_MODEL_ID"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Deploy Model Garden Model to Vertex AI Dedicated Endpoint
resource "google_vertex_ai_endpoint_with_model_garden_deployment" "model_garden_deployment" {
  project              = var.project_id
  location             = var.region
  publisher_model_name = var.publisher_model_name
  
  model_config {
    accept_eula = true
  }
}

output "endpoint_id" {
  value       = google_vertex_ai_endpoint_with_model_garden_deployment.model_garden_deployment.id
  description = "The ID of the created Vertex AI Endpoint."
}
