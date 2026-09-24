# Operations

## Cloud preview

For access without an open laptop, run the workspace on an always-on cloud host or
cluster. Install your chosen ingress controller and authentication gateway first.
Provide an existing TLS Secret and DNS record:

```yaml
ingress:
  enabled: true
  className: traefik
  host: task-42.preview.example.com
  tlsSecret: preview-tls
  annotations: {} # configure your controller's authentication middleware here
```

The chart routes both HTTP and WebSocket requests to the same development port.
Configure the ingress controller and auth gateway to support WebSockets, and set
your framework's allowed hosts to the exact preview hostname. Do not disable host
validation globally. Restrict previews to the intended collaborators: TLS encrypts
traffic but does not authenticate viewers. The chart supplies no authentication.

The optional ingress requires `host` and `tlsSecret`; it is disabled by default.
Your cluster's DNS, certificate issuance, ingress controller and access policies
remain under your control.

## Agent connection

A coding agent with an authorized Kubernetes client can use `kubectl exec` to edit
and run code in the workspace. Alternatively supply a workspace image containing
the CLI you use and authenticate it with its supported flow. This release does not
install Cursor/Codex, forward their subscriptions, or implement mobile remote control.
Review any agent provider's headless and remote-execution terms and capabilities.

Never give the workspace pod a cluster-admin token. It does not mount a Kubernetes
service-account token. Users of the Kubernetes API need separately scoped access.
Use a separate namespace per task, quotas and network policies appropriate to your
cluster. Default charts do not restrict egress. For hostile code, use a stronger
isolation runtime or dedicated VM; namespaces and ordinary containers are insufficient.

## Persistence and cleanup

The PVC survives pod replacement and `helm uninstall`. The running process does
not survive replacement: your startup command must restart the development server.
Back up important source, uncommitted work and data independently of the cluster.

```bash
helm uninstall demo --kube-context "$SKHERI_CONTEXT" -n skheri-demo
# After exporting the source and confirming the workspace is no longer needed:
kubectl --context "$SKHERI_CONTEXT" -n skheri-demo delete pvc demo-source
kubectl --context "$SKHERI_CONTEXT" delete namespace skheri-demo
```

Deleting a namespace also deletes retained PVCs in it. Never use namespace deletion
as routine end-of-turn cleanup. PVC retention is not a backup policy. PVC size/class
changes and storage expansion depend on the storage provider; do not assume Helm
can shrink or move an existing volume.

## Releases and rollback

Build once, scan and test the artifact, then record its digest. Use separate release
namespaces and values files for staging and production. Keep databases and their
backups outside this stateless app chart. `helm --atomic --wait` handles a failed
Kubernetes rollout; it does not roll back schema migrations or external side effects.

```bash
helm history demo-app --kube-context "$SKHERI_CONTEXT" -n demo-staging
helm rollback demo-app 1 --kube-context "$SKHERI_CONTEXT" -n demo-staging --wait
```

Choose a known successful revision from `helm history`, not always revision 1.
