# Phase 9D — Rapport LaTeX modulaire

Audit de création finalisé le **10 octobre 2026** sur `feature/latex-report`.
Les sections « Livrables créés » à « Validations » ci-dessous décrivent la
création initiale. La revue corrective finale du même jour est documentée
séparément en fin d'audit ; ses chiffres et preuves actualisent cette version.
Point de départ : `24ab075f8117266301e875cb2db2785038d6f822`, identique au
HEAD de `main` au début de cette branche. Travail additif ; commit local uniquement.

## Livrables créés

**64 nouveaux fichiers versionnables** : 63 sous `report_latex/` et le présent
audit. Aucun fichier préexistant n'est modifié.

| Ensemble | Nombre | Contenu |
|---|---:|---|
| Sources TeX | 38 | 3 fichiers principaux, 3 liminaires, 12 chapitres, 5 annexes, 14 tableaux et 1 schéma TikZ |
| Figures historiques PNG | 15 | Copies exactes des quinze figures du rapport canonique |
| Utilitaires Python | 3 | Préparation documentaire, compilation et vérification |
| PowerShell | 1 | `build_latex_report.ps1` |
| Bibliographie | 1 | `references.bib`, 17 sources primaires existantes |
| Manifeste | 1 | `sources_manifest.json`, 73 sources avec SHA-256 et cellules affichées |
| Extrait LLM original | 1 | Copie exacte de la section B, en UTF-8 |
| Guide et exclusions Git | 2 | `README.md` et `.gitignore` local |
| PDF LaTeX | 1 | `rapport_final_latex.pdf` |
| Audit documentaire | 1 | Ce fichier |
| **Total** | **64** | Journaux et images de revue exclus du versionnement |

Entrée : [main.tex](../report_latex/main.tex). Guide d'édition et de compilation :
[README](../report_latex/README.md). Couverture modifiable dans `metadata.tex` :
membres, enseignant, date et formation restent clairement à compléter.

## Contenu et fidélité scientifique

Les douze chapitres couvrent introduction/objectifs, données et préparation,
méthodologie, EDA/stationnarité, ARIMA/validation, VAR/Granger/Johansen/VECM,
GARCH, LSTM/GRU, holdout final, analyse critique du LLM, reproduction et conclusion.
Les annexes A–E conservent les diagnostics complémentaires, les spécifications,
la traçabilité et l'explication vulgarisée originale du LLM.

- Les 15 figures historiques sont identiques à leurs sources en bytes ; aucune
  image scientifique n'est redessinée. Le nouveau schéma TikZ synthétise les
  protocoles et distingue prix, interactions et variance conditionnelle.
- Les 9 tableaux du rapport canonique sont repris depuis son lecteur CSV
  documentaire. Cinq présentations supplémentaires utilisent directement les
  cellules gelées : diagnostics ARIMA, validation ARIMA, VAR/Johansen,
  spécifications LSTM/GRU et application de la règle de recommandation.
  Les unités, périmètres, arrondis et fichiers sources accompagnent les tableaux.
- Un tableau documentaire supplémentaire, dans le chapitre 11, présente les
  preuves A/B/C de reproduction. Le PDF contient donc **15 tableaux et 16 figures**.
- Les panneaux Python incomplets de validation ARIMA restent explicitement
  identifiés. Les scores disponibles ne sont pas assimilés aux gains appariés
  qui gouvernent la décision du protocole.
- **Naive reste recommandé**. ARIMA reste proche mais ne satisfait pas la règle
  complète prédéfinie ; les résultats neuronaux défavorables sont conservés.
  Non-rejet DM ne signifie pas équivalence. Granger ne prouve pas une causalité
  économique et GARCH ne prédit pas la direction du prix.
- Le contexte historique GARCH et la source FOMC déjà présents dans le rapport
  canonique sont repris comme concordance descriptive. Aucune attribution
  causale ou nouvelle vérification historique indépendante n'est ajoutée.
