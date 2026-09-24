---
name: skheri
description: Create persistent Kubernetes development workspaces, preview uncommitted changes, and deploy built applications with Skheri Helm charts.
---

# Skheri

Read [README.md](README.md) and [the environment contract](docs/contract.md).
Use standard Helm and kubectl commands; Skheri has no daemon or custom CLI.

1. Identify the user's target kube context, namespace, release and operation.
   Use `--kube-context` with Helm and `--context` with kubectl. Do not change the
   global context. Never infer that an existing production cluster is a test cluster.
2. Render the chart and inspect the diff before applying. Reuse the same workspace
   release for follow-up turns. Source belongs to its PVC, not an agent's temporary job.
3. Keep Git credentials, provider logins and kubeconfigs out of images, chart values,
   source archives and reports. Use existing Secrets and scoped credentials.
4. For development, edit `/workspace/app` and keep the project's dev server running.
   A commit is not required to preview. Preserve the framework's WebSocket connection.
5. For review, associate the observed preview with a source snapshot or commit and
   Argos evidence. A live preview can change; do not present it as an immutable approval.
6. For staging/production, build once, record the image digest, and deploy that digest
   using `charts/app`. Do not mount the live development PVC in a production release.
7. Report context, namespace, release, PVC, preview route and validation outcome.
   Never uninstall/delete a PVC or namespace merely because one agent turn completed.

Workspace containers run trusted code under one team's administration. They are
not a hardened sandbox for untrusted tenants. Public preview routes require TLS
and an external authentication layer. The charts do not provision cloud machines,
install an ingress controller, issue certificates, or configure agent subscriptions.
