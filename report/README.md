# Rapport scientifique final — Phase 9B

Le rapport en français présente les résultats gelés des Phases 1–8, leur protocole et leurs limites. Le modèle final de prévision de prix reste **Naive**.

- [rapport_final.docx](rapport_final.docx) : livrable principal Word, texte et équations éditables, tableaux natifs, figures PNG historiques.
- [rapport_final.pdf](rapport_final.pdf) : version rendue par Microsoft Word, destinée à la lecture et au contrôle de pagination.
- [rapport_final.md](rapport_final.md) : source canonique éditable ; conserver sa cohérence avec les deux exports.
- [preparation_soutenance.md](preparation_soutenance.md) : quinze questions et réponses avec sources internes.
- [Audit du rapport](../docs/phase9b_report_audit.md), [pagination et empreintes](../docs/phase9b_render_audit.json), [traçabilité des résultats](../docs/phase9b_results_traceability.csv).

Le document compte **30 pages rendues** : 3 de couverture/sommaire, **21 de corps avec références**, 6 d’annexes. Il compte donc **24 pages hors annexes**, couverture et sommaire inclus. Il comprend dix chapitres, dix-sept références externes, neuf tableaux, dix figures principales et cinq figures en annexes. L’annexe E reproduit intégralement la section B originale du LLM, avec son identité et sa provenance. Les figures couvrant toute la période sont explicitement descriptives ; les décisions de modélisation reposent sur TRAIN. Les champs de l’équipe, de l’enseignant et de la date restent clairement à compléter par l’équipe avant remise.

Le notebook Phase 9A est un mode **FAST** de vérification des artefacts. La reproduction intégrale **FULL** sur machine vierge reste **PARTIAL**, non exécutée ; le plan minimal figure dans la discussion et l’annexe D, avec les prérequis et la protection de Phase 7 et du LLM. Le PDF officiel du cahier des charges n’était pas intégré au dépôt lors de l’audit automatisé ; aucune vérification indépendante exhaustive de ce PDF n’est revendiquée. Cela ne constitue pas un livrable scientifique obligatoire manquant.

## Réédition documentaire

Depuis la racine du dépôt, avec les outils disponibles localement :

```powershell
.venv/Scripts/python.exe report/build_report.py
powershell -NoProfile -ExecutionPolicy Bypass -File report/render_report_windows.ps1
& 'C:/Program Files/Python312/python.exe' report/audit_report.py
```

Le builder OOXML n’utilise que la bibliothèque standard et les CSV archivés. `--refresh-tables` redispose leurs valeurs et met à jour la traçabilité ; ce n’est pas un recalcul scientifique. La conversion nécessite Word installé et utilisable. L’inspection PDF utilise le package `pypdf` déjà présent dans le Python système de la machine de rédaction ; adapter ce chemin sur une autre machine. Les outils documentaires ne font pas partie des packages scientifiques. Aucune dépendance n’a été installée pour cette livraison.

Après chaque réédition, relire le rendu, vérifier les pages hors annexes, refaire les empreintes et les contrôles :

```powershell
python -m ruff check .
python -m pytest
git diff --check
git status
```

Les tests du rapport lisent les fichiers et les sources gelées, sans entraîner de modèle. Le script d’audit remet le statut de relecture visuelle à `PENDING` : ne déclarer `PASS` qu’après contrôle de toutes les pages. La livraison Phase 9B ne modifie ni les sorties historiques, ni les protocoles, ni la réponse officielle LLM, ni le notebook Phase 9A.
