# Rapport scientifique LaTeX — Phase 9D

Projet documentaire séparé du rapport Markdown/Word/PDF de référence sous `report/`.
La recommandation officielle reste **Naive**. Aucun modèle ni test statistique
n'est exécuté par les outils de ce dossier.

## Structure et édition en équipe

| Fichier / dossier | Usage |
|---|---|
| `main.tex` | Ordre des sections, sommaire, bibliographie et annexes |
| `metadata.tex` | Institution, spécialité, classe, membres, enseignant, date et année |
| `preamble.tex` | Typographie, marges, couleurs et macros |
| `frontmatter/` | Couverture, résumé et références internes |
| `chapters/01_…tex` à `12_…tex` | Contenu scientifique réparti par thème |
| `appendices/A_…tex` à `F_…tex` | Diagnostics, spécifications, texte original du LLM et courbes d'apprentissage |
| `figures/` | Dix-sept copies PNG historiques et schéma natif `pipeline.tex` |
| `tables/` | Quinze tableaux composés depuis les CSV gelés |
| `documents/llm/` | Quatre documents LLM complets, copies identiques aux originaux |
| `references.bib` | Dix-sept sources primaires déjà citées dans le rapport canonique |
| `sources_manifest.json` | Provenance, cellules affichées et empreintes SHA-256 |
| `rapport_final_latex.pdf` | Export de cette version LaTeX |

La couverture a été personnalisée dans le commit `ccc7624` avec les quatre
membres, l'enseignant, la spécialité, la classe et la date de remise.
Ces champs sont désormais renseignés dans `metadata.tex`. Répartir
les chapitres entre membres ; les chemins sont relatifs et les fichiers UTF-8.
Employer `\label`, `\ref` et `\cite` pour garder une numérotation automatique.
Échapper les caractères réservés de LaTeX, notamment `%`, `&` et `_`.

Les tableaux sont des présentations des valeurs archivées, avec leurs arrondis,
unités, périmètres et sources. Le panneau ARIMA Python indique les prévisions
manquantes ; il ne remplace pas les comparaisons appariées du protocole.
Un seizième tableau, écrit dans le chapitre 11, distingue les preuves de
reproduction 9C3. Les dix-sept figures historiques sont conservées en corps ou
annexes, et le schéma TikZ constitue la dix-huitième figure. Les compléments
STL et corrélations glissantes sont en annexes A/B ; les courbes d'apprentissage
LSTM/GRU sont en annexe F. Le tableau de validation Phase 6 du chapitre 8
présente Naive, LSTM C et GRU C sur TRAIN et se distingue du TEST Phase 7.

Ne pas retoucher les métriques pour améliorer la mise en page. Une adaptation
de présentation des tableaux passe par `prepare_assets.py`, puis par une
régénération explicite et une nouvelle revue. Les chapitres, annexes et le
schéma TikZ ne sont pas réécrits par le script de compilation.

## Compilation Windows depuis la racine du dépôt

Prérequis : Python 3.12 (bibliothèque standard uniquement pour les outils),
une distribution TeX exposant `pdflatex` et `bibtex` dans le PATH, et les packages
du préambule déjà installés. La compilation a été vérifiée avec MiKTeX 25.12
lors des audits antérieurs à la personnalisation de la couverture (`ccc7624`).
Les principales dépendances TeX sont `babel` français, `geometry`, `mathptmx`,
`amsmath`, `amssymb`, `graphicx`, `booktabs`, `tabularx`, `longtable`, `microtype`,
`caption`, `placeins`, `xcolor`, `tikz`, `fancyhdr`, `xurl` et `hyperref`.

```powershell
.\report_latex\build_latex_report.ps1
```

Le script utilise `.venv/Scripts/python.exe` s'il existe, sinon Python du PATH.
On peut préciser `-Python 'C:\chemin\python.exe'`. L'équivalent Python est :

```powershell
.\.venv\Scripts\python.exe -B report_latex/build_latex_report.py
```

Le build vérifie les sources et les copies, lance pdfLaTeX, BibTeX puis deux
passes pdfLaTeX, et copie le PDF final seulement après succès. Les journaux et
`compile_audit.json` sont dans `_build/`, ignoré par Git. L'installation
automatique MiKTeX et le shell escape sont désactivés. Les entrées du PATH qui
ne sont pas des dossiers sont filtrées dans les seuls subprocess TeX.

