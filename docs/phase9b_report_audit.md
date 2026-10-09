# Audit du rapport scientifique final — Phase 9B

## Périmètre et livraison

Le rapport est rédigé en français à partir des résultats gelés des Phases 1–8, sur la branche `feature/final-report`, issue du commit `658794d` et du tag de référence `v0.12.0-phase9a`. Aucun modèle n’a été entraîné ou réestimé pour cette phase. Le modèle final demeure Naive. La checklist Phase 9A reste un audit historique ; le rapport est livré ici dans la Phase 9B.

Livrables :

- `report/rapport_final.md` : source canonique ;
- `report/rapport_final.docx` : principal Word éditable ;
- `report/rapport_final.pdf` : export Word pour lecture et contrôle ;
- `report/README.md` : lecture, réédition et contrôles ;
- `report/preparation_soutenance.md` : quinze réponses courtes sourcées ;
- `docs/phase9b_results_traceability.csv` : cellules affichées, résultats quantitatifs et décisions reliés aux sources ;
- `docs/phase9b_render_audit.json` : pagination réelle, sections et SHA-256 des exports ;
- `docs/phase9b_frozen_references.json` : protection supplémentaire du manifeste et du notebook Phase 9A ;
- `tests/test_final_report.py` : tests documentaires et de préservation ;
- `report/build_report.py`, `report/report_sources.py`, `report/render_report_windows.ps1`, `report/audit_report.py` : outils documentaires locaux, sans import de modèle scientifique ni écriture historique.

## Contenu et preuves scientifiques

Les dix chapitres couvrent introduction, acquisition/préparation, EDA/stationnarité, ARIMA/validation, VAR/Johansen, ARCH/GARCH, LSTM/GRU, évaluation finale, audit LLM, discussion/limites/conclusion. Seize références méthodologiques externes ont été consultées sur des sources primaires ; les résultats viennent des fichiers internes, pas des pages web.

Neuf tableaux natifs correspondent aux données, distributions TRAIN, stationnarité, Granger, paramètres GARCH, métriques finales, DM, audit LLM et coûts. Le tableau final unique contient les dix lignes officielles des cinq modèles à h5 et h10. Les valeurs sont lues dans les CSV avec arrondi d’affichage explicite ; aucune nouvelle prévision n’est produite. La traçabilité contient **167 entrées** et distingue les cellules numériques exactes, comptages et somme des durées CPU des rapprochements documentaires.

Les quinze PNG de `docs/final_figure_selection.md` sont utilisés sans modification : dix dans le corps et cinq en annexes. Chaque légende précise fichier, unités, période et périmètre. Les graphiques descriptifs couvrant TEST ne deviennent pas des preuves de sélection TRAIN. Les interprétations distinguent corrélation, précédence prédictive, identification récursive et causalité économique.

Les conclusions ont été confrontées aux documents, protocoles, locks et tables correspondants :

- d=1 est soutenu sur TRAIN ; non-normalité et effets ARCH restent visibles ;
- le lock de Phase 3B est Naive ; ARIMA(2,1,2) avec drift est un challenger pédagogique explicitement pré-déclaré en Phase 7, sans changement du lock ;
- VAR(9) résulte du gate de diagnostics, malgré les critères proposant 1 ; rang Johansen nul, donc pas de VECM ;
- le choix GARCH Normal ne valide pas des queues gaussiennes et ne transforme pas sigma en prix ;
- LSTM/GRU conservent leurs résultats défavorables et les limites de seed/grille/extrapolation ;
- ARIMA a un léger avantage RMSE à h10 mais échoue à la règle complète : gain moyen insuffisant, MAE défavorable, pas de soutien DM ; Naive reste final ;
- les 35 affirmations LLM auditées sont soutenues, sans audit indépendant aveugle ni fiabilité générale démontrée. Les métadonnées exactes de génération manquent ; la réponse intégrale reste inchangée.

## Reproduction et protection

FAST vérifie les artefacts et recalcule arithmétiquement les métriques depuis les prédictions gelées. Il ne reproduit pas l’étude par réestimation complète. FULL sur machine vierge reste **PARTIAL**, non démontré et non exécuté ici.

Le rapport documente un notebook FULL distinct, orchestrant les vrais scripts Python/R dans un clone isolé. Prérequis : snapshots originaux vérifiés ou téléchargement contrôlé et comparaison aux manifestes ; packages Python/R listés ; TensorFlow CPU compatible ; historique et protocoles authentiques ; sortie Phase 7 active vierge dans la copie isolée ; journaux, durées et empreintes. La vingtaine de minutes neuronales archivée n’est pas une estimation de tout FULL. Les prédictions officielles et la réponse LLM doivent rester protégées et ne pas être régénérées ou écrasées pour la rédaction.

