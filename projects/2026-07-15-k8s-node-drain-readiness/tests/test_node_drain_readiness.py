import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from node_drain_readiness import review_snapshot


PROJECT_DIR = Path(__file__).resolve().parents[1]


class NodeDrainReadinessTests(unittest.TestCase):
    def load_sample(self, name):
        return json.loads((PROJECT_DIR / "samples" / name).read_text())

    def test_ready_snapshot_has_no_blockers(self):
        self.assertEqual(review_snapshot(self.load_sample("ready_node.json")), [])

    def test_blocked_snapshot_finds_operational_risks(self):
        blockers = review_snapshot(self.load_sample("blocked_node.json"))
        self.assertEqual(len(blockers), 7)
        self.assertEqual(
            {item.code for item in blockers},
            {"unmanaged-pod", "local-data-risk", "single-replica", "no-ready-replacement", "pdb-blocks-eviction", "eviction-disabled"},
        )

    def test_duplicate_pods_are_rejected(self):
        pod = {"namespace": "default", "name": "api", "owner_kind": "DaemonSet"}
        with self.assertRaisesRegex(ValueError, "duplicate pod"):
            review_snapshot({"node": "worker-1", "pods": [pod, pod]})

    def test_cli_distinguishes_ready_blocked_and_invalid(self):
        ready = subprocess.run(
            [sys.executable, str(PROJECT_DIR / "node_drain_readiness.py"), str(PROJECT_DIR / "samples/ready_node.json")],
            capture_output=True, text=True, check=False,
        )
        blocked = subprocess.run(
            [sys.executable, str(PROJECT_DIR / "node_drain_readiness.py"), str(PROJECT_DIR / "samples/blocked_node.json")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual((ready.returncode, blocked.returncode), (0, 1))
        self.assertIn("READY:", ready.stdout)
        self.assertIn("STOP:", blocked.stdout)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as malformed:
            malformed.write("not-json")
            malformed.flush()
            invalid = subprocess.run(
                [sys.executable, str(PROJECT_DIR / "node_drain_readiness.py"), malformed.name],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("ERROR:", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
