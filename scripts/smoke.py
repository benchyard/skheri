#!/usr/bin/env python3
"""Exercise only an ephemeral kind cluster created by this process."""
import atexit
import json
import os
from pathlib import Path
import socket
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    name = "skheri-check-" + uuid.uuid4().hex[:8]
    with tempfile.TemporaryDirectory(prefix="skheri-check-") as temp:
        kubeconfig = str(Path(temp) / "kubeconfig")
        env = {**os.environ, "KUBECONFIG": kubeconfig}
        cleanup = lambda: subprocess.run(["kind", "delete", "cluster", "--name", name], check=False)
        atexit.register(cleanup)
        forwards = []
        try:
            for image in ("node:22-bookworm-slim", "nginxinc/nginx-unprivileged:1.28-alpine"):
                run("docker", "pull", image)
            run("kind", "create", "cluster", "--name", name, "--kubeconfig", kubeconfig, "--wait", "180s")
            # Docker's containerd store may retain a multi-platform index with
            # only the host's layers. Export that platform explicitly so kind
            # does not attempt to import absent architectures (Docker 28+).
            platform = subprocess.check_output(
                ["docker", "image", "inspect", "node:22-bookworm-slim", "--format", "{{.Os}}/{{.Architecture}}"],
                text=True,
            ).strip()
            images = str(Path(temp) / "images.tar")
            run("docker", "image", "save", "--platform", platform, "-o", images,
                "node:22-bookworm-slim", "nginxinc/nginx-unprivileged:1.28-alpine")
            run("kind", "load", "image-archive", images, "--name", name)

            def kubectl(*args, **kwargs):
                return run("kubectl", "--context", "kind-" + name, "-n", "skheri-test", *args, env=env, **kwargs)

            def helm(*args):
                return run("helm", *args, "--kube-context", "kind-" + name, "-n", "skheri-test", env=env)

            def forward(service, target):
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
                proc = subprocess.Popen(
                    ["kubectl", "--context", "kind-" + name, "-n", "skheri-test", "port-forward",
                     "svc/" + service, f"{port}:{target}"], env=env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                forwards.append(proc)
                return f"http://127.0.0.1:{port}"

            def expect(url, marker):
                deadline = time.monotonic() + 180
                while time.monotonic() < deadline:
                    try:
                        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=3) as response:
                            if marker in response.read().decode():
                                return
                    except (OSError, TimeoutError):
                        pass
                    time.sleep(2)
                kubectl("logs", "deploy/demo", "--tail=40")
                raise AssertionError(f"preview did not contain {marker!r}")

            helm("upgrade", "--install", "demo", str(ROOT / "charts/workspace"), "--create-namespace",
                 "-f", str(ROOT / "examples/environments/dev.yaml"), "--wait", "--timeout", "5m")
            archive = Path(temp) / "example.tar"
            with tarfile.open(archive, "w") as tar:
                for filename in ("package.json", "package-lock.json", "index.html"):
                    tar.add(ROOT / "examples/vite" / filename, arcname=filename)
            with archive.open("rb") as source:
                kubectl("exec", "-i", "deploy/demo", "--", "tar", "-xf", "-", "-C", "/workspace/app", stdin=source)
            # Wait inside the pod before opening port-forward: kubectl can exit
            # on an initial connection refusal while npm is still installing.
            kubectl("exec", "deploy/demo", "--", "node", "-e",
                    "const end=Date.now()+180000;async function wait(){try{const r=await fetch('http://127.0.0.1:5173');if(r.ok)return;}catch{}if(Date.now()>end)process.exit(1);setTimeout(wait,1000)}wait()")
            url = forward("demo", 5173)
            expect(url, "Preview before commit.")
            # Vite's injected client proves this is the dev server, not a stale image.
            expect(url, "/@vite/client")
            kubectl("exec", "deploy/demo", "--", "sed", "-i",
                    "s/Preview before commit[.]/Uncommitted acceptance edit./g", "/workspace/app/index.html")
            expect(url, "Uncommitted acceptance edit.")
            expect(url, "</title>")  # The example edit must preserve surrounding HTML.
            kubectl("delete", "pod", "-l", "app.kubernetes.io/instance=demo", "--wait=true")
            kubectl("rollout", "status", "deploy/demo", "--timeout=180s")
            kubectl("exec", "deploy/demo", "--", "node", "-e",
                    "const end=Date.now()+180000;async function wait(){try{const r=await fetch('http://127.0.0.1:5173');if(r.ok)return;}catch{}if(Date.now()>end)process.exit(1);setTimeout(wait,1000)}wait()")
            expect(forward("demo", 5173), "Uncommitted acceptance edit.")

            helm("upgrade", "--install", "app", str(ROOT / "charts/app"),
                 "--set", "image.repository=nginxinc/nginx-unprivileged", "--set", "image.tag=1.28-alpine",
                 "--wait", "--timeout", "5m")
            expect(forward("app", 8080), "Welcome to nginx")
            helm("uninstall", "demo")
            pvc = kubectl("get", "pvc", "demo-source", "-o", "json", capture_output=True, text=True)
            assert json.loads(pvc.stdout)["status"]["phase"] == "Bound"
            print("PASS: uncommitted preview, Vite client, pod replacement, app rollout, retained PVC")
        except Exception:
            subprocess.run(["kubectl", "--context", "kind-" + name, "-n", "skheri-test",
                            "get", "events", "--sort-by=.lastTimestamp"], env=env, check=False)
            raise
        finally:
            for proc in forwards:
                proc.terminate()
                proc.wait(timeout=10)
            cleanup()
            atexit.unregister(cleanup)


if __name__ == "__main__":
    main()
