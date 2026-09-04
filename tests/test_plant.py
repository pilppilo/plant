import json
import subprocess
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "plant"


def document(identifier, kind, status, depends_on="[]"):
    return "\n".join((
        "---", f"id: {identifier}", "title: Test", f"type: {kind}", f"status: {status}",
        "owners: [test]", "created: 2026-09-04", "updated: 2026-09-04",
        f"depends_on: {depends_on}", "supersedes: []", "related: []", "---", "", "# Test", "",
    ))


def index(status="ready"):
    return "\n".join((
        "# Planning index", "", "## Current focus", "", "- **Now:** PHASE-0001",
        "- **Read:** ARCH-0001", "- **Workstream:** None.", "- **Next:** None.", "- **Blocked:** None.", "",
        "## Governing direction", "", "| ID | Document | Status | Purpose |", "| --- | --- | --- | --- |",
        "| ARCH-0001 | architecture/arch-0001-test.md | accepted | Test |", "", "## Delivery order", "",
        "| Order | ID | Status | Depends on | Outcome |", "| --- | --- | --- | --- | --- |",
        f"| 1 | PHASE-0001 | {status} | ARCH-0001 | Test |", "",
    ))


class PlantCheckTests(unittest.TestCase):
    def plans_dir(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "plans"
        (root / "architecture").mkdir(parents=True)
        (root / "phases").mkdir()
        (root / "architecture" / "arch-0001-test.md").write_text(document("ARCH-0001", "architecture", "accepted"))
        (root / "phases" / "phase-0001-test.md").write_text(document("PHASE-0001", "phase", "ready", "[ARCH-0001]"))
        (root / "README.md").write_text(index())
        return temporary, root

    def check(self, root):
        return subprocess.run([str(CLI), "--json", "check", str(root)], capture_output=True, text=True, check=False)

    def test_valid_plan_passes(self):
        temporary, root = self.plans_dir()
        with temporary:
            result = self.check(root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_missing_reference_fails(self):
        temporary, root = self.plans_dir()
        with temporary:
            (root / "phases" / "phase-0001-test.md").write_text(document("PHASE-0001", "phase", "ready", "[ARCH-0002]"))
            result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("references missing document", result.stdout)

    def test_reservation_cannot_collide_with_document(self):
        temporary, root = self.plans_dir()
        with temporary:
            (root / "README.md").write_text(index() + "\n## ID reservations\n\n| Type | ID | Owner | Purpose | Reserved at |\n| --- | --- | --- | --- | --- |\n| architecture | ARCH-0001 | test | Duplicate | 2026-09-04 |\n")
            result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be removed", result.stdout)

    def test_ready_phase_requires_accepted_governing_document(self):
        temporary, root = self.plans_dir()
        with temporary:
            architecture = root / "architecture" / "arch-0001-test.md"
            architecture.write_text(document("ARCH-0001", "architecture", "proposed"))
            readme = root / "README.md"
            readme.write_text(index().replace("| ARCH-0001 | architecture/arch-0001-test.md | accepted |", "| ARCH-0001 | architecture/arch-0001-test.md | proposed |"))
            result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("ARCH-0001 must be accepted", result.stdout)


if __name__ == "__main__":
    unittest.main()
