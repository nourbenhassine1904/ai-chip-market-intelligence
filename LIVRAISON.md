# Livraison universitaire — AI-Chip Market Intelligence

**TEK-UP — Séries Temporelles pour Data Science & IA, année 2026/2027.**
Spécialité : Data Science et Intelligence Artificielle. Classe : ING-5-J-SDIAF-B.
Enseignant : **Ahmed Dhouibi**. Date de remise : **12 octobre 2026**, échéance
à **23h55, heure de Tunis**.

Équipe : **Nour Ben Hassine, Nouhe Ben Khelil, Hadir Felli, Nouha Briki**.

Le rapport principal est [RAPPORT_FINAL.pdf](RAPPORT_FINAL.pdf), copie exacte de
[l'export LaTeX](report_latex/rapport_final_latex.pdf). Les sources éditables et
la couverture personnalisée sont dans `report_latex/`. La recommandation finale
reste **Naive**. Cette livraison rassemble des résultats gelés ; elle ne réentraîne
aucun modèle, ne produit aucune prévision et ne télécharge aucune donnée.
La révision scientifique est `v0.15.0-phase9d` ; le hash du checkout source et
la date de construction figurent dans `MANIFESTE_LIVRAISON.json`.

```text
RAPPORT_FINAL.pdf              Rapport principal pour la remise
LIVRAISON.md                  Ce guide
MANIFESTE_LIVRAISON.json       Inventaire, tailles, SHA256 et statuts
report_latex/                 PDF final, TeX, BibTeX, figures, tableaux, annexes
report/                       Rapports Word/PDF/Markdown historiques Phase 9B
python/                       Scripts authentiques et outils de vérification
r/                            ARIMA, validation, VAR/Johansen, GARCH
notebooks/                    Notebooks FAST et FULL, sources non exécutées
data/raw/                     Trois snapshots Yahoo historiques vérifiés
data/processed/               Alignement, features et split TRAIN/TEST historiques
outputs/tables/               Résultats, diagnostics, audits et provenance gelés
outputs/figures/               Figures scientifiques historiques
llm/                          Prompt, réponse complète, critiques et avertissements
docs/                         Protocoles, dictionnaire, décisions, guides et audits
tests/                        Contrats scientifiques et tests de livraison
requirements*.txt             Dépendances Python scientifiques et de vérification
ai-chip-market-intelligence.Rproj  Projet RStudio commun
```

Le rapport Phase 9B et les audits Phase 9A/9B sont conservés comme **états
historiques** : leurs mentions de rapport à préparer, de couverture à compléter
ou de FULL non exécuté doivent être replacées dans leur phase. L'état FULL audité
est celui de [9C3](docs/phase9c_full_execution_audit.md). Les preuves de rendu
9D antérieures à la personnalisation ne valident pas la couverture actuelle
dans Prism ; aucun contrôle Prism de cette couverture n'est attesté.

## Installation et versions

Versions scientifiques observées : **Python 3.12.3, R 4.5.2, TensorFlow 2.21.0,
CPU Windows**. Les versions détaillées sont consignées dans les tables
`outputs/tables/phase6_runtime_versions.csv`, `phase7_runtime_versions.csv` et
dans `docs/phase9c_full_reproduction.md`. Les requirements ne figent pas toute
la pile ; comparer les versions installées aux preuves historiques.

Depuis la racine extraite, dans un chemin court et accessible en écriture :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip check
```

Si l'activation est bloquée, utiliser `.\.venv\Scripts\python.exe` à chaque
commande. Un éditeur compatible Jupyter peut sélectionner cet environnement.
R n'est pas nécessaire pour FAST. Pour une future reproduction classique,
installer manuellement dans R les packages `forecast`, `tseries`, `FinTS`,
`vars`, `urca`, `rugarch` :

```r
install.packages(c("forecast", "tseries", "FinTS", "vars", "urca", "rugarch"),
                 repos = "https://cloud.r-project.org")
```

Ouvrir le `.Rproj` à la racine. Les scripts n'installent aucun package.
`r/01_data_eda.R` reste un placeholder historique ; les quatre autres scripts R
sont des implémentations réelles. L'EDA canonique est réalisée en Python.

## FAST : consultation et contrôles des résultats gelés

FAST lit les sorties archivées, vérifie leur provenance et les formules des
métriques sur les prévisions déjà gelées. Il ne fait aucune estimation, ne
recalcule pas les prévisions Phase 7 et n'effectue aucune nouvelle évaluation
du holdout. Depuis la racine extraite :

```powershell
python -B python/phase9a_review.py --portable
python -B python/phase9a_review.py --data
```

Ouvrir `notebooks/AI_Chip_Market_Intelligence.ipynb` et exécuter les cellules
dans l'ordre, ou utiliser l'exécuteur protégé dans **une copie de travail** :

```powershell
python -B python/09a_execute_notebook.py --clean-copy
```

Cet exécuteur écrit un nouvel audit technique dans la copie de travail sous
`outputs/tables/phase9a_notebook_execution_audit.csv` et des notebooks exécutés
sous `.cache/phase9a/` ; conserver l'archive extraite de référence intacte.
Le packaging `--run-fast` utilise directement son exécution protégée dans une
extraction temporaire, avec les sorties techniques hors des livrables : il
ne remplace pas l'audit historique. FAST n'est pas une preuve de conformité
intégrale au §8.3.

## FULL : reproduction ultérieure dans un environnement isolé

Le runner FULL a **réellement terminé dans un sandbox préparé** (17 commandes
scientifiques). Une machine entièrement vierge et le notebook FULL exécuté
de bout en bout restent **PARTIAL**. L'environnement de cet essai historique
provenait de bibliothèques Python/R déjà installées. Des valeurs GRU diffèrent
réellement ; les décisions demeurent identiques, sans garantie bit-for-bit.

L'archive exclut `.git/`. **FULL ne peut pas être lancé directement depuis
le ZIP seul** : le runner et le gate Phase 7 nécessitent un checkout Git complet
et l'historique du protocole pré-déclaré. Les tests qui vérifient cet historique
requièrent également ce checkout. Ne pas créer un dépôt neuf pour contourner
ces contrôles. Pour un essai ultérieur, obtenir le dépôt et sélectionner le hash
`source_revision` du manifeste, puis restaurer dans ce checkout les sept CSV
du ZIP, sans modifier leurs octets :

```powershell
$Delivery = (Get-Location).Path
$SourceRevision = (Get-Content MANIFESTE_LIVRAISON.json -Raw | ConvertFrom-Json).source_revision
git clone https://github.com/nourbenhassine1904/ai-chip-market-intelligence.git C:\Temp\ai-chip-reference
git -C C:\Temp\ai-chip-reference checkout --detach $SourceRevision
$Reference = 'C:\Temp\ai-chip-reference'
$Snapshots = @('data/raw/NVDA_raw.csv', 'data/raw/AMD_raw.csv', 'data/raw/SOXX_raw.csv',
  'data/processed/market_aligned.csv', 'data/processed/market_features.csv',
  'data/processed/market_train.csv', 'data/processed/market_test.csv')
foreach ($Relative in $Snapshots) {
  Copy-Item -LiteralPath (Join-Path $Delivery $Relative) -Destination (Join-Path $Reference $Relative)
}
```

Vérifier chaque code de retour ; si la révision manque sur le serveur, obtenir
un checkout local complet contenant cette révision. Installer Python/R et les
packages dans la référence selon le guide Windows. Choisir ensuite **un chemin
de sandbox qui n'existe pas**, conserver la référence propre et préparer :

```powershell
Set-Location -LiteralPath $Reference
$Sandbox = 'C:\Temp\ai-chip-full-submission'
$Rscript = 'C:\Program Files\R\R-4.5.2\bin\Rscript.exe'
python python/09c_full_reproduction.py --reference-root $Reference --sandbox-root $Sandbox --source-revision $SourceRevision --rscript $Rscript --mode PREFLIGHT --prepare --copy-environment
```

Cette copie de dépendances constitue un environnement préparé, pas une machine
vierge. Si les packages R sont dans une bibliothèque personnelle, voir
`--copy-r-library` dans [le guide FULL](docs/phase9c_full_reproduction.md).
Après PREFLIGHT réussi, une future exécution explicitement autorisée se lance
depuis le sandbox avec son Python :

```powershell
Set-Location -LiteralPath $Sandbox
.\.venv\Scripts\python.exe python/09c_full_reproduction.py --reference-root $Reference --sandbox-root $Sandbox --source-revision $SourceRevision --rscript $Rscript --mode FULL --authorize-full
```

Ces commandes ne sont pas exécutées pendant la remise 9E. Ne pas ajouter
`--controlled-download` : les snapshots originaux sont fournis.
Les résultats nouveaux restent dans le sandbox ; les originaux, le protocole,
les SHA historiques et la réponse LLM demeurent inchangés.

Pour piloter un futur essai par `AI_Chip_Market_Intelligence_FULL.ipynb`, ouvrir
sa **copie dans le sandbox** et définir `AI_CHIP_REFERENCE_ROOT`,
`AI_CHIP_SANDBOX_ROOT`, `AI_CHIP_RSCRIPT`. Aligner `SOURCE_REVISION` sur le hash
du `state.json` créé (son défaut historique est `v0.13.0-phase9b`), conserver
`PREPARE = False`, puis choisir explicitement `MODE = "FULL"` et
`AUTHORIZE_FULL = True`. Les paramètres par défaut sont PREFLIGHT et
`AUTHORIZE_FULL = False`. `--execute-notebook` ne transmet pas automatiquement
la révision choisie. Cette adaptation d'une copie reste une limite du parcours
actuel ; aucune réussite de ce notebook sur machine vierge n'est revendiquée.

FULL est coûteux en CPU : 18 fits neuronaux et deux refits Phase 6, validation
ARIMA répétée, puis reconstructions Phase 7 possibles. La Phase 6 historique
a mesuré environ 20,14 minutes de fits ; le run 9C3 cumule 839,065 secondes pour
ses 17 commandes scientifiques, hors certains contrôles et copies. Ces temps
ne garantissent pas la durée sur une autre machine. Ne jamais relancer FULL
pour vérifier simplement l'archive.

## Données, résultats et traçabilité

Les trois raw proviennent de Yahoo Finance via yfinance, observations communes
du 2 janvier 2018 au 2 octobre 2026 : 2200 dates, TRAIN 1980 et TEST 220, split
chronologique 90/10. Les quatre processed sont les originaux alignés, features,
TRAIN et TEST. Les sept SHA sont vérifiés contre les manifestes Phase 1/1.5/2
et les preuves 9C3 ; absence ou divergence provoque un STOP sans téléchargement.
Les poids neuronaux et les environnements ne sont pas distribués.

| Analyse | Code | Preuves / présentation |
| --- | --- | --- |
| EDA et stationnarité | `python/01_data_eda.py` | `phase2_*`, chapitre 4 et annexes A/B |
| ARIMA et validation | `python/02_arima.py`, `02b_arima_validation.py`, homologues R | `phase3_*`, `phase3b_*`, chapitre 5 |
| VAR, Granger, Johansen | `python/03_var_vecm.py`, `r/03_var_vecm.R` | `phase4_*`, chapitre 6 |
| GARCH | `python/04_garch.py`, `r/04_garch.R` | `phase5_*`, chapitre 7 |
| LSTM/GRU | `python/05_lstm_gru.py` | `phase6_*`, chapitre 8, annexe F |
| Holdout historique | `python/06_evaluation.py` | `phase7_final_predictions.csv`, métriques/DM, chapitre 9 |
| LLM et critique | `llm/prompts/`, `responses/`, `human_analysis/` | Chapitre 10, annexe E et documents intégraux |

Les noms `phaseN_*` désignent `outputs/tables/` et les figures correspondantes
sont sous `outputs/figures/`. Les tableaux LaTeX et leurs sources sont reliés
par `report_latex/sources_manifest.json` ; le rapport Phase 9B possède aussi
`docs/phase9b_results_traceability.csv`.

**Naive reste recommandé** aux horizons 5/10 séances. ARIMA est proche mais
ne satisfait pas la règle complète pré-déclarée ; LSTM/GRU sont défavorables.
VAR(9) est stable ; le rang Johansen nul ne justifie pas VECM. GARCH décrit
la variance conditionnelle, sans prédire la direction du prix. Granger ne
prouve pas une causalité économique et un non-rejet DM ne prouve pas l'égalité.
Le LLM explique et structure les résultats sous contrôle humain ; sa réponse
originale, sa critique et les avertissements d'investissement simulé sont
conservés. Aucun conseil financier personnel n'est fourni.

## Reconstruction et intégrité de l'archive

Depuis le checkout contenant les outils 9E et les sept snapshots, ou depuis
une extraction intacte contenant le manifeste interne :

```powershell
python -B python/09e_build_submission.py
python -B python/09e_build_submission.py --run-fast
python -B python/09e_build_submission.py --verify dist/AI_Chip_Market_Intelligence_Remise_2026.zip
```

Le build emploie une zone de staging isolée, vérifie CRC/SHA/chemins/exclusions,
puis extrait réellement le ZIP et compare tous les fichiers. `--run-fast`
nécessite les dépendances de vérification installées. Les dates de construction
peuvent changer le hash du ZIP reconstruit ; les bytes scientifiques restent
ceux des sources. La taille exacte et les plus gros dossiers sont enregistrés
dans `docs/final_submission_manifest.json` du checkout de construction.
Le SHA du ZIP est séparé dans `dist/*.zip.sha256` ; le manifeste interne
exclut sa propre empreinte. Le manifeste externe et l'audit 9E sont des
preuves post-construction conservées hors du ZIP pour éviter tout cycle.

La taille ZIP doit être comparée au plafond réel du service mail : l'encodage
base64 ajoute environ un tiers, plus les en-têtes. Aucun livrable obligatoire
ne doit être retiré pour réduire la taille. Un partage externe, si nécessaire,
demande une autorisation distincte. Aucun email ni publication n'est effectué
par le script ou pendant cette mission.
