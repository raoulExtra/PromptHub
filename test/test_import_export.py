"""Tests for the PromptHub import/export utility."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "extensions" / "import-export" / "import-export.py"
spec = importlib.util.spec_from_file_location("prompthub_import_export", MODULE_PATH)
import_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(import_export)
EXTENSION_PATH = ROOT / "extensions" / "extension.py"
spec = importlib.util.spec_from_file_location("prompthub_extension", EXTENSION_PATH)
extension = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extension)


def test_init_db_then_export(tmp_path, monkeypatch):
    database = tmp_path / "prompthub.db"
    monkeypatch.setattr(import_export, "DB_PATH", database)
    monkeypatch.setattr(import_export, "BASE_DIR", tmp_path)
    monkeypatch.setattr(extension, "DB_PATH", database)

    inserted = extension.init_db(
        [
            {
                "title": "Critical agent",
                "body": "Follow the safety policy.",
                "type": "System prompt",
                "favorite": "Favorite",
                "tags": ["agent", "criticality:critical", "data:demo"],
            },
            {
                "title": "Low priority",
                "body": "Add optional context.",
                "type": "User prompt",
                "tags": ["criticality:low"],
            },
        ]
    )

    assert inserted == 2
    registered_tags = [row["name"] for row in extension.read_table("tags_registered")]
    assert registered_tags == [
        "criticality:critical", "criticality:high", "criticality:medium",
        "criticality:low", "data:demo", "governance:system_instruction",
    ]
    export_dir = tmp_path / "protected" / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "old-prompt.md").write_text("stale", encoding="utf-8")
    (export_dir / "safety-rules.md").write_text("preserve", encoding="utf-8")
    exported = import_export.export_prompts()
    assert exported == 2

    files = sorted((tmp_path / "protected" / "export").glob("*.md"))
    assert (export_dir / "safety-rules.md").exists()
    assert not (export_dir / "old-prompt.md").exists()
    assert [path.name for path in files] == [
        "001-critical-agent.md",
        "002-low-priority.md",
        "safety-rules.md",
    ]
    critical_prompt = files[0].read_text(encoding="utf-8")
    critical_yaml = (export_dir / "001-critical-agent.yaml").read_text(encoding="utf-8")
    assert "title: Critical agent" in critical_prompt
    assert "id: 1" in critical_yaml
    assert "criticality: critical" in critical_yaml
    assert "updated_at:" in critical_yaml
    assert 'tags: ["agent", "criticality:critical", "data:demo"]' in critical_yaml
    assert "Follow the safety policy." in critical_yaml
    assert "tags: agent, criticality:critical" in critical_prompt
    assert "Follow the safety policy." in critical_prompt
    assert extension.generate_system_prompt("high") == "Follow the safety policy."

    for path in files:
        path.unlink()
    assert import_export.export_prompts(demo=True) == 1
    demo_files = list((tmp_path / "protected" / "export").glob("*.md"))
    assert [path.name for path in demo_files] == ["001-critical-agent.md"]
