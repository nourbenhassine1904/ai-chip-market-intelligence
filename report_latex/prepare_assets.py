"""Prepare documentary copies from frozen sources; never run scientific models."""

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
ROOT = PROJECT.parent
SOURCE = ROOT / "report/rapport_final.md"
MANIFEST = PROJECT / "sources_manifest.json"
LLM_DOCUMENTS = (
    "llm/prompts/phase8_official_llm_prompt.md",
    "llm/responses/phase8_official_llm_response.md",
    "llm/human_analysis/phase8_human_vs_llm_comparison.md",
    "llm/human_analysis/phase8_hallucination_audit.csv",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(name):
    with (ROOT / f"outputs/tables/{name}.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        return list(csv.DictReader(handle))


def plain_tex(text):
    """Escape prose without executing or interpreting commands from the source."""
    text = str(text)
    superscripts = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")
    text = re.sub(
        r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+",
        lambda match: (
            "SUPERSCRIPTBEGIN" + match[0].translate(superscripts) + "SUPERSCRIPTEND"
        ),
        text,
    )
    escapes = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "→": r"\(\rightarrow\)",
        "≤": r"\(\leq\)",
        "≥": r"\(\geq\)",
        "≈": r"\(\approx\)",
        "×": r"\(\times\)",
        "−": "-",
        "–": "--",
        "—": "---",
        "α": r"\(\alpha\)",
        "β": r"\(\beta\)",
        "ω": r"\(\omega\)",
        "σ": r"\(\sigma\)",
        "ε": r"\(\varepsilon\)",
        "Φ": r"\(\Phi\)",
        "Θ": r"\(\Theta\)",
        "Δ": r"\(\Delta\)",
        "²": r"\textsuperscript{2}",
        "₂": r"\textsubscript{2}",
        "ₜ": r"\textsubscript{t}",
        "ᵈ": r"\textsuperscript{d}",
    }
    result = "".join(escapes.get(char, char) for char in text)
    return result.replace("SUPERSCRIPTBEGIN", r"\textsuperscript{").replace(
        "SUPERSCRIPTEND", "}"
    )


def inline(text):
    """Convert the limited Markdown conventions used in the canonical report."""
    tokens = {}

    def stash(value):
        key = f"LATEXTOKEN{len(tokens)}ZZ"
        tokens[key] = value
        return key

    text = re.sub(
        chr(96) + r"([^" + chr(96) + r"]+)" + chr(96),
        lambda m: stash(r"\sourcepath{" + m[1] + "}"),
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        lambda m: stash(r"\href{" + m[2] + "}{" + plain_tex(m[1]) + "}"),
        text,
    )
    text = re.sub(
        r"\[(R\d+(?:,\s*R\d+)*)\]",
        lambda m: stash(r"\cite{" + m[1].replace(" ", "") + "}"),
        text,
    )
    text = re.sub(
        r"\*\*(.+?)\*\*", lambda m: stash(r"\textbf{" + inline(m[1]) + "}"), text
    )
    text = re.sub(
        r"(?<!\*)\*([^*]+)\*(?!\*)",
        lambda m: stash(r"\emph{" + inline(m[1]) + "}"),
        text,
    )
    result = plain_tex(text)
    for key, value in tokens.items():
        result = result.replace(key, value)
    return result


def number(value, digits=3):
    return f"{float(value):.{digits}f}".replace(".", ",")


def integer(value):
    return str(int(float(value)))


def source_tables():
    # This existing documentary module uses stdlib CSV readers, not estimators.
    spec = importlib.util.spec_from_file_location(
        "frozen_report_sources", ROOT / "report/report_sources.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tables = module.tables()
    md = SOURCE.read_text(encoding="utf8")
    captions = {
        name: re.search(r"<!-- endtable: " + name + r" -->\s*(Tableau [^\n]+)", md)[1]
        for name in tables
    }
    diagnostics = csv_rows("phase3_arima_diagnostic_summary")
    tables["arima_diagnostics"] = (
        ["Langue", "Modèle avec drift", "LB(10)", "LB(20)", "ARCH-LM(5)"],
        [
            [
                r["language"],
                r["model"].replace("_drift", ""),
                number(r["ljung_box_10"], 6),
                number(r["ljung_box_20"], 6),
                f"{float(r['arch_lm_5']):.6g}",
            ]
            for r in diagnostics
        ],
        ["outputs/tables/phase3_arima_diagnostic_summary.csv"],
    )
    captions["arima_diagnostics"] = (
        "Diagnostics des modèles de moyenne provisoires de Phase 3A. "
        "TRAIN ; p-values Ljung-Box et ARCH-LM, sans unité. "
        "Six décimales ou six chiffres significatifs. "
        "Jarque-Bera rejette dans les deux langages ; zéro numérique par sous-flux."
    )
    validation = [
        r
        for r in csv_rows("phase3b_arima_validation_metrics")
        if r["model"] in ("Naive", "ARIMA111_drift", "ARIMA212_drift")
    ]
    tables["arima_validation"] = (
        ["Langue", "Candidat", "h", "n / prévu", "RMSE", "MAE"],
        [
            [
                r["language"],
                {
                    "ARIMA111_drift": "(1,1,1) + drift",
                    "ARIMA212_drift": "(2,1,2) + drift",
                    "Naive": "Naive",
                }[r["model"]],
                r["horizon"],
                r["n_forecasts"] + " / " + r["n_origins"],
                number(r["RMSE"]),
                number(r["MAE"]),
            ]
            for r in validation
        ],
        ["outputs/tables/phase3b_arima_validation_metrics.csv"],
    )
    captions["arima_validation"] = (
        "Validation interne ARIMA : sous-ensemble pédagogique Naive/(1,1,1)/(2,1,2). "
        "h en séances ; RMSE/MAE en USD ajustés, trois décimales. "
        "Scores sur origines disponibles : panels Python incomplets, non appariés "
        "à Naive dans ce tableau ; les gains de la règle utilisent les panels appariés."
    )
    var = {r["language"]: r for r in csv_rows("phase4_r_python_summary")}
    johansen = next(
        r
        for r in csv_rows("phase4_johansen_rank_comparison")
        if r["level_lags"] == "3" and r["null_rank_at_most"] == "0"
    )
    indicators = [
        ("Ordre proposé AIC/BIC", "aic_proposed_lag", integer),
        ("Ordre retenu", "selected_lag", integer),
        ("Module compagnon maximal", "max_companion_modulus", lambda v: number(v, 6)),
        ("Portmanteau, p à 20", "serial_p20", lambda v: number(v, 6)),
        ("Portmanteau, p à 30", "serial_p30", lambda v: number(v, 6)),
        ("Rang Johansen", "johansen_rank", integer),
        ("VECM justifié", "vecm_justified", lambda v: "Oui" if v == "True" else "Non"),
    ]
    var_rows = [
        [label, formatter(var["R"][key]), formatter(var["Python"][key])]
        for label, key, formatter in indicators
    ]
    var_rows.extend(
        [
            [
                "Trace Johansen au rang 0",
                number(johansen["trace_statistic_r"], 6),
                number(johansen["trace_statistic_python"], 6),
            ],
            [
                "Valeur critique native à 5 %",
                number(johansen["critical_5pct_r"], 4),
                number(johansen["critical_5pct_python"], 4),
            ],
        ]
    )
    tables["var_johansen"] = (
        ["Indicateur TRAIN", "R", "Python"],
        var_rows,
        [
            "outputs/tables/phase4_r_python_summary.csv",
            "outputs/tables/phase4_johansen_rank_comparison.csv",
        ],
    )
    captions["var_johansen"] = (
        "Décisions et diagnostics multivariés. VAR sur rendements ; "
        "Johansen principal à trois retards en niveaux. "
        "P-values, module et trace sans unité ; tables critiques natives conservées."
    )
    networks = [csv_rows("phase6_locked_lstm")[0], csv_rows("phase6_locked_gru")[0]]
    neural_fields = [
        ("Configuration", "configuration", str),
        ("Fenêtre, séances", "lookback", integer),
        ("Unités récurrentes", "units", integer),
        ("Dropout", "dropout", lambda v: number(v, 2)),
        ("Paramètres entraînables", "trainable_parameters", integer),
        ("Ratio RMSE moyen de sélection", "average_RMSE_ratio", lambda v: number(v, 6)),
        ("Epochs du refit verrouillé", "median_best_epoch", integer),
    ]
    tables["neural_comparison"] = (
        ["Spécification TRAIN", "LSTM C", "GRU C"],
        [
            [label, *[formatter(row[key]) for row in networks]]
            for label, key, formatter in neural_fields
        ],
        [
            "outputs/tables/phase6_locked_lstm.csv",
            "outputs/tables/phase6_locked_gru.csv",
        ],
    )
    captions["neural_comparison"] = (
        "Configurations verrouillées et score de sélection interne. "
        "Ratio : moyenne des six ratios RMSE modèle/Naive par fold et horizon ; "
        "ce n'est pas le ratio des RMSE poolées. Aucune métrique holdout n'est utilisée."
    )
    validation = [
        r for r in csv_rows("phase6_validation_metrics_summary")
        if r["model"] == "Naive" or r["configuration"] == "C"
    ]
    validation.sort(key=lambda r: (
        int(r["horizon"]), {"Naive": 0, "LSTM": 1, "GRU": 2}[r["model"]]
    ))
    tables["neural_validation"] = (
        ["Candidat", "h", "n", "RMSE", "MAE"],
        [[r["model"] + (" C" if r["configuration"] == "C" else ""),
          r["horizon"], r["n_forecasts"], number(r["RMSE"]), number(r["MAE"])]
         for r in validation],
        ["outputs/tables/phase6_validation_metrics_summary.csv"],
    )
    captions["neural_validation"] = (
        "Validation temporelle dans TRAIN (Phase 6), distincte du TEST Phase 7. "
        "Erreurs poolées sur trois folds, 561 prévisions par candidat et horizon ; "
        "h en séances, RMSE/MAE en USD ajustés, trois décimales. "
        "Les origines chevauchantes ne sont pas indépendantes."
    )
    checks = csv_rows("phase7_recommendation_checks")
    recommendation = csv_rows("phase7_final_model_recommendation")[0]
    if recommendation["final_recommended_price_model"] != "Naive":
        raise ValueError("Frozen official recommendation differs from Naive")
    tables["recommendation"] = (
        ["Modèle", "Ratio RMSE moyen", "Ratio MAE moyen", "Éligible"],
        [
            [
                r["model"],
                number(r["average_RMSE_ratio"], 6),
                number(r["average_MAE_ratio"], 6),
                "Oui" if r["eligible_challenger"] == "True" else "Non",
            ]
            for r in checks
        ],
        [
            "outputs/tables/phase7_recommendation_checks.csv",
            "outputs/tables/phase7_final_model_recommendation.csv",
        ],
    )
    captions["recommendation"] = (
        "Application de la règle finale pré-déclarée. Ratios sans unité, six décimales. "
        "Naive est le benchmark, pas un challenger ; aucun challenger éligible. "
        "Modèle recommandé : Naive."
    )
    return tables, captions


def cell_tex(value):
    scientific = re.fullmatch(r"([-+]?\d+(?:[.,]\d+)?)e([-+]?\d+)", str(value))
    if scientific:
        mantissa = scientific[1].replace(".", ",").replace(",", "{,}")
        return r"\(" + mantissa + r"\times 10^{" + str(int(scientific[2])) + r"}\)"
    return inline(str(value))


def render_table(name, headers, rows, caption, sources):
    # Flexible text columns; explicit compact numerical columns for the main panels.
    layouts = {
        "data": "Xrrr",
        "descriptive": "Xrrrr",
        "stationarity": "XXXXX",
        "granger": "XrrX",
        "garch": "Xrrrrr",
        "final_metrics": "Xrrrrr",
        "dm": "XrrrX",
        "llm": "XrrX",
        "costs": "XrrrX",
        "arima_diagnostics": "lXrrr",
        "arima_validation": "lXrrrr",
        "var_johansen": "Xrr",
        "neural_comparison": "Xrr",
        "neural_validation": "Xrrrr",
        "recommendation": "Xrrc",
    }
    caption = re.sub(r"^Tableau \d+ [—-] ", "", caption)
    if "Source" in caption:
        caption, original_source = caption.split("Source", 1)
        note = "Source" + original_source
    else:
        note = "Sources : " + " ; ".join(chr(96) + s + chr(96) for s in sources) + "."
    content = [
        "% Documentary display only; edit preparation definitions for a refresh.",
        "% Source CSVs: " + "; ".join(sources),
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\caption{" + inline(caption.strip()) + "}",
        r"\label{tab:" + name + "}",
        r"\small",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.16}",
        r"\begin{tabularx}{\linewidth}{" + layouts[name] + "}",
        r"\toprule",
        " & ".join(r"\textbf{" + cell_tex(h) + "}" for h in headers) + r" \\",
        r"\midrule",
    ]
    content.extend(" & ".join(cell_tex(c) for c in row) + r" \\" for row in rows)
    content.extend(
        [
            r"\bottomrule",
            r"\end{tabularx}",
            r"\par\smallskip",
            r"\begin{minipage}{\linewidth}\footnotesize " + inline(note),
            r"\end{minipage}",
            r"\end{table}",
            "",
        ]
    )
    return "\n".join(content)


def expected_assets():
    """Compute display plans by reading archived cells, without new estimation."""
    md = SOURCE.read_text(encoding="utf8")
    images = re.findall(r"!\[([^]]+)\]\(([^)]+)\)", md)
    tables, captions = source_tables()
    if len(images) != 15 or len(tables) != 15:
        raise ValueError("Unexpected canonical figure/table coverage")
    images.extend([
        ("Décomposition STL du log-prix NVDA sur TRAIN",
         "../outputs/figures/phase2/nvda_log_price_stl_train.png"),
        ("Corrélations glissantes sur 60 séances TRAIN",
         "../outputs/figures/phase2/rolling_correlations_60d.png"),
    ])
    return images, tables, captions


def check_assets():
    if not MANIFEST.is_file():
        raise ValueError("Missing sources manifest; run --refresh-assets once")
    manifest = json.loads(MANIFEST.read_text(encoding="utf8"))
    images, tables, captions = expected_assets()
    for record in manifest["source_files"]:
        if digest(ROOT / record["path"]) != record["sha256"]:
            raise ValueError("Frozen source changed: " + record["path"])
    for record in manifest["figures"]:
        if (digest(PROJECT / record["copy"]) != record["sha256"]
                or digest(ROOT / record["source"]) != record["sha256"]):
            raise ValueError("Figure copy differs: " + record["copy"])
    if {r["name"] for r in manifest["tables"]} != set(tables):
        raise ValueError("Incomplete table manifest")
    for record in manifest["tables"]:
        name = record["name"]
        headers, rows, sources = tables[name]
        expected = render_table(name, headers, rows, captions[name], sources)
        actual = (PROJECT / f"tables/{name}.tex").read_text(encoding="utf8")
        if actual != expected:
            raise ValueError("Table display differs from frozen source: " + name)
    if len(images) != len(manifest["figures"]):
        raise ValueError("Incomplete figure manifest")
    if {r["source"] for r in manifest["document_copies"]} != set(LLM_DOCUMENTS):
        raise ValueError("Incomplete LLM delivery package")
    for record in manifest["document_copies"]:
        if (digest(ROOT / record["source"]) != record["sha256"]
                or digest(PROJECT / record["copy"]) != record["sha256"]):
            raise ValueError("LLM documentary copy differs: " + record["copy"])
    raw = (ROOT / "llm/responses/phase8_official_llm_response.md").read_bytes()
    section = raw[
        raw.index(b"B. VULGARISATION\n") : raw.index(
            b"C. SIMULATED INVESTMENT INTERPRETATION\n"
        )
    ]
    if (PROJECT / "appendices/llm_section_b_original.txt").read_bytes() != section:
        raise ValueError("Original LLM excerpt differs")
    print(
        "PASS: 17 historical figure copies, 15 sourced tables, four exact LLM documents, "
        "exact LLM excerpt and source hashes"
    )
    return manifest


def refresh_assets():
    # A documentary refresh must never silently accept changed archived sources.
    if MANIFEST.is_file():
        previous = json.loads(MANIFEST.read_text(encoding="utf8"))
        for record in previous["source_files"]:
            if digest(ROOT / record["path"]) != record["sha256"]:
                raise ValueError("Frozen source changed: " + record["path"])
    images, tables, captions = expected_assets()
    for name in ("figures", "tables", "appendices"):
        (PROJECT / name).mkdir(parents=True, exist_ok=True)
    figures = []
    sources = {
        "report/rapport_final.md",
        "report/rapport_final.docx",
        "report/rapport_final.pdf",
    }
    for title, link in images:
        path = (SOURCE.parent / link).resolve()
        relative = path.relative_to(ROOT).as_posix()
        target = PROJECT / "figures" / path.name
        shutil.copyfile(path, target)
        figures.append(
            {
                "caption_original": title,
                "source": relative,
                "copy": "figures/" + path.name,
                "sha256": digest(path),
            }
        )
        sources.add(relative)
    table_records = []
    for name, (headers, rows, files) in tables.items():
        (PROJECT / f"tables/{name}.tex").write_text(
            render_table(name, headers, rows, captions[name], files), encoding="utf8"
        )
        table_records.append(
            {
                "name": name,
                "sources": files,
                "headers": headers,
                "displayed_rows": rows,
                "caption": captions[name],
            }
        )
        sources.update(files)
    document_copies = []
    for relative in LLM_DOCUMENTS:
        target = PROJECT / "documents" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        document_copies.append({
            "source": relative,
            "copy": target.relative_to(PROJECT).as_posix(),
            "sha256": digest(ROOT / relative),
        })
        sources.add(relative)
    sources.update([
        "outputs/tables/phase2_rolling_correlation_summary.csv",
        "outputs/tables/phase2_weekday_returns.csv",
    ])
    raw = (ROOT / "llm/responses/phase8_official_llm_response.md").read_bytes()
    section = raw[
        raw.index(b"B. VULGARISATION\n") : raw.index(
            b"C. SIMULATED INVESTMENT INTERPRETATION\n"
        )
    ]
    (PROJECT / "appendices/llm_section_b_original.txt").write_bytes(section)
    sources.update(
        [
            "report/report_sources.py",
            "report/README.md",
            "docs/reproduction_guide.md",
            "docs/data_dictionary.md",
            "docs/protocol.md",
            "docs/decisions.md",
            "docs/final_figure_selection.md",
            "docs/phase9a_reproducibility.md",
            "docs/phase9a_repository_audit.md",
            "docs/phase9b_report_audit.md",
            "docs/phase9b_results_traceability.csv",
            "docs/phase9c_preflight_audit.md",
            "llm/responses/phase8_official_llm_response.md",
            "llm/human_analysis/phase8_hallucination_audit.csv",
            "docs/phase9c_full_summary.json",
            "docs/phase9c_full_execution_audit.md",
            "docs/phase9c_full_reproduction.md",
            "docs/final_requirements_checklist.md",
            "docs/phase7_final_evaluation_protocol.json",
            "docs/phase7_final_evaluation_protocol.md",
        ]
    )
    sources.update(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "docs").glob("phase[1-8]*")
        if path.is_file()
    )
    manifest = {
        "scope": "Documentary copies/displays from frozen repository; no model or statistical test rerun",
        "canonical_report": "report/rapport_final.md",
        "historical_figures": len(figures),
        "new_process_figure": "figures/pipeline.tex (TikZ, documentary synthesis)",
        "tables_count": len(table_records),
        "figures": figures,
        "tables": table_records,
        "document_copies": document_copies,
        "source_files": [
            {"path": p, "sha256": digest(ROOT / p)} for p in sorted(sources)
        ],
        "llm_section_b_sha256": hashlib.sha256(section).hexdigest(),
        "official_recommendation": "Naive",
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    return check_assets()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-assets", action="store_true")
    args = parser.parse_args()
    if args.refresh_assets:
        refresh_assets()
    else:
        check_assets()


if __name__ == "__main__":
    main()
