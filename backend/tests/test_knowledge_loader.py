"""
Knowledge Loader Tests · Phase 6B
"""
from pathlib import Path
import pytest

from app.knowledge.chunker import chunk_document
from app.knowledge.loader import load_knowledge_base
from app.knowledge.schemas import KnowledgeDocument


@pytest.fixture
def knowledge_dir(tmp_path):
    """Create a tmp knowledge/ directory with sample Markdown files."""
    d = tmp_path / "knowledge"
    d.mkdir()
    (d / "anomaly_detection.md").write_text(
        "<!--\n"
        "title: Anomaly Detection\n"
        "purpose: Detect abnormal readings.\n"
        "source: BuildHealth Internal Engineering Notes\n"
        "-->\n"
        "\n"
        "# Anomaly Detection\n"
        "\n"
        "## Threshold Method\n"
        "\n"
        "Triggers when a single reading exceeds an absolute bound.\n"
        "\n"
        "## Rate of Change Method\n"
        "\n"
        "Triggers on relative change between consecutive readings.\n",
        encoding="utf-8",
    )
    (d / "health_assessment.md").write_text(
        "# BHI Overview\n"
        "\n"
        "BHI is a 0-100 number.\n"
        "\n"
        "## Dimensions\n"
        "\n"
        "Five sub-scores, weighted.\n",
        encoding="utf-8",
    )
    (d / "no_frontmatter_no_h1.md").write_text(
        "Just plain text without any headings.\n",
        encoding="utf-8",
    )
    (d / "ignore_me.txt").write_text("not a markdown file", encoding="utf-8")
    (d / ".hidden.md").write_text("hidden", encoding="utf-8")
    return d


def test_loads_all_md_files(knowledge_dir):
    docs = load_knowledge_base(knowledge_dir)
    # 3 .md files (anomaly_detection, health_assessment, no_frontmatter_no_h1)
    # .txt and .hidden.md are skipped
    assert len(docs) == 3
    assert all(isinstance(d, KnowledgeDocument) for d in docs)


def test_skips_non_md_files(knowledge_dir):
    docs = load_knowledge_base(knowledge_dir)
    doc_ids = [d.document_id for d in docs]
    assert "ignore_me.txt" not in doc_ids
    assert ".hidden.md" not in doc_ids


def test_parses_frontmatter_and_title(knowledge_dir):
    docs = load_knowledge_base(knowledge_dir)
    by_id = {d.document_id: d for d in docs}
    a = by_id["anomaly_detection.md"]
    assert a.title == "Anomaly Detection"
    # frontmatter source 字段覆盖默认
    assert a.source == "BuildHealth Internal Engineering Notes"


def test_parses_sections_from_h2(knowledge_dir):
    docs = load_knowledge_base(knowledge_dir)
    by_id = {d.document_id: d for d in docs}
    a = by_id["anomaly_detection.md"]
    # full_text 应含 ## headings
    assert "## Threshold Method" in a.full_text
    assert "## Rate of Change Method" in a.full_text


def test_fallback_title_for_no_h1(knowledge_dir):
    docs = load_knowledge_base(knowledge_dir)
    by_id = {d.document_id: d for d in docs}
    bad = by_id["no_frontmatter_no_h1.md"]
    # 无 # heading → 用 filename 转 title
    assert bad.title == "No Frontmatter No H1"
    assert bad.full_text.strip() == "Just plain text without any headings."
    # 无 ## section → chunker 产出单个 "Full Document" chunk
    chunks = chunk_document(bad)
    assert len(chunks) == 1
    assert chunks[0].section == "Full Document"


def test_empty_directory_returns_empty_list(tmp_path):
    d = tmp_path / "empty_knowledge"
    d.mkdir()
    assert load_knowledge_base(d) == []


def test_nonexistent_directory_returns_empty_list(tmp_path):
    d = tmp_path / "nonexistent_knowledge"
    # 不创建
    assert load_knowledge_base(d) == []


# ============ Phase 6B · skip list ============
def test_readme_is_not_indexed(tmp_path):
    """knowledge/README.md 是目录导航, 不进入检索索引."""
    d = tmp_path / "kb"
    d.mkdir()
    (d / "README.md").write_text(
        "<!--\ntitle: KB\ndocument map\n-->\n\n# KB\n\n## Document Map\n\n"
        "| File | Topic |\n|---|---|\n| a.md | thing |\n",
        encoding="utf-8",
    )
    (d / "a.md").write_text(
        "# A\n\n## Real Content\n\nActual engineering notes.\n",
        encoding="utf-8",
    )
    docs = load_knowledge_base(d)
    ids = [x.document_id for x in docs]
    assert ids == ["a.md"]


def test_other_md_files_still_load(tmp_path):
    """只有 README.md 被跳过, 其他 .md 正常加载."""
    d = tmp_path / "kb"
    d.mkdir()
    (d / "README.md").write_text("# KB\n\n## Map\n\nx\n", encoding="utf-8")
    (d / "one.md").write_text("# One\n\n## S\n\ny\n", encoding="utf-8")
    (d / "two.md").write_text("# Two\n\n## S\n\nz\n", encoding="utf-8")
    ids = [x.document_id for x in load_knowledge_base(d)]
    assert ids == ["one.md", "two.md"]