Le PDF intégral officiel du cahier des charges est absent : cela limite la certification documentaire exhaustive, sans constituer un livrable scientifique obligatoire manquant. Les exigences transmises sont appliquées explicitement.

Le manifeste Phase 9A protège 305 fichiers historiques par SHA-256 ; les tests acceptent leurs bytes de capture ou leur blob Git exact pour la portabilité des fins de ligne. Le notebook Phase 9A et son manifeste sont également comparés au tag `v0.12.0-phase9a`, puis protégés par les empreintes additionnelles. Les sept snapshots locaux disponibles sont comparés à l’audit de checksums historique. L’empreinte de la réponse LLM officielle est vérifiée explicitement. Les sorties Phase 7, protocoles et scripts historiques restent inchangés.

## Production et contrôle du rendu

Le DOCX est construit en OOXML avec la bibliothèque standard, avec A4, marges de 2,5 cm, Times New Roman 11 pt, interligne 1,15, titres numérotés, quatre équations natives, tableaux et figures. Le titre anglais demandé est conservé. Les noms et la date de remise restent à compléter, sans identités inventées.

Le helper `render_docx.py` du skill documents n’est pas utilisable localement : python-docx/pdf2image et LibreOffice sont absents. Aucun package n’a été installé. Le remplacement utilise Microsoft Word déjà installé, met à jour le sommaire et exporte le PDF ; le Python système disposant de pypdf inspecte indépendamment pages et titres. Poppler/MiKTeX déjà présent fournit les PNG de contrôle, avec initialisation explicite de son profil local, sans téléchargement de package.

Les défauts du conteneur OOXML initial et les références débordant sur des pages presque vides ont été corrigés avant livraison. La pagination enregistrée dans `docs/phase9b_render_audit.json` est issue du document Word sauvegardé et du PDF exporté, pas d’une estimation du Markdown : **28 pages réelles**, dont 3 de couverture/sommaire, **21 de corps avec références** (19 de chapitres scientifiques, 2 de références), puis 4 d’annexes. Toutes les 28 pages finales ont été inspectées en PNG à leur résolution d’origine, 120 dpi : **PASS**, sans texte tronqué, chevauchement, page débordée presque vide, figure ou équation manquante. Les panneaux IRF/résidus restent denses et méritent une vérification de lisibilité à l’impression par l’équipe. Les pages examinées sont enregistrées dans l’audit JSON ; les images de contrôle sont temporaires, sans être des livrables.

## Validation finale

Les contrôles finaux ont été exécutés avec le Python 3.12.3 du venv du projet :

| Contrôle | Résultat |
| --- | --- |
| `python -m ruff check .` | PASS — All checks passed |
| `python -m pytest` | PASS — 368 tests, dont 20 Phase 9B, en 31,29 s |
| Avertissements pytest | 4 FutureWarning existants de statsmodels/acorr_lm dans les tests ARIMA ; aucun échec |
| `git diff --check` | PASS — aucun défaut d’espacement |
| `git status` avant commit | 14 fichiers Phase 9B uniquement ; aucun fichier scientifique historique modifié |
| Référence `main` | Inchangée : `658794d5cfabe336a261b1986505c3d4374c2661` |
| Rendu et pagination | PASS — 28 pages Word/PDF concordantes, 21 de corps avec références, 28 pages relues |
| Sources et préservation | PASS — neuf tableaux Word/Markdown conformes aux CSV, quantités clés de prose vérifiées, 15 PNG identiques, 167 entrées traçables, 305 fichiers historiques + notebook/manifeste Phase 9A + 7 snapshots locaux intacts |

Les tests utilisent des fixtures et contrôles de fichiers ; ils ne relancent pas les modèles scientifiques sur les données officielles et n’exécutent pas FULL. Le commit local autorisé porte le message `docs: add final scientific report`. Son hash et le statut Git après commit sont fournis dans le compte rendu de livraison.

## Relecture de l’équipe avant remise

Compléter la couverture. Relire particulièrement d=1, le passage du lock Naive au challenger ARIMA final pré-déclaré, VAR(9) plutôt que 1, l’absence de VECM, Normal plutôt que Student-t, les pertes neuronales, la règle finale Naive, le non-rejet DM, les limites du LLM et le caractère PARTIAL de FULL. Vérifier la lisibilité des panneaux multivariés au format de remise et l’accès aux fichiers internes cités. Les réponses d’oral sont dans `report/preparation_soutenance.md`.

La livraison est limitée à la Phase 9B avec commit local ; aucune publication GitHub, PR, modification de main, merge ou création de tag n’est effectuée.
