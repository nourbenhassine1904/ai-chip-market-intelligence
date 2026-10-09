# Phase 9C — reproduction FULL isolée : préparation et audit d’exécution

La reproduction intégrale §8.3 reste **PARTIAL**. La préparation 9C1 avait
uniquement exécuté PREFLIGHT. Le run FULL ultérieur, audité en 9C3 sans relance,
a réellement exécuté les estimations classiques, la grille neuronale et
l’évaluation Phase 7 dans le sandbox préparé : **PIPELINE_EXECUTED**,
**PARTIAL_PENDING_CLEAN_MACHINE_REVIEW**, aucun `full_failure.json`.
Cela démontre le runner dans cet environnement ; la machine vierge et le notebook
exécuté intégralement en mode FULL restent à démontrer.
Le notebook FAST, le rapport final et la recommandation officielle Naive restent
inchangés. Les audits Phase 9A sont conservés comme preuves historiques.

L’[audit d’exécution 9C3](phase9c_full_execution_audit.md), le
[registre des 210 fichiers](phase9c_full_differences.csv) et le
[résumé traçable](phase9c_full_summary.json) documentent **116 fichiers identiques,
94 différents** : 64 fins de ligne, 20 durées/provenance, 4 images, 1 journal de
réestimation et 5 fichiers avec valeurs scientifiques différentes. Les décisions
classiques, DM/Holm et Naive sont conservées, mais les prévisions GRU reconstruites
ne sont pas identiques. Aucun résultat officiel n’est remplacé par ce run.

## Sources et isolation

Point scientifique : `v0.13.0-phase9b`, commit
`e3cd311e4177807c2d422e74f3290d93cef35dab`, identique à main au démarrage.
Développement : `feature/full-reproduction`. Les sources de tous les scripts
Python/R sont inventoriées (SHA256, lignes, options CLI Python réelles) dans
`.cache/phase9c/source_inventory.json`. `r/01_data_eda.R` est un placeholder,
parsable mais exclu du pipeline ; EDA canonique est Python.

Le notebook [FULL](../notebooks/AI_Chip_Market_Intelligence_FULL.ipynb) appelle
uniquement les fonctions de [l’orchestrateur](../python/09c_full_reproduction.py).
Celui-ci clone Git avec `--no-local --no-hardlinks`, conserve l’historique complet
et enregistre `reference_root`, `sandbox_root` et `source_revision`. Il refuse
les racines identiques ou imbriquées, un dossier sandbox préexistant lors de
sa création, les chemins absolus/traversants et les redirections par lien/jonction.
Les subprocess scientifiques utilisent exclusivement le cwd et les scripts du
sandbox, une liste fermée de commandes et le Python de son propre `.venv`.
FULL exige aussi que l’appelant ait `cwd=sandbox_root`.

Sandbox préparé pour cette mission : `C:\Temp\ai-chip-full-9c1-e3cd311`, hors
OneDrive. Son manifeste `state.json` protège les SHA256 des **358 fichiers suivis
du point scientifique**, dont toutes les sorties 1–8, les protocoles, FAST et
les exports du rapport. Les sept snapshots sont également recontrôlés.
Avant/après opérations et entre phases, toute mutation de la référence arrête
le workflow. Aucun cache neuronal ni ancien gate Phase 7 n’est copié.

Les journaux techniques, états, manifests, kernels temporaires et notebook exécuté
restent dans `sandbox_root/.cache/phase9c/`. Un `.gitignore` interne `*` ignore
ce répertoire sans modifier le `.gitignore` scientifique. La référence contient
uniquement du scratch technique ignoré dans son propre `.cache/phase9c/`.
Les acquisitions/restaurations et tout nouveau résultat scientifique restent
dans le sandbox ; rien ne remplace les livrables officiels.

## Entrées strictes