Un package TeX absent doit être installé par l'équipe avant la compilation.
Le script ne télécharge pas de données, n'entraîne aucun modèle et ne modifie
aucun export sous `report/`.

## Contrôles et régénération documentaire

Ces commandes requièrent le dépôt complet et ses artefacts gelés :

```powershell
.\.venv\Scripts\python.exe -B report_latex/verify_latex_project.py
.\.venv\Scripts\python.exe -m ruff check report_latex
```

Le vérificateur contrôle les chemins locaux, tous les fichiers TeX inclus,
les labels, les dix-sept citations, les dix-sept PNG, les quinze tableaux,
les SHA des sources, les quatre copies LLM complètes et le texte de l'annexe E. Il n'est pas un audit indépendant
de chaque clause du PDF officiel du cahier des charges.

Pour recréer uniquement les copies et tableaux documentaires depuis les
sources actuelles, après revue explicite de leur intégrité :

```powershell
.\report_latex\build_latex_report.ps1 -RefreshAssets
```

Cette option contrôle d'abord les empreintes déjà enregistrées, puis réécrit
les copies PNG, les tableaux, les quatre documents LLM complets, l'extrait texte du LLM et
le manifeste **dans ce dossier seulement**. Elle ne valide pas de nouvelles
sorties scientifiques. Le build normal conserve les empreintes déjà enregistrées.

## Compilation autonome et adaptation ultérieure

Le contenu LaTeX ne dépend pas d'un chemin absolu, de Python, de R ou d'un
service externe. Pour partager le projet, copier l'ensemble de `report_latex/`
sans `_build/`, en conservant ses sous-dossiers. Dans ce dossier, les commandes
standard sont :

```text
pdflatex -interaction=nonstopmode -halt-on-error -no-shell-escape main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error -no-shell-escape main.tex
pdflatex -interaction=nonstopmode -halt-on-error -no-shell-escape main.tex
```

Avec MiKTeX, ajouter `--disable-installer` à chaque commande pdfLaTeX pour
conserver l'absence d'installation automatique. Les auxiliaires sont ignorés
par Git. Cette voie autonome ne contrôle pas les SHA des sources du dépôt.

L'utilisateur a réellement importé et compilé la version précédente dans
Prism AI et a signalé **29 pages affichées**. Cette preuve concerne la version
avant la revue corrective du 10 octobre 2026. La révision corrective a ensuite
été compilée et contrôlée localement avec MiKTeX, avant la personnalisation
de la couverture dans `ccc7624` ; ces contrôles décrivent un état antérieur.
Aucun contrôle de la couverture personnalisée dans Prism n'est attesté ici.
Un réimport, une compilation et une relecture dans Prism restent à effectuer.
Aucune validation de toutes les pages de la version actuelle dans Prism ni
du travail collaboratif n'est revendiquée.

## Limites scientifiques et documentaires

- FAST relit et vérifie les résultats gelés ; ce n'est pas une nouvelle étude.
- Le runner FULL a terminé dans un sandbox préparé. Le notebook FULL complet
  sur machine vierge reste **PARTIAL** ; le chapitre 11 expose les différences
  GRU de reproduction sans remplacer les prévisions officielles.
- Le PDF officiel du cahier des charges n'était pas intégré au dépôt lors de
  l'audit automatisé. Les sources disponibles et les exigences transmises
  par l'équipe constituent le périmètre de cette version.
- L'annexe E identifie le texte original du LLM. Son extrait exact est dans
  `appendices/llm_section_b_original.txt` ; la réponse officielle reste intacte.
- Remettre tout `report_latex/` sans `_build/`, y compris `documents/llm/` :
  prompt, réponse, comparaison humaine et audit des hallucinations complets.
  Leurs chemins et empreintes sont contrôlés par le
  manifeste ; le PDF seul ne contient que l'extrait vulgarisé et les références.
- Les champs de couverture sont renseignés depuis `ccc7624`. La fidélité
  scientifique et la mise en page doivent être relues après toute édition.

L'audit de création et les contrôles effectués sont consignés dans
`docs/phase9d_latex_report.md` à la racine du dépôt.
