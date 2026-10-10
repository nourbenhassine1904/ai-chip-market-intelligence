"""Check local TeX dependencies, reference closure and the verbatim LLM annex."""

import re
from pathlib import Path

from prepare_assets import check_assets

PROJECT = Path(__file__).resolve().parent


def local_file(relative, suffix=""):
    candidate = (PROJECT / (relative + suffix)).resolve()
    if not candidate.is_relative_to(PROJECT) or not candidate.is_file():
        raise ValueError("Missing or nonlocal document asset: " + relative + suffix)
    return candidate


def verify_structure():
    pending = [PROJECT / "main.tex"]
    visited = set()
    graphics = set()
    figure_labels = []
    bibliographies = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        text = path.read_text(encoding="utf8")
        for name in re.findall(r"\\input\{([^}]+)\}", text):
            if "#" not in name:  # Preamble's explicitly checked chapter macro.
                pending.append(local_file(name, ".tex"))
        for name in re.findall(r"\\chapterfile\{([^}]+)\}", text):
            pending.append(local_file("chapters/" + name, ".tex"))
        for name in re.findall(r"\\historicalfigure\{([^}]+)\}", text):
            graphics.add(local_file("figures/" + name))
            figure_labels.append("fig:" + name)
        for name in re.findall(r"\\bibliography\{([^}]+)\}", text):
            bibliographies.add(local_file(name, ".bib"))
    all_tex = set(PROJECT.rglob("*.tex"))
    all_tex = {path for path in all_tex if "_build" not in path.parts}
    if all_tex != visited:
        raise ValueError("Unreferenced TeX files: " + str(sorted(all_tex - visited)))
    combined = "\n".join(path.read_text(encoding="utf8") for path in visited)
    labels = [
        name for name in re.findall(r"\\label\{([^}]+)\}", combined) if "#" not in name
    ] + figure_labels
    if len(labels) != len(set(labels)):
        raise ValueError("Duplicate TeX label")
    required = set(re.findall(r"\\(?:ref|pageref|eqref)\{([^}]+)\}", combined))
    if required - set(labels):
        raise ValueError("Undefined labels: " + str(sorted(required - set(labels))))
    references = set()
    for bibliography in bibliographies:
        references.update(
            re.findall(r"@\w+\{([^,]+),", bibliography.read_text(encoding="utf8"))
        )
    cited = set()
    for names in re.findall(r"\\cite\{([^}]+)\}", combined):
        cited.update(name.strip() for name in names.split(","))
    if references != cited or len(references) != 17:
        raise ValueError("Bibliography/citation mismatch: " + str(references ^ cited))
    expected_figures = {path.resolve() for path in (PROJECT / "figures").glob("*.png")}
    if graphics != expected_figures or len(graphics) != 17:
        raise ValueError(
            "Historical figure coverage differs from the 17 source figures"
        )
    if sum(path.parent.name == "tables" for path in visited) != 15:
        raise ValueError("Expected 15 sourced table inputs")
    print(
        f"PASS: {len(visited)} reachable TeX files, 17 local PNGs, 17 cited references"
    )


def verify_llm_annex():
    annex = (PROJECT / "appendices/E_llm.tex").read_text(encoding="utf8")
    body = annex.split(r"\begin{quote}\small", 1)[1].split(r"\end{quote}", 1)[0]
    # Only the three typography substitutions present in this source excerpt.
    body = body.replace(r"\%", "%").replace(r"\_", "_").replace("---", "—")
    original = (PROJECT / "appendices/llm_section_b_original.txt").read_text(
        encoding="utf8"
    )
    normalize = lambda text: re.sub(r"\s+", " ", text).strip()
    if normalize(body) != normalize(original):
        raise ValueError("LLM annex body differs from the original section B")
    print(
        "PASS: displayed LLM annex equals original section B after typography normalization"
    )


def main():
    check_assets()
    verify_structure()
    verify_llm_annex()


if __name__ == "__main__":
    main()
