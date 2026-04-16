FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends \
    jq \
    && rm -rf /var/lib/apt/lists/*

# RUN npm install -g @anthropic/gwscli # Package name needs verification

USER vscode
WORKDIR /workspaces/llm-review-system