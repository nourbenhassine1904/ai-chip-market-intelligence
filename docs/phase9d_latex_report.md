# Phase 9D — Rapport LaTeX modulaire

Audit de création finalisé le **10 octobre 2026** sur `feature/latex-report`.
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
- La structure modulaire permet une adaptation ultérieure dans Prism AI.
  Aucun import ou fonctionnement du service Prism n'a été testé.
- Les champs de couverture restent à compléter avant remise ; les autres
  limites scientifiques sont celles exposées dans les résultats gelés et 9C3.

Seuls `report_latex/` et ce document sont ajoutés au commit de Phase 9D.
`main` reste au point de départ ci-dessus. Aucune publication, PR, fusion ou
création de tag n'est effectuée dans cette mission.