Les sept snapshots sont recherchés uniquement aux chemins du checkout original
fourni. Les SHA attendus viennent de
`outputs/tables/phase9a_data_checksum_audit.csv`, contrôlés avec les protocoles
TRAIN/TEST originaux. Aucune normalisation de fins de ligne ou correction de
hash n’est admise pour les données. Le PREFLIGHT lit les bytes de TEST pour
les hacher, sans parser ses observations ni calculer de statistique dessus.

| Snapshot | SHA256 historique attendu |
| --- | --- |
| `data/raw/NVDA_raw.csv` | `ce0be7475afb30081b9127580e87fe98a4de60c3d3ea73583b7a1455354fcdd5` |
| `data/raw/AMD_raw.csv` | `fcd5544f0ab3c134223fff66432ca980d903540b1d3ffe62371ac950f6bf8b97` |
| `data/raw/SOXX_raw.csv` | `7d4317ae33e89f8dc021037a4b7002964f17a43ef1a388218029dd63090e463e` |
| `data/processed/market_aligned.csv` | `e4f69e14cb46c797c6eb383c0f60ecc8b5d6a918ccd248288696f08557473b04` |
| `data/processed/market_features.csv` | `d64fe085b919bf20c4bf0fc372235cb4f42a2b45d6815883573ec0746aeff00a` |
| `data/processed/market_train.csv` | `c3651f95959a49d8d64c791a8d48443dd520b978c3887b8793256dfff76c8f1c` |
| `data/processed/market_test.csv` | `124ebdff5b37de4459fcd9738e8d8ad968b3f945b66b647310f741640fa55fe4` |

Un fichier absent ou divergent arrête la reproduction stricte avant estimation.
Les snapshots et poids ne sont jamais ajoutés à Git.

La voie par défaut restaure les snapshots originaux et conserve la provenance
historique de l’acquisition : elle ne prétend pas avoir effectué une nouvelle
requête Yahoo. `--controlled-download`, uniquement en FULL explicitement demandé,
exécute réellement `python/00_data_acquisition.py`, puis exige les SHA historiques
des trois raw. Un nouveau manifeste Yahoo cohérent ne suffit pas. Cette voie n’a
pas été utilisée ni testée avec un téléchargement pendant 9C1.

## Environnement et commandes de vérification

Python 3.12.x, TensorFlow **2.21.0**, CPU et tous les packages de
`requirements.txt`/`requirements-dev.txt` sont nécessaires ; aucun GPU n’est requis.
Rscript doit être fourni ou trouvé sur PATH, avec forecast, tseries, FinTS, vars,
urca et rugarch. Le code n’installe aucun package et n’appelle jamais pip install
ou install.packages. `--copy-environment` crée explicitement un venv neuf (pip
standard fourni par venv), puis copie les packages déjà installés de la référence
et sa bibliothèque R locale. `--copy-r-library` copie explicitement une autre
bibliothèque R installée. Ces copies ne sont pas une installation sur machine
vierge et ne prouvent pas la distribution autonome des dépendances.

Versions observées dans le sandbox :

| Composant | Version |
| --- | --- |
| Python | 3.12.3 |
| TensorFlow / dispositif | 2.21.0 / CPU uniquement |
| pandas / numpy / scipy | 3.0.6 / 2.5.3 / 1.18.1 |
| matplotlib / statsmodels | 3.11.2 / 0.15.0 |
| arch / pmdarima | 8.0.0 / 2.1.1 |
| yfinance / scikit-learn | 1.7.0 / 1.9.1 |
| nbformat / nbclient / ipykernel | 5.11.1 / 0.11.0 / 7.4.0 |
| R | 4.5.2 |
| forecast / tseries / FinTS | 9.0.2 / 0.10.63 / 0.4.9 |
| vars / urca / rugarch | 1.6.1 / 1.3.4 / 1.5.6 |

