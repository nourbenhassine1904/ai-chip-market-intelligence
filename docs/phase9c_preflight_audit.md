# Audit réel Phase 9C1 — PREFLIGHT

Branche : `feature/full-reproduction`. Base scientifique : main et tag
`v0.13.0-phase9b`, commit `e3cd311e4177807c2d422e74f3290d93cef35dab`.
La mission prépare seulement FULL. Son statut §8.3 reste **PARTIAL** ; aucune
estimation classique/GARCH sur les snapshots de l’étude, grille LSTM/GRU,
Phase 7 ni requête Yahoo n’a été lancée. Les tests utilisent des fixtures.

## Inspection et protections

Les quatre guides/checklist demandés et les protocoles 6/7 ont été lus.
Tous les scripts de `python/` et `r/` ont été inventoriés et inspectés pour leurs
entrées, écritures, options et ordre ; Python est parsé sans import scientifique,
et les cinq fichiers R sont parsés sans `source`. Le placeholder R EDA n’est pas
compté comme une implémentation. Les vrais flags des synthèses sont validés par AST.
`05_lstm_gru.py` réalise 18 fits + deux refits ; `06_evaluation.py` refuse les
prévisions existantes et impose gate/protocoles puis gel TRAIN avant lecture TEST.

Le clone indépendant `C:\Temp\ai-chip-full-9c1-e3cd311` est hors OneDrive, avec
historique Git complet et HEAD détaché au point scientifique. La référence reste
le checkout original de l’utilisateur. Le manifeste `state.json` contient leurs
chemins explicites, source_revision et les SHA des **358 fichiers suivis**.
Toutes les sorties historiques, protocoles, FAST, rapport, réponse officielle
et recommandation Naive sont préservés. Aucun snapshot/poids n’est suivi par Git.

## Résultat du PREFLIGHT réel