- Les 17 références BibTeX proviennent des sources primaires déjà citées.
  Les citations multiples ADF/KPSS et LSTM/GRU sont reliées à la bibliographie.
  Les dates de consultation sont attribuées au rapport source.
- L'annexe E reproduit les dix paragraphes de la section B officielle.
  La composition typographique est adaptée, sans correction du texte du LLM.
  Le vérificateur compare l'annexe affichée à la copie originale après
  normalisation des seules substitutions typographiques et espaces.

Réponse LLM officielle intacte, SHA-256 :
`eecb0de3e0dd8e152e93db70ff71f9dad87024b7b2f3e1bee1ede05225f6f3b4`.
Les empreintes des rapports Markdown/DOCX/PDF de référence, des sources et de
l'extrait B sont consignées dans le manifeste du nouveau projet.

## FAST, FULL et cahier des charges

Le chapitre 11 et l'annexe D présentent l'état **post-audit 9C3**, en distinguant
les preuves historiques 9A/9B/9C1 :

- FAST relit et contrôle les résultats gelés ; il ne réexécute pas l'étude.
- Le runner FULL a réellement terminé dans un sandbox préparé, avec les logs
  et résultats décrits dans `docs/phase9c_full_execution_audit.md`.
- La démonstration sur machine vierge et l'exécution complète du notebook FULL
  demeurent **PARTIAL**. Les variations GRU sont exposées sans remplacer les
  résultats officiels ni prétendre avoir établi leur mécanisme numérique.
- Les prérequis et actions restantes incluent snapshots vérifiés ou téléchargement
  contrôlé, sources Python/R réelles, packages, TensorFlow CPU, clone indépendant,
  checkpoint/gate Phase 7 authentiques et préservation de la réponse LLM.
  Les temps historiques sont distingués d'une durée garantie de reproduction.

Le PDF officiel du cahier des charges **n'était pas intégré au dépôt lors de
l'audit automatisé**. Cette limite d'accès ne constitue pas un livrable
scientifique obligatoire manquant. Aucune certification indépendante exhaustive
de ses clauses n'est revendiquée. Les exigences transmises et documentées,
dont l'annexe LLM et la reproduction §8.3, sont prises en compte.

## Compilation et pagination vérifiées

Compilation réussie avec **MiKTeX-pdfTeX 4.23 / MiKTeX 25.12**, BibTeX et les
packages déjà installés. Aucun téléchargement automatique de package ni shell
escape. Le script PowerShell a été exécuté avec succès ; la version finale a
ensuite été compilée par le même utilitaire Python après ajustement des annexes.

Pipeline de compilation : pdfLaTeX, BibTeX, puis deux passes pdfLaTeX ; les
quatre commandes retournent zéro. La dernière passe ne contient aucun label
ou citation non résolu, caractère manquant ou `Overfull`.
Les entrées du PATH qui sont des fichiers plutôt que des dossiers sont filtrées
pour les subprocess TeX seulement, afin de contourner une anomalie locale du PATH.

**29 pages physiques au total, dont 25 hors annexes** : couverture, sommaire,
résumé et bibliographie inclus. Le corps scientifique occupe les pages physiques
4–24, soit 21 pages ; la bibliographie est en page 25 et les annexes en pages
26–29. Le format de 15–25 pages hors annexes est respecté avec cette convention
de comptage explicite. La pagination romaine des préliminaires puis arabe du
corps est distincte des numéros physiques du PDF.

SHA-256 du PDF effectivement relu :
`61992f496ced93c76242031459511512044f6e330c1728979574b83715bc2e5e`.

Les 29 pages ont été rendues en PNG à 110 dpi avec `pdftoppm` et examinées
visuellement. La revue inclut couverture, sommaire, schéma, tableaux, figures,
bibliographie et annexes ; les pages du schéma et de l'annexe LLM ont aussi été
inspectées individuellement. Les chevauchements du premier schéma et les
débordements de chemins/empreintes ont été corrigés. L'annexe E tient désormais
sur une page dédiée, sans paragraphe isolé sur une dernière page presque vide.
Les fichiers de revue restent dans `.cache/phase9d/`, ignoré par Git ; les
journaux de compilation restent dans `report_latex/_build/`.