Le PREFLIGHT effectue un import TensorFlow et une requête des dispositifs, un
`python -m pip check`, des `requireNamespace`/`packageVersion` R, puis `parse()`
sur les cinq sources R. Il ne les source pas. Les commandes exactes, stdout,
stderr, codes de sortie et durées sont dans `.cache/phase9c/logs/`.
Les requirements existants restent partiellement non épinglés ; respecter leurs
plages (arch 8.x, pmdarima >=2.1.1,<3, nbformat 5.x, nbclient >=0.10,<1,
ipykernel >=6.29,<8) et comparer les versions aux tables historiques.
Seeds, CPU et opérations déterministes demandées ne garantissent pas des bytes
ou résultats numériquement identiques entre versions/CPUs. Les profils/temp/caches
du kernel et des subprocess sont dirigés dans le sandbox.

## Ordre scientifique préparé en 9C1, exécuté lors du FULL audité

Les 17 commandes scientifiques ci-dessous ont un journal de sortie 0 dans le
run FULL audité. Le contrôle LLM est interne au runner, documentaire et historique,
sans subprocess ni nouvelle génération. L’ordre et les preuves sont détaillés
dans l’audit 9C3 ; aucune commande scientifique n’a été relancée pendant 9C3.

1. Restauration vérifiée des sept originaux ; ou téléchargement contrôlé explicitement demandé.
2. `python python/01_data_preparation.py` ; SHA raw/canonique contre historique.
3. `python python/01_data_eda.py` ; SHA des sept fichiers contre historique.
4. `python python/02_arima.py` ; `Rscript r/02_arima.R` ;
   `python python/02_arima.py --compare-r` ; `python python/02_arima.py --summarize`.
5. `python python/02b_arima_validation.py` ; `Rscript r/02b_arima_validation.R` ;
   `python python/02b_arima_validation.py --summarize`.
6. `python python/03_var_vecm.py` ; `Rscript r/03_var_vecm.R` ;
   `python python/03_var_vecm.py --summarize`.
7. `python python/04_garch.py` ; `Rscript r/04_garch.R` ;
   `python python/04_garch.py --summarize`.
8. `python python/05_lstm_gru.py` : vraie grille A/B/C, LSTM/GRU, seed 42,
   trois folds chronologiques, scalers TRAIN-only, early stopping original,
   18 fits et deux refits. Les C historiques sont des résultats attendus,
   jamais des choix forcés : lock ou epochs différents => STOP.
9. Préparation Phase 7 décrite ci-dessous ; `python python/06_evaluation.py`,
   sans `--summarize`, donc vraie nouvelle prévision et audits.
10. Chargement documentaire de la réponse LLM historique, 35 affirmations
    vérifiées présentes dans le texte et audit, sources existantes ; aucune génération.

Les scripts Python 3A/3B peuvent faire une synthèse provisoire avant R ; la synthèse
finale suit toujours les deux nouvelles exécutions. Les anciennes sorties 3–7
sont archivées avant tout fit pour éviter une synthèse utilisant un ancien R.
Préparation/EDA construisent le split et les figures descriptives prévus par les
scripts originaux ; ce n’est pas un accès anticipé du nouvel évaluateur au TEST.
Les fits classiques et neuronaux utilisent exclusivement TRAIN. Les règles
historiques SARIMA/VECM/higher-GARCH restent intactes. Les nouveaux locks Phase
3B/4/5/6 doivent conserver les spécifications historiques ; sinon arrêt sans retuning.

## Nouvelle Phase 7 : garde-fous conservés

Avant la première estimation FULL, les sorties copiées `phase3_*` à `phase7_*`
et figures correspondantes sont déplacées, bytes conservés et hashés, dans
`.cache/phase9c/historical_outputs/`. La référence n’est jamais déplacée.
L’espace actif Phase 7 doit être vide, sans anciennes prédictions, runtime audit
ou `.cache/phase7/` gate. Aucune archive ni nouveau gate n’a été créé pour une
exécution scientifique réelle pendant 9C1.

