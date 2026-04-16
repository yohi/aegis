# Setup Guide

## Prerequisites

- Docker Desktop (for DevContainer)
- GCP project with Model Armor API enabled
- Google Cloud CLI authenticated (`gcloud auth application-default login`)

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `LLM_REVIEW_SYNC_NOTEBOOK_ID` | Target NotebookLM ID | Yes |
| `LLM_REVIEW_SYNC_DRIVE_FOLDER_ID` | Upload destination folder ID | Yes |
| `LLM_REVIEW_SECURITY_GCP_PROJECT_ID` | GCP project ID for Model Armor | Yes |
| `LLM_REVIEW_SECURITY_MODEL_ARMOR_LOCATION` | Model Armor region | No (default: us-central1) |
| `LLM_REVIEW_SECURITY_BLOCK_ON_HIGH_SEVERITY` | Block on high severity findings | No (default: true) |
| `LLM_REVIEW_RETRY_MAX_ATTEMPTS` | Max retry attempts | No (default: 3) |