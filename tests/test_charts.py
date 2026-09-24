"""Validate user-facing configuration contracts without accessing a cluster."""
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def render(chart, *args):
    return subprocess.run(
        ["helm", "template", "test", str(ROOT / "charts" / chart), *args],
        capture_output=True, text=True,
    )


class Charts(unittest.TestCase):
    def test_workspace_requires_no_credentials_or_ingress(self):
        result = render("workspace")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("helm.sh/resource-policy: keep", result.stdout)
        self.assertNotIn("kind: Ingress", result.stdout)
        self.assertIn("automountServiceAccountToken: false", result.stdout)

    def test_preview_requires_both_hostname_and_certificate(self):
        args = ["--set", "ingress.enabled=true"]
        self.assertNotEqual(render("workspace", *args).returncode, 0)
        args += ["--set", "ingress.host=preview.example.com"]
        self.assertNotEqual(render("workspace", *args).returncode, 0)
        args += ["--set", "ingress.tlsSecret=preview-tls"]
        self.assertEqual(render("workspace", *args).returncode, 0)

    def test_invalid_values_do_not_silently_render(self):
        for option in ("port=0", "port=65536", "persistence.size=-1Gi", "ingres.enabled=true"):
            with self.subTest(option=option):
                self.assertNotEqual(render("workspace", "--set", option).returncode, 0)

    def test_deployment_requires_versioned_image(self):
        self.assertNotEqual(render("app").returncode, 0)
        args = ["--set", "image.repository=example/app"]
        self.assertNotEqual(render("app", *args, "--set", "image.tag=latest").returncode, 0)
        digest = "sha256:" + "a" * 64
        result = render("app", *args, "--set", f"image.digest={digest}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("example/app@" + digest, result.stdout)
        self.assertNotIn("PersistentVolumeClaim", result.stdout)
        self.assertNotEqual(render("app", *args, "--set", "image.digest=sha256:nope").returncode, 0)


if __name__ == "__main__":
    unittest.main()
