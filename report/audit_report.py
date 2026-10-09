"""Inspect the rendered Word/PDF report and record read-only Phase 9B evidence.

Run with the existing system Python that provides pypdf. No installation, model
imports, downloads or writes to historical scientific artifacts are performed.
"""

import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pdf = ROOT / "report/rapport_final.pdf"
    docx = ROOT / "report/rapport_final.docx"
    pages = [page.extract_text().encode("utf8", errors="replace").decode("utf8")
             for page in PdfReader(pdf).pages]
    cache = ROOT / ".cache/phase9b"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "page_text.json").write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf8")
    with ZipFile(docx) as archive:
        app = ET.fromstring(archive.read("docProps/app.xml"))
        word_pages = int(app.find("{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Pages").text)
        document = ET.fromstring(archive.read("word/document.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        styles = ET.fromstring(archive.read("word/styles.xml"))
        heading_styles = {s.get("{" + ns["w"] + "}styleId")
                          for s in styles.findall("w:style", ns)
                          if s.find("w:pPr/w:outlineLvl", ns) is not None
                          and int(s.find("w:pPr/w:outlineLvl", ns).get("{" + ns["w"] + "}val")) < 2}
        headings = []
        for p in document.findall(".//w:body/w:p", ns):
            style = p.find("w:pPr/w:pStyle", ns)
            if style is not None and style.get("{" + ns["w"] + "}val") in heading_styles:
                headings.append("".join(t.text or "" for t in p.findall(".//w:t", ns)))
    found = []
    for heading in headings:
        # The TOC includes dotted/tabbed page references. A body heading occupies
        # its own extracted line, avoiding front-matter matches.
        matching = [i + 1 for i, text in enumerate(pages) if heading in text.splitlines()]
        if len(matching) != 1:
            raise ValueError(f"Heading occurrence in rendered body: {heading}: {matching}")
        found.append({"title": heading, "page": matching[0]})
    body_start = next(x["page"] for x in found if x["title"].strip() == "1 Introduction")
    annex_start = next(x["page"] for x in found if x["title"] == "Annexes")
    audit = {
        "renderer": "Microsoft Word COM; PDF ExportAsFixedFormat; pypdf independent page/text inspection",
        "total_pages": len(pages), "word_saved_page_count": word_pages,
        "front_matter_pages": body_start - 1, "body_start_page": body_start,
        "annex_start_page": annex_start, "body_pages_excluding_annexes": annex_start - body_start,
        "pages_excluding_annexes": annex_start - 1,
        "annex_pages": len(pages) - annex_start + 1, "sections": found,
        "markdown_sha256": digest(ROOT / "report/rapport_final.md"),
        "docx_sha256": digest(docx), "pdf_sha256": digest(pdf),
        "visual_review": "PENDING",
    }
    (ROOT / "docs/phase9b_render_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    extra = ROOT / "docs/phase9b_frozen_references.json"
    if not extra.exists():
        paths = ["docs/phase9a_frozen_artifacts_manifest.json", "notebooks/AI_Chip_Market_Intelligence.ipynb"]
        records = []
        for path in paths:
            blob = subprocess.check_output(["git", "show", f"v0.12.0-phase9a:{path}"], cwd=ROOT)
            # Capture the local newline representation only if its normalized
            # text equals the Phase 9A tag. The tag provides independent evidence.
            local = (ROOT / path).read_bytes()
            if local.replace(b"\r\n", b"\n") != blob.replace(b"\r\n", b"\n"):
                raise ValueError(f"Historical Phase 9A artifact changed: {path}")
            records.append({"path": path, "sha256": hashlib.sha256(local).hexdigest(),
                            "git_blob_sha256": hashlib.sha256(blob).hexdigest()})
        extra.write_text(json.dumps({"base_tag": "v0.12.0-phase9a", "artifacts": records}, indent=2) + "\n", encoding="utf8")
    print(json.dumps({k: v for k, v in audit.items() if k != "sections"}, indent=2))
    for i, text in enumerate(pages):
        print(i + 1, text[:100].replace("\n", " | "), "words", len(text.split()))


if __name__ == "__main__":
    main()