Après les véritables 18 fits et deux refits de Phase 6, l’orchestrateur vérifie
les locks C (60/64/0.2, epochs 38/36) et leur cohérence ; il crée un **commit
local dans le sandbox seulement** des nouveaux résultats TRAIN et de l’archivage.
Le protocole original reste aux mêmes bytes et conserve son commit pré-déclaré
`1e5ad76c6834f4e24fee825c894261597c94c917`. Le working tree doit être propre.
L’orchestrateur appelle alors **`verify_protocol_commit` du véritable
`python/06_evaluation.py`**, sans construire lui-même un gate PASS. Celui-ci crée
un nouveau gate seulement en l’absence d’ancien cache et d’ancien runtime audit.
Le runner officiel effectue ensuite ses contrôles, fits/verrouillages TRAIN,
puis ouvre TEST uniquement avec `models_ready=True`.

Les poids/scalers fraîchement entraînés sont comparés aux hashes pré-déclarés
par le loader original. S’ils diffèrent, seule sa branche existante
`reconstructed_from_locked_specification` est autorisée : deux refits
supplémentaires C, 38/36 epochs, TRAIN-only, provenance déclarée dans le nouveau
`phase7_model_fit_log.csv`. Les anciens hashes ne sont pas changés, et ces poids
ne sont pas présentés comme ceux de l’étude. Des locks/provenances incompatibles
arrêtent l’exécution avant TEST ; aucune reconstruction ne les contourne.
Les anciens runtime audits restent archivés, jamais des preuves du nouveau run.

Les nouvelles prévisions, métriques, DM et audit du sandbox sont les sorties
du runner authentique. Comparaison finale : hashes byte-à-byte, écarts signés
MSE/RMSE/MAE/MAPE, provenance des poids et tolérance descriptive absolue
pré-déclarée `1e-6`. Cette tolérance ne garantit pas une équivalence scientifique.
Les 35 affirmations LLM restent un audit **historique**, pas une certification de
nouvelles valeurs ; les divergences sont affichées séparément. Naive demeure
la recommandation officielle du projet.

L’inspection ZIP/HDF5 9C3 montre que les refits Phase 6 ont des charges utiles
`model.weights.h5` identiques aux historiques. Leurs fichiers `.keras` diffèrent
par date de sauvegarde et identifiants d’objets sérialisés ; les SHA de fichiers
exigés par le loader Phase 7 ne correspondent donc pas. Les deux reconstructions
C ont eu lieu : LSTM retrouve les mêmes poids numériques, GRU diffère sur 12865
paramètres (maximum absolu 2.8312206268310547e-07). Le champ `cache_file_sha256`
du journal désigne le fichier Phase 6 examiné ; les SHA des fichiers Phase 7
effectivement utilisés sont donnés séparément dans l’audit et le JSON.
Quatre écarts GRU MSE/RMSE dépassent `1e-6`, les quatre écarts MAE/MAPE sont
inférieurs à ce seuil ; 304 prévisions et quatre lignes DM varient. Les décisions
restent identiques. La cause numérique précise reste non établie ; aucune
tolérance, seed ou configuration n’a été ajustée pour obtenir une correspondance.

## Commandes de préparation pour un futur essai distinct

Ces instructions sont conservées pour un essai ultérieur autorisé ; elles ne
sont pas à exécuter pendant l’audit 9C3. Préserver le sandbox déjà FULL et ses
archives/logs/poids. Après les nouveaux livrables 9C3, utiliser une révision locale
contenant ces documents : le tag scientifique ancien seul ne contient pas les
nouveaux fichiers et ne satisfait pas la liste fermée des copies préparées en 9C1.
Enregistrer le hash de la révision locale et le passer à chaque commande de ce
nouvel essai ; les sources scientifiques historiques sont inchangées.

Depuis la référence, pour **un nouveau chemin qui n’existe pas**, préparer sans fit :