**PREFLIGHT PASS** : les sept snapshots dans la référence et leur copie isolée
correspondent exactement aux SHA historiques détaillés dans
[la préparation FULL](phase9c_full_reproduction.md#entrées-strictes).
TEST est haché pour intégrité uniquement, sans parsing d’observations.
Les protocoles 6/7 sont cohérents et les bytes du protocole Phase 7 correspondent
au commit pré-déclaré `1e5ad76c6834f4e24fee825c894261597c94c917`.

Python isolé : `C:\Temp\ai-chip-full-9c1-e3cd311\.venv\Scripts\python.exe`,
version 3.12.3, TensorFlow 2.21.0, CPU seulement. nbformat 5.11.1, nbclient 0.11.0,
ipykernel 7.4.0. `pip check` PASS. Rscript 4.5.2, packages forecast 9.0.2,
tseries 0.10.63, FinTS 0.4.9, vars 1.6.1, urca 1.3.4, rugarch 1.5.6.
Toutes les versions Python observées figurent dans le guide et l’audit JSON.

Le premier PREFLIGHT a correctement arrêté sur `Missing forecast` : la copie
initiale `.cache/R-library` ne contenait pas les packages de la bibliothèque
personnelle. Ceux-ci ont ensuite été copiés explicitement depuis
`C:\Users\nourb\AppData\Local\R\win-library\4.5` vers le sandbox. La reprise
a passé les six vérifications. Aucune installation réseau ou silencieuse.
Les warnings R de locale `C.UTF-8` sont visibles dans stderr ; ils n’ont pas
empêché les contrôles avec code de sortie zéro.

La réponse LLM garde SHA256
`eecb0de3e0dd8e152e93db70ff71f9dad87024b7b2f3e1bee1ede05225f6f3b4`.
Les 35 identifiants audités sont uniques, leurs affirmations sont présentes dans
la réponse originale, marquées supported/TRUE et reliées à des fichiers existants.
Ce contrôle documentaire ne reproduit pas la génération et ne certifie pas de
nouvelles métriques scientifiques.

## Notebook et tests

Le notebook canonique contient cinq cellules Python, JSON nbformat valide et
syntaxe Python valide, sans outputs stockés. Defaults PREFLIGHT, autorisation FULL
fausse, préparation et download désactivés. L’exécuteur utilise nbclient et un
kernel temporaire pointant explicitement sur le Python du sandbox, sans enregistrement
global. La copie exécutée et son audit sont dans `.cache/phase9c/` du sandbox.

Notebook réel : **PASS**, cinq cellules exécutées avec nbclient et le Python
isolé, sans erreur de cellule ; kernel fermé explicitement après exécution.
Les 358 fichiers protégés et sept snapshots de la référence sont inchangés.
L’audit `notebook_execution.json` enregistre les SHA de la source canonique et
de l’orchestrateur, le chemin du kernel et `full_executed=false`. Aucun output
n’est ajouté au notebook source. Un warning local du kernel TCP est visible ;
il n’a pas empêché l’exécution et ne modifie pas ces résultats.

Ruff : **PASS**, `All checks passed`. Suite complète : **402 tests PASS**,
dont **32 Phase 9C**, en 29,15 s. Quatre FutureWarning statsmodels/acorr_lm
préexistants ; aucun échec. `git diff --check` et `git diff --cached --check`
**PASS**. L’index contient exactement les cinq nouveaux fichiers Phase 9C,
aucune modification ou suppression de fichier scientifique historique.

Empreintes des sources effectivement exécutées en PREFLIGHT :

- notebook : `c3b458069529272c4059ec7fea242896e84832c6b35332d4d1f9d6d98c177581` ;
- orchestrateur : `84dc27d3b53c84667ce7b7947b01c25874ad771d1957b515a244577c5edee8e8`.

Les logs ne contiennent que les quatre probes Python/TensorFlow, pip, packages R
et parsing R. Absence vérifiée de `.cache/phase7/protocol_gate.json` et de
`.cache/phase9c/historical_outputs` dans le sandbox : aucune préparation active
de Phase 7 ou archival scientifique réelle n’a été lancée.

Les tests de sécurité couvrent racines identiques/imbriquées, traversal et jonction
vers référence, snapshots absents/divergents, altération de fichiers protégés ou
de l’identité du sandbox, protocoles incohérents, commandes hors allowlist,
prévisions/runtime/gate historiques dans l’espace actif et refus de Phase 7 avant
Phase 6. Des fixtures Git testent aussi **la fonction authentique** du vérificateur :
création d’un gate neuf sur arbre propre, rejet d’un arbre sale et d’un protocole
altéré, sans donnée, modèle ou TEST. Ces gates de tests ne sont pas un nouveau gate
de reproduction scientifique et ne sont pas présentés comme tels.

## Travail restant et limites

Les étapes classiques, 18 fits et deux refits neuronaux sont préparés, pas exécutés.
La nouvelle Phase 7 prévoit archivage des seules copies, checkpoint Git local TRAIN,
gate authentique et vraie évaluation avec provenance des caches/reconstructions.
Cette procédure complète n’a pas été exercée avec de nouveaux modèles pendant 9C1.
Les anciennes prévisions sont encore dans le clone **avant** son futur archivage,
et ne sont pas présentées comme de nouveaux résultats. Aucun gate réel de Phase 7
n’a été créé ; seules ses protections sont testées en fixtures.

Pas de blocage d’entrée ou de dépendance constaté après correction. Les blocages
possibles du futur run restent explicites : données révisées, locks différents,
epochs différents, provenance incompatible, échec de convergence ou du gate.
Ils entraîneront STOP sans changer les hashes ni retuner sur le holdout.
La copie de packages déjà installés prouve la disponibilité locale isolée,
pas une installation réussie sur une machine vierge. Durée totale et équivalence
numérique FULL ne sont pas démontrées. Le rapport, FAST, checklist Phase 9A et les
résultats gelés sont inchangés ; ce nouvel audit ne remplace pas leurs preuves.

La livraison 9C1 comprend uniquement cinq nouveaux fichiers : notebook FULL,
orchestrateur, tests, guide et présent audit. Commit local seulement, aucun push,
PR, merge, tag ou changement de main. Le hash final est fourni dans le compte rendu.

Un fichier verrou Word non suivi `report/~$pport_final.docx` est apparu pendant
la mission ; il est laissé en place et exclu du commit. Aucun fichier du rapport
suivi n’est modifié. Un contrôle Git du sandbox depuis l’identité restreinte du
tool a été rejeté pour ownership ; il a été repris avec l’identité propriétaire,
sans modification globale de `safe.directory` ni désactivation de ce garde-fou.
