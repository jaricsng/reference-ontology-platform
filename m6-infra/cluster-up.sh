#!/usr/bin/env bash
# Create the k3d cluster and install Argo CD.
set -euo pipefail

CLUSTER="${CLUSTER:-hospital}"

echo "==> Creating k3d cluster '$CLUSTER'"
k3d cluster create "$CLUSTER" --agents 1 --wait

echo "==> Installing Argo CD"
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
echo "==> Waiting for Argo CD server"
kubectl -n argocd rollout status deploy/argocd-server --timeout=300s
echo "Done. Argo CD admin password:"
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo
