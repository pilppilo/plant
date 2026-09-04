import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import plant as plant_cli


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "plant"


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

    def source_root(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "plant"
        (root / "schema").mkdir(parents=True)
        (root / "templates").mkdir()
        (root / "PROTOCOL.md").write_text("Protocol v1\n")
        (root / "schema" / "metadata.schema.json").write_text("{}\n")
        (root / "templates" / "index.md").write_text("# Planning index\n\nPlant source revision: unpinned\n")
        return temporary, root

    def test_valid_plan_passes(self):
        temporary, root = self.plans_dir()
        with temporary:
            result = self.check(root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_init_copies_a_pinned_snapshot(self):
        temporary, source = self.source_root()
        with temporary:
            plans = source.parent / "project" / "plans"
            lock = plant_cli.init_plans(plans, source)
            self.assertEqual((plans / "PROTOCOL.md").read_text(), "Protocol v1\n")
            self.assertIn(lock["source_revision"], (plans / "README.md").read_text())
            self.assertEqual(json.loads((plans / ".plant-lock.json").read_text()), lock)

    def test_update_refuses_modified_managed_files(self):
        temporary, source = self.source_root()
        with temporary:
            plans = source.parent / "project" / "plans"
            plant_cli.init_plans(plans, source)
            (plans / "PROTOCOL.md").write_text("Local change\n")
            (source / "PROTOCOL.md").write_text("Protocol v2\n")
            with self.assertRaisesRegex(plant_cli.PlantError, "locally modified managed files: PROTOCOL.md"):
                plant_cli.update_plans(plans, source)
            self.assertEqual((plans / "PROTOCOL.md").read_text(), "Local change\n")

    def test_update_requires_the_index_revision_marker(self):
        temporary, source = self.source_root()
        with temporary:
            plans = source.parent / "project" / "plans"
            plant_cli.init_plans(plans, source)
            (plans / "README.md").write_text("# Planning index\n")
            with self.assertRaisesRegex(plant_cli.PlantError, "missing its Plant source revision line"):
                plant_cli.update_plans(plans, source)

    def test_update_refreshes_untouched_snapshot(self):
        temporary, source = self.source_root()
        with temporary:
            plans = source.parent / "project" / "plans"
            plant_cli.init_plans(plans, source)
            (source / "PROTOCOL.md").write_text("Protocol v2\n")
            plant_cli.update_plans(plans, source)
            self.assertEqual((plans / "PROTOCOL.md").read_text(), "Protocol v2\n")

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
            (root / "README.md").write_text(index() + "\n## ID reservations\n\n| Type | ID | Owner | Purpose | Reserved at | Status |\n| --- | --- | --- | --- | --- | --- |\n| architecture | ARCH-0001 | test | Duplicate | 2026-09-04 | active |\n")
            result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be removed", result.stdout)

    def test_retired_reservation_cannot_be_reused(self):
        temporary, root = self.plans_dir()
        with temporary:
            (root / "README.md").write_text(index() + "\n## ID reservations\n\n| Type | ID | Owner | Purpose | Reserved at | Status |\n| --- | --- | --- | --- | --- | --- |\n| architecture | ARCH-0001 | test | Abandoned | 2026-09-04 | retired |\n")
            result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("retired ID reservation ARCH-0001 cannot be reused", result.stdout)

    def test_decision_status_must_match_index(self):
        temporary, root = self.plans_dir()
        with temporary:
            (root / "decisions").mkdir()
            (root / "decisions" / "adr-0001-test.md").write_text(document("ADR-0001", "decision", "accepted"))
            (root / "README.md").write_text(index() + "\n## Decisions\n\n| ID | Status | Decision | Supersedes |\n| --- | --- | --- | --- |\n| ADR-0001 | proposed | Test | None |\n")
            result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("index status proposed does not match frontmatter accepted", result.stdout)

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

    def test_shipped_example_passes(self):
        result = self.check(ROOT / "example" / "plans")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_indexed_document_must_exist(self):
        temporary, root = self.plans_dir()
        with temporary:
            (root / "README.md").write_text(index() + "\n## Active experiments\n\n| ID | Status | Question | Informs |\n| --- | --- | --- | --- |\n| EXP-0001 | planned | Missing | None |\n")
            result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("indexed document is missing: EXP-0001", result.stdout)

    def test_duplicate_index_row_fails(self):
        temporary, root = self.plans_dir()
        with temporary:
            (root / "README.md").write_text(index() + "\n## Duplicate\n\n| ID | Status | Purpose |\n| --- | --- | --- |\n| ARCH-0001 | accepted | Duplicate |\n")
            result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate index row", result.stdout)

    def test_duplicate_document_id_fails(self):
        temporary, root = self.plans_dir()
        with temporary:
            (root / "architecture" / "arch-0001-copy.md").write_text(document("ARCH-0001", "architecture", "accepted"))
            result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate id", result.stdout)

    def test_dependency_cycle_fails(self):
        temporary, root = self.plans_dir()
        with temporary:
            (root / "architecture" / "arch-0001-test.md").write_text(document("ARCH-0001", "architecture", "accepted", "[PHASE-0001]"))
            result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("dependency cycle", result.stdout)

    def test_malformed_metadata_is_structured_json_error(self):
        base = document("PHASE-0001", "phase", "ready", "[ARCH-0001]")
        cases = (
            (base.replace("type: phase", "type: [phase]"), "type must be a non-empty scalar"),
            (base.replace("title: Test", "title: [Test]"), "title must be a non-empty scalar"),
            (base.replace("created: 2026-09-04", "created: yesterday"), "created must be an ISO 8601 date"),
            (base.replace("owners: [test]", "extra: value\nowners: [test]"), "unknown frontmatter fields"),
            (base.replace("title: Test", "title: Test\ntitle: Again"), "duplicate frontmatter field"),
        )
        for contents, expected in cases:
            temporary, root = self.plans_dir()
            with temporary:
                phase = root / "phases" / "phase-0001-test.md"
                phase.write_text(contents)
                result = self.check(root)
            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1, payload)
            self.assertFalse(payload["ok"])
            self.assertIn(expected, result.stdout)
            self.assertNotIn("Traceback", result.stderr)

    def test_current_focus_roles_are_enforced(self):
        temporary, root = self.plans_dir()
        with temporary:
            readme = root / "README.md"
            readme.write_text(index().replace("- **Workstream:** None.", "- **Workstream:** ARCH-0001"))
            result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Workstream must reference an active WORK", result.stdout)

    def test_current_focus_now_must_be_actionable(self):
        temporary, root = self.plans_dir()
        with temporary:
            phase = root / "phases" / "phase-0001-test.md"
            phase.write_text(document("PHASE-0001", "phase", "proposed", "[ARCH-0001]"))
            (root / "README.md").write_text(index("proposed"))
            result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Current focus Now must reference", result.stdout)

    def test_schema_and_checker_mappings_match(self):
        schema = json.loads((ROOT / "schema" / "metadata.schema.json").read_text())
        prefixes = {
            rule["properties"]["type"]["const"]: rule["properties"]["id"]["pattern"].split("-")[0][1:]
            for rule in schema["allOf"][0]["oneOf"]
        }
        statuses = {}
        for rule in schema["allOf"][1:]:
            kind_rule = rule["if"]["properties"]["type"]
            kinds = kind_rule.get("enum", [kind_rule.get("const")])
            for kind in kinds:
                statuses[kind] = set(rule["then"]["properties"]["status"]["enum"])
        self.assertEqual(prefixes, plant_cli.PREFIXES)
        self.assertEqual(statuses, plant_cli.STATUSES)


if __name__ == "__main__":
    unittest.main()
