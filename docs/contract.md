# Environment contract

Skheri 0.1 uses two Helm charts. It deliberately does not add a second YAML DSL
on top of Helm values or promise to provision every cloud provider.

| Property | Development | Staging / production |
|---|---|---|
| Chart | `charts/workspace` | `charts/app` |
| Identity | kube context + namespace + release | kube context + namespace + release |
| Source | `/workspace/app` on `<release>-source` PVC | built image |
| Lifetime | until explicitly retired | until replaced or uninstalled |
| Update | edit files; framework HMR | new image digest; Helm rollout |
| Preview | port-forward or authenticated ingress | readiness-gated Service / ingress |
| Credentials | existing `secretName` | existing `secretName` |

Use one dedicated namespace per workspace. Give each agent task a separate workspace
unless collaborators intentionally share one editor/agent session. Skheri does not
serialize concurrent writes to a shared checkout. A shared namespace or PVC is not
an authorization system.

## Values

The checked-in `values.yaml` files and JSON schemas are the authoritative field
definitions. Keep environment differences in small overlay files. Credentials
are Kubernetes Secrets managed outside Git; the chart accepts only the Secret name.

`persistence.storageClass: null` uses the cluster default. An empty string disables
dynamic provisioning and requires a compatible pre-provisioned volume. The volume
uses `ReadWriteOnce`; the workspace uses one replica and `Recreate` updates.

The workspace's idle process is immediately ready for `kubectl exec`. Readiness of
that pod does not imply that your development server has finished installing or
starting. Confirm its logs and preview response before sharing the URL.

Use `image.digest` for reproducible releases. A versioned `image.tag` is accepted for
development/testing, but a registry can move a tag. `latest` is rejected. The app
chart requires an HTTP readiness endpoint and a non-root-compatible image.

## Report to the caller

Return context, namespace, release, source PVC, preview URL or port-forward command,
Git revision (when available), image digest (for releases), and validation report.
Do not report “deployed” on the basis of a successful template render.

A live preview is mutable. Freeze the reviewed source as a commit or explicit
snapshot before recording approval. Store the reviewed revision with the image
digest and evidence. Environment variables, live databases and external services
are not captured by a Git commit.

## Compatibility

The charts use stable `apps/v1`, `networking.k8s.io/v1` and `v1` resources. They target
existing Kubernetes clusters, including k3s. CI validates on kind; this is not a
claim of certification on every managed Kubernetes distribution.