```powershell
$Reference = (Get-Location).Path
$SourceRevision = (git rev-parse HEAD).Trim()
$Sandbox = 'C:\Temp\ai-chip-full-next'
$Rscript = 'C:\Program Files\R\R-4.5.2\bin\Rscript.exe'
.\.venv\Scripts\python.exe python/09c_full_reproduction.py --reference-root $Reference --sandbox-root $Sandbox --source-revision $SourceRevision --rscript $Rscript --mode PREFLIGHT --prepare --copy-environment
# Si les packages R sont dans la bibliothèque personnelle, copier explicitement :
.\.venv\Scripts\python.exe python/09c_full_reproduction.py --reference-root $Reference --sandbox-root $Sandbox --source-revision $SourceRevision --rscript $Rscript --mode PREFLIGHT --copy-r-library 'C:\Users\nourb\AppData\Local\R\win-library\4.5'
```

Le sandbox `C:\Temp\ai-chip-full-9c1-e3cd311` a désormais commencé et terminé
FULL : ne pas reprendre ses anciennes commandes PREFLIGHT/FULL. Le notebook
PREFLIGHT déjà exécuté reste une preuve de préparation, pas une preuve FULL.

Lors d’une autorisation ultérieure de FULL **dans la nouvelle copie seulement**,
conserver `$Reference` et `$SourceRevision` avant de changer de cwd, puis :

```powershell
Set-Location -LiteralPath $Sandbox
.\.venv\Scripts\python.exe python/09c_full_reproduction.py --reference-root $Reference --sandbox-root $Sandbox --source-revision $SourceRevision --rscript $Rscript --mode FULL --authorize-full
```

Cette commande utilise les snapshots restaurés ; elle ne télécharge pas Yahoo.
Le notebook offre la même orchestration : ouvrir sa copie dans le sandbox,
sélectionner `.venv`, définir `AI_CHIP_REFERENCE_ROOT` et `AI_CHIP_SANDBOX_ROOT`,
définir `AI_CHIP_RSCRIPT`, puis harmoniser `SOURCE_REVISION` avec le hash enregistré
dans le nouveau `state.json` (le défaut du notebook reste le tag scientifique
ancien). Changer explicitement `MODE` et `AUTHORIZE_FULL`. Aucun basculement
automatique. `--execute-notebook` n’injecte pas la révision sélectionnée : il ne
convient pas à une nouvelle révision sans cette adaptation de la copie isolée.
Ces adaptations et commandes pour un nouvel essai n’ont pas été exécutées en 9C3.
Un sandbox ayant commencé FULL n’est pas repris silencieusement après un échec :
inspecter ses preuves et préparer une nouvelle copie pour une autre tentative.

## Durée et acceptation

La Phase 6 historique a mesuré environ 20,14 minutes de fits CPU, hors préparation,
scoring et autres étapes. ARIMA rolling R/Python et les éventuelles reconstructions
Phase 7 ajoutent du temps ; aucun temps total FULL n’a été mesuré pendant 9C1.
Dans le run audité en 9C3, les 17 commandes scientifiques cumulent **839.065 s**
(13.98 minutes), dont Phase 6 **491.242 s**, Phase 7 **123.876 s** ; avec
checkpoint/gate, **845.982 s**. Ces sommes de durées de subprocess excluent une
partie des copies, imports/contrôles et archives ; ce n’est pas le temps mural
total ni une garantie de durée pour une autre machine.
Prévoir une session CPU prolongée, de l’espace disque pour la copie de dépendances,
poids, archives et nouveaux résultats ; les logs mesurent chaque commande.

§8.3 reste PARTIAL tant que le notebook ne termine pas le vrai pipeline sur une
machine/environnement vierge préparé avec packages et snapshots documentés.
Conserver notebook exécuté FULL, versions, révision, entrées SHA, logs/code-sortie,
nouveaux audits, freeze/provenance, comparaisons et empreintes finales de la référence.
Un arrêt protégé est un blocage documenté, jamais un PASS scientifique.