## Validations

| Contrôle | Résultat |
|---|---|
| `python -B report_latex/verify_latex_project.py` | PASS : 38 fichiers TeX atteignables, chemins locaux, 15 PNG, 14 tableaux, labels et 17 citations |
| Sources/copies/cellules et annexe LLM | PASS : 73 SHA de sources, figures exactes, présentations conformes aux CSV et extrait B fidèle |
| `python -m ruff check report_latex` | PASS ; limité aux nouveaux scripts Python |
| `python -m pytest tests/test_final_deliverables.py tests/test_full_reproduction.py tests/test_llm_package.py` | **172 passed**, 7,86 s |
| `git diff --check` et contrôle du diff indexé | PASS |
| Intégrité des fichiers préexistants | **366 fichiers suivis et 7 snapshots locaux inchangés**, comparaison SHA-256 avant/après |
| Rapports Word/PDF, prévisions et protocoles officiels | Intacts ; aucune sortie scientifique remplacée |

Les tests ciblent les contrats de livrables, d'isolation et de protection LLM,
sans lancer la chaîne scientifique historique. Aucun nouveau jeu de tests
statistiques, téléchargement de marché ou entraînement de modèle n'est exécuté.
La suite pytest complète n'a pas été relancée pour cette évolution documentaire.

## Limites et usage ultérieur

- La compilation est vérifiée dans cet environnement Windows ; un autre moteur
  ou une distribution différente peut modifier la pagination et demande une revue.
- Le projet TeX utilise exclusivement des chemins locaux relatifs, PNG et BibTeX.
  La compilation directe de `main.tex` ne nécessite pas les scripts Python/R.
  Les contrôles SHA et la préparation documentaire requièrent le dépôt complet.
- L'utilisateur a réellement importé et compilé le projet initial dans Prism AI,
  avec **29 pages affichées**, selon son retour dans la mission corrective.
  Cette preuve concerne la version initiale ; elle ne valide pas toutes les
  pages après les modifications ultérieures ni le fonctionnement collaboratif.
- Les champs de couverture restent à compléter avant remise ; les autres
  limites scientifiques sont celles exposées dans les résultats gelés et 9C3.

Seuls `report_latex/` et ce document sont ajoutés au commit de Phase 9D.
`main` reste au point de départ ci-dessus. Aucune publication, PR, fusion ou
création de tag n'est effectuée dans cette mission.


## Revue corrective finale — 10 octobre 2026

Cette révision répond à la mission pédagogique finale sur `feature/latex-report`.
Aucun entraînement, aucune phase statistique, aucune génération LLM ni accès
de scoring TEST n'a été relancé. Les résultats et décisions gelés sont conservés.

### Compléments scientifiques documentaires

- Chapitre 4 : lecture des quatre panneaux STL NVDA, équation additive,
  tendance dominante, faible amplitude saisonnière variable et pics résiduels.
  L'interprétation s'appuie sur la figure réellement examinée et les diagnostics
  Phase 2 (ADF/KPSS, rendements au carré, extrêmes et jours de semaine).
  Période de cinq séances imposée, jours fériés, filtres bilatéraux et absence de
  preuve de cycle stable expliquent pourquoi STL ne justifie pas SARIMA.
- Annexe A : copie exacte de `nvda_log_price_stl_train.png`, figure 10,
  page physique 26 ; quatre panneaux, échelles, unité, périmètre et source conservés.
- Chapitre 4 / annexe B : `rolling_correlations_60d.png`, figure 13,
  page physique 28. Moyennes TRAIN 0,669 / 0,796 / 0,738 et plages
  [0,154 ; 0,936] / [0,506 ; 0,956] / [0,348 ; 0,943], arrondies à trois
  décimales depuis `phase2_rolling_correlation_summary.csv`. Fenêtres passées
  de 60 séances, chevauchement et absence d'identification causale explicités.
