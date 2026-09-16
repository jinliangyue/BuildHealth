"""
Knowledge Document Loader · Phase 6B
=====================================

Scans `knowledge/` directory, parses Markdown, extracts frontmatter,
title (first `#` heading), and sections (subsequent `##` / `###`).

Skips hidden files, non-`.md` files, and the directory's own `README.md`
(see `SKIP_FILENAMES`).

Returns a list of `KnowledgeDocument` objects.
"""
import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

from app.knowledge.schemas import KnowledgeDocument

logger = logging.getLogger(__name__)

# Frontmatter pattern: <!-- key: value\n     key2: value2\n     -->
FRONTMATTER_RE = re.compile(
    r"^<!--\s*\n((?:[a-zA-Z_]+\s*:\s*.*\n)+)\s*-->\s*\n",
    re.MULTILINE,
)

# Filenames that document the knowledge base itself rather than being part
# of it. Indexing these would let directory navigation (e.g. the "Document
# Map" table) outrank real engineering content in retrieval.
SKIP_FILENAMES = frozenset({"readme.md"})


def _parse_frontmatter(text: str) -> Tuple[dict, str]:
    """Parse <!-- key: value ... --> frontmatter. Return (meta, remaining_text)."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    body = text[m.end():]
    meta = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip().lower()] = v.strip()
    return meta, body


def _parse_title_and_sections(body: str) -> Tuple[Optional[str], List[Tuple[str, str]]]:
    """
    解析 Markdown body.
    返回 (title, sections) 其中 sections = [(section_heading, section_text), ...]
    - 第一个 `# heading` 作为 title
    - 后续 `##` / `###` 作为 sections (只取 ## 层级, ### 视为内容)
    """
    lines = body.splitlines()
    title: Optional[str] = None
    sections: List[Tuple[str, str]] = []
    current_section: Optional[str] = None
    current_lines: List[str] = []

    def _flush_section():
        nonlocal current_section, current_lines
        if current_section is not None:
            content = "\n".join(current_lines).strip()
            if content:
                sections.append((current_section, content))
        current_section = None
        current_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            # 顶层 # heading
            if title is None:
                title = stripped[2:].strip()
            else:
                # 多个 # heading → 视为 section
                _flush_section()
                current_section = stripped[2:].strip()
                current_lines = []
        elif stripped.startswith("## ") and not stripped.startswith("### "):
            # 二级 ## heading → 新 section
            _flush_section()
            current_section = stripped[3:].strip()
            current_lines = []
        else:
            # 内容 (含 ### 三级 heading 与段落)
            if current_section is not None:
                current_lines.append(line)
            # 若 current_section 为 None 且 title 也不为 None, 顶级 # 之前的 prologue 丢弃
    _flush_section()
    return title, sections


def _load_single_md(md_path: Path) -> Optional[KnowledgeDocument]:
    """Parse one .md file. Return None on failure (with logged warning)."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to read %s: %s", md_path, e)
        return None

    meta, body = _parse_frontmatter(text)
    title, sections = _parse_title_and_sections(body)

    if title is None:
        # 损坏 markdown: 用 filename 作为 title, 整文件作为 single section
        title = md_path.stem.replace("_", " ").title()
        sections = [("Full Document", body.strip())]
    elif not sections:
        # 有 title 但无 ## section: 整文件作为 single section
        sections = [("Full Document", body.strip())]

    document_id = md_path.name
    full_text = body.strip()
    # 构造 sections 为 KnowledgeChunk 列表 (chunker 阶段处理)
    return KnowledgeDocument(
        document_id=document_id,
        title=title,
        source=meta.get("source") or "BuildHealth Internal Engineering Notes",
        sections=[],  # chunker 会填充
        full_text=full_text,
    )


def load_knowledge_base(knowledge_dir: Path) -> List[KnowledgeDocument]:
    """
    扫描 `knowledge_dir` 全部 .md 文件, 解析为 KnowledgeDocument 列表.
    跳过非 .md 文件, 跳过损坏文件 (log warning), 跳过隐藏文件.
    空目录 → 空列表.
    """
    if not knowledge_dir.exists() or not knowledge_dir.is_dir():
        logger.info(
            "knowledge directory %s does not exist or is not a dir; returning []",
            knowledge_dir,
        )
        return []

    docs: List[KnowledgeDocument] = []
    for md_path in sorted(knowledge_dir.iterdir()):
        if not md_path.is_file():
            continue
        if md_path.name.startswith("."):
            continue
        if md_path.name.lower() in SKIP_FILENAMES:
            continue
        if md_path.suffix.lower() != ".md":
            continue
        doc = _load_single_md(md_path)
        if doc is not None:
            docs.append(doc)
    return docs