- Chapitre 8 : `tables/neural_validation.tex`, tableau 9, page physique 17,
  compare Naive, LSTM C et GRU C à h=5/10. RMSE et MAE en USD ajustés, 561
  prévisions par candidat/horizon, valeurs arrondies à trois décimales depuis
  `phase6_validation_metrics_summary.csv`. Validation sur trois folds externes
  dans TRAIN, distincte de la loss d'arrêt et du TEST Phase 7 (211 origines).
- Les courbes LSTM/GRU existantes sont déplacées en annexe F, page 33,
  avec leurs légendes, unités, sources et références conservées.
- Chapitre 10 : gain de clarté documentaire, absence de gain de temps quantifié,
  contrôle humain nécessaire et limites de l'interprétation financière simulée.
  Aucune conclusion financière ni métrique nouvelle n'est introduite.

### Paquet LLM et provenance

Les quatre fichiers complets accompagnent désormais le dossier autonome :

- `report_latex/documents/llm/prompts/phase8_official_llm_prompt.md`
- `report_latex/documents/llm/responses/phase8_official_llm_response.md`
- `report_latex/documents/llm/human_analysis/phase8_human_vs_llm_comparison.md`
- `report_latex/documents/llm/human_analysis/phase8_hallucination_audit.csv`

Copies identiques octet par octet aux originaux ; le manifeste conserve leurs
sources, destinations et SHA-256. Il couvre maintenant **80 sources**, 17 PNG,
15 tableaux composés depuis les CSV et les quatre copies LLM intégrales.
La réponse officielle garde le SHA-256
`eecb0de3e0dd8e152e93db70ff71f9dad87024b7b2f3e1bee1ede05225f6f3b4`.
L'extrait B affiché en annexe E est également vérifié sans correction du texte.
La remise doit inclure tout `report_latex/` sans `_build/`, et non le PDF seul.
Le rafraîchissement documentaire refuse les changements des sources déjà gelées.

### Pagination, rendu et Prism

| Version | Total physique | Hors annexes | Annexes |
|---|---:|---:|---:|
| Avant correction (MiKTeX et retour utilisateur Prism) | 29 | 25 | 4 |
| Après correction (MiKTeX, PDF final) | 33 | 25 | 8 |

Convention inchangée : couverture, sommaire, résumé et bibliographie inclus
dans les 25 pages hors annexes ; corps scientifique pages physiques 4–24,
bibliographie page 25, annexes pages 26–33. L'exigence de 15–25 pages hors
annexes est respectée sans modifier les résultats. Les chemins préfèrent les
coupures aux séparateurs ; les empreintes disposent d'une macro distincte.
Les cinq tableaux déjà présents retouchés conservent exactement leurs cellules
et ne changent que la composition des chemins sources. Les attributs Git locaux
déclarent les PDF/PNG binaires pour préserver leurs octets. Les copies LLM
conservent leurs fins de ligne originales (dont CRLF) et leurs lignes finales ;
le contrôle Git reconnaît ces conventions uniquement pour ces copies fidèles.

Compilation finale : pdfLaTeX, BibTeX et deux nouvelles passes pdfLaTeX,
quatre codes de retour zéro, **aucun Overfull**, référence/citation non résolue
ou caractère manquant. Les 33 pages ont été rendues à 110 dpi et examinées
visuellement ; les nouvelles figures, le tableau TRAIN et les annexes sont lisibles.
Après la dernière correction de la mention Prism au chapitre 11, les 33 pages
ont été rendues à nouveau : seule la page 23 change, et elle est relue.

SHA-256 du PDF final contrôlé : `d0e00bce511136d34f35d478efdbc04b010fb402d7d5097e9427e11d4604bb41`.

L'utilisateur a réellement importé et compilé le projet dans **Prism AI**,
avec **29 pages affichées** avant cette correction. Ce retour est reconnu
dans le README, le chapitre 11 et l'audit ; il ne certifie pas les 33 pages
de cette nouvelle révision dans Prism. Un réimport, une compilation et une
relecture dans Prism restent à effectuer ; aucune validation future des pages
ou du travail collaboratif n'est revendiquée.

### Vérifications finales

| Contrôle | Résultat |
|---|---|
| Vérificateur LaTeX | PASS : 40 fichiers TeX atteignables, 17 PNG, 15 tableaux, 17 références citées, labels résolus |
| Chiffres et sources | PASS : affichages identiques aux CSV gelés, arrondis déclarés, unités/périmètres/sources présents |
| LLM | PASS : quatre copies intégrales exactes, originaux et extrait B intacts |
| Ruff sur `report_latex` | PASS |
| Tests livrables, reproduction isolée, LLM et rapport | **194 passed**, 36,07 s |
| `git diff --check` | PASS, y compris contrôle du diff indexé avant commit |
| Intégrité avant/après | **373 fichiers protégés inchangés**, y compris les snapshots locaux, les sources historiques, résultats et rapports de référence |

Commande pytest exécutée :
`python -m pytest tests/test_final_deliverables.py tests/test_full_reproduction.py tests/test_llm_package.py tests/test_final_report.py -q`.
Ces tests ciblent les contrats documentaires et l'isolation ; aucune phase
scientifique historique n'a été exécutée. La suite complète n'a pas été relancée.

### Fichiers de cette révision

33 fichiers ajoutés ou modifiés ; liste exacte :

- `docs/phase9d_latex_report.md`
- `report_latex/.gitattributes`
- `report_latex/README.md`
- `report_latex/appendices/A_univariate.tex`
- `report_latex/appendices/B_multivariate.tex`
- `report_latex/appendices/C_specifications.tex`
- `report_latex/appendices/D_artifacts.tex`
- `report_latex/appendices/E_llm.tex`
- `report_latex/appendices/F_neural_training.tex`
- `report_latex/chapters/04_eda_stationarity.tex`
- `report_latex/chapters/07_garch.tex`
- `report_latex/chapters/08_lstm_gru.tex`
- `report_latex/chapters/09_final_evaluation.tex`
- `report_latex/chapters/10_llm_analysis.tex`
- `report_latex/chapters/11_reproducibility.tex`
- `report_latex/documents/llm/human_analysis/phase8_hallucination_audit.csv`
- `report_latex/documents/llm/human_analysis/phase8_human_vs_llm_comparison.md`
- `report_latex/documents/llm/prompts/phase8_official_llm_prompt.md`
- `report_latex/documents/llm/responses/phase8_official_llm_response.md`
- `report_latex/figures/nvda_log_price_stl_train.png`
- `report_latex/figures/rolling_correlations_60d.png`
- `report_latex/main.tex`
- `report_latex/preamble.tex`
- `report_latex/prepare_assets.py`
- `report_latex/rapport_final_latex.pdf`
- `report_latex/sources_manifest.json`
- `report_latex/tables/arima_diagnostics.tex`
- `report_latex/tables/arima_validation.tex`
- `report_latex/tables/neural_comparison.tex`
- `report_latex/tables/neural_validation.tex`
- `report_latex/tables/recommendation.tex`
- `report_latex/tables/var_johansen.tex`
- `report_latex/verify_latex_project.py`

### Limites et Git

Les champs d'équipe, enseignant et date de couverture restent à compléter.
Le PDF officiel du cahier des charges absent du dépôt n'a pas fait l'objet
d'une certification indépendante exhaustive ; la conformité vérifiée ici porte
sur les exigences transmises dans cette mission. Les limites scientifiques
et l'état FULL sur machine vierge restent ceux du dossier gelé.

Branche : `feature/latex-report`. Message du commit local :
`docs: strengthen LaTeX EDA and model interpretation`.
Aucun push, aucune PR, fusion ou création de tag dans cette mission.
