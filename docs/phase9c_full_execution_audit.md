# Phase 9C3 — audit final de la reproduction FULL isolée

Audit du 9 octobre 2026 sur `feature/full-reproduction`, en lecture seule des
résultats déjà produits. **Aucun FULL, entraînement ni évaluateur Phase 7 n’a été
relancé pendant cet audit.** Seuls les quatre livrables documentaires Phase 9C
sont créés/modifiés ; les résultats officiels restent ceux du projet historique.

## Conclusion et portée

Le vrai `.cache/phase9c/full_result.json` du sandbox
`C:\Temp\ai-chip-full-9c1-e3cd311` indique **PIPELINE_EXECUTED** et
**PARTIAL_PENDING_CLEAN_MACHINE_REVIEW**. `full_failure.json` est absent.
Les 17 commandes scientifiques, le checkpoint et le gate ont terminé avec le
code 0. Cela démontre l’exécution du runner dans ce sandbox préparé.
Les résultats ne sont pas tous identiques : 116/210 fichiers ont les mêmes
octets, 94 diffèrent, dont des valeurs et poids GRU réellement différents.

| Exigence distinguée | Statut | Preuve / manque |
| --- | --- | --- |
| A. Pipeline FULL dans le sandbox préparé | PASS pour l’exécution | Journaux et nouvelles sorties inspectés ; identité numérique complète non obtenue |
| B. Machine entièrement vierge | PARTIAL | Environnement Python et bibliothèque R copiés d’installations existantes ; aucun essai d’installation/exécution sur machine vierge |
| C. Notebook FULL exécuté intégralement | PARTIAL | Seul un notebook exécuté PREFLIGHT est conservé, 5 cellules ; pas de notebook exécuté en mode FULL |
| §8.3, notebook reproduisant toute l’étude sur machine vierge | PARTIAL | A ne suffit pas pour satisfaire B et C |

Le FAST historique sert à consulter/recalculer des synthèses de sorties gelées ;
il ne démontre pas les estimations FULL. Le notebook FULL orchestre le runner,
mais sa capacité préparée ne constitue pas une preuve de son exécution complète.
Le PDF officiel du cahier des charges n’était pas intégré au dépôt lors de
l’audit automatisé : limite documentaire, pas livrable scientifique manquant.

## Traçabilité et méthode de comparaison

Point scientifique `e3cd311e4177807c2d422e74f3290d93cef35dab`
(`v0.13.0-phase9b`) ; développement avant audit
`69d07c6cca68a49ab8b0a450be6c75830fde3c0f`.
Checkpoint TRAIN du sandbox : `524a4de859f482e5c846a1b102a6c3651579040f`.
SHA256 du vrai résultat FULL : `a40762f8ad3bbd3216508ee5bc42876e5a75841168a652f9a84da710bcc432f1`.

Pour chacun des 210 chemins du manifeste d’archive, l’audit a relu les trois
fichiers : historique dans `sandbox/.cache/phase9c/historical_outputs/<path>`,
historique encore présent dans `reference/<path>`, reproduit dans `sandbox/<path>`.
Tous les SHA enregistrés ont été recalculés et correspondent ; les 210 archives
correspondent à la référence actuelle. Aucun chemin absent ou substitué.

Les CSV ont été comparés avec `csv.DictReader` : ordre/en-têtes, nombre de lignes
et chaque cellule, sans tolérance pour décider leur égalité. Les écarts numériques
sont calculés en float64, signés `reproduit − historique`, et relatifs à la valeur
historique. La tolérance absolue descriptive originale `1e-6` reste inchangée ;
elle n’est pas une preuve d’équivalence scientifique. Les PNG sont décodés RGBA
et comparés pixel à pixel. Les fichiers `.keras` sont ouverts comme ZIP/HDF5,
sans charger TensorFlow : tableaux récurrents puis Dense, ordre des variables
numériques, concaténation C-contiguë identique à `weights_hash`. Les SHA ainsi
calculés concordent avec les deux journaux de fits Phase 7.

Le [registre CSV](phase9c_full_differences.csv) contient les **210 chemins** et
les neuf colonnes demandées ; les 116 identiques sont explicitement `identical`.
Une catégorie principale par fichier ; les changements mixtes sont décrits dans
`scientific_impact`, `explanation` et `verification_status`. Le
[résumé JSON](phase9c_full_summary.json) conserve les différences par colonne,
les maxima, les 40 métriques historique/reproduit, poids, versions observées,
gates, événements, journaux/commandes/SHA et fichiers critiques protégés.

## Classification des 94 fichiers différents

| Catégorie principale | Nombre | Preuve / limite |
| --- | --- | --- |
| metadata_or_runtime | 20 | Colonnes de durée/provenance, ou source de gestion des audits inspectée |
| formatting_or_serialization | 64 | Égalité exacte après CRLF → LF, cellules inchangées |
| plot_rendering | 4 | Pixels comparés ; données GRU sous-jacentes aussi différentes |
| floating_point | 0 | Non retenu comme explication causale autonome |
| model_estimation | 1 | Poids GRU reconstruits réellement différents |
| neural_nondeterminism | 0 | Non prouvé ; cause numérique laissée non résolue |
| scientific_difference | 5 | Panel, métriques, DM, ratios et coûts comparatifs mixtes |
| unresolved | 0 | Aucun contenu de fichier non caractérisé ; cause GRU non résolue séparément |

Total : **64 + 20 + 4 + 1 + 5 = 94**. L’absence de fichier classé `unresolved`
signifie que son contenu a été caractérisé ; **le mécanisme numérique de la
variation GRU reste non résolu**, signalé dans les statuts de vérification.
Les 94 différences ne sont donc pas toutes sans incidence scientifique.

## Résultats scientifiques vérifiés directement dans les CSV

| Phase | Comparaison et résultat |
| --- | --- |
| 2 | 12 CSV supplémentaires, hors corpus archivé des 210, comparés directement référence/sandbox : toutes les cellules identiques, y compris statistiques ADF/KPSS, p-values et décisions. NVDA/AMD/SOXX : niveaux et log-prix non stationnaires, log-rendements stationnaires selon les décisions historiques. Split 2200 = 1980 TRAIN + 220 TEST, dates 2018-01-02 → 2025-11-14 / 2025-11-17 → 2026-10-02 inchangées. Les 7 snapshots ont leurs SHA historiques exacts dans les deux racines. |
| 3A/3B | Coefficients, scores, résidus, diagnostics et validation R/Python identiques ; seule la durée dans la trace auto-ARIMA change. Lock Phase 3B Naive `(0,1,0)`, drift FALSE, avertissement diagnostique conservé. L’ARIMA(2,1,2) challenger Phase 7 reste la spécification distincte pré-déclarée. |
| 4 | Toutes les cellules CSV inchangées, y compris coefficients VAR, Granger (statistiques/p-values), Johansen (statistiques/valeurs critiques/rangs), résidus, stabilité, IRF/FEVD. VAR(9) stable et adéquat, rang 0, VECM FALSE inchangés. Les décisions R et Python restent celles des tableaux comparatifs originaux. |
| 5 | GARCH(1,1) Normal verrouillé ; coefficients, p-values, persistance, ARCH-LM et diagnostics identiques cellule par cellule. Aucune différence de coefficient maquillée en métadonnée ; les CSV Python différents en bytes ne diffèrent que par CRLF/LF. |
| 6 | 18 fits et 2 refits PASS dans les nouveaux CSV ; grilles A/B/C, scores/folds/prédictions de validation et pertes identiques. C retenue pour LSTM et GRU : lookback 60, 64 unités, dropout 0.2, epochs 38/36. Seules les durées des 7 CSV de coût/fits changent. Les deux refits Phase 6 ont même charge utile `model.weights.h5` et mêmes tableaux de poids que les historiques, malgré des `.keras` différents en bytes. |
| 7 | 211 origines communes, 5 modèles, horizons 5/10, 2110 prévisions. Dates, actuals, périmètre, coefficients ARIMA/VAR et scalers inchangés. 32/40 cellules métriques exactement identiques ; 8 différences GRU, 4 dépassant 1e-6. Les 4 autres modèles ont mêmes valeurs de prévision et de métriques. Les décisions DM/Holm, critères d’éligibilité et recommandation finale Naive restent identiques. |

Les différences préexistantes **entre R et Python** ne sont pas effacées : la
comparaison porte sur chaque réalisation historique contre sa nouvelle réalisation.
Les valeurs complètes des principaux CSV et les 12 comparaisons Phase 2 sont dans
`scientific_checks` du JSON ; les diagnostics détaillés sont couverts par les 210
comparaisons et leurs preuves par fichier, pas seulement par les lignes du tableau.

## Poids et écarts GRU

| Réseau / artefact | SHA256 fichier `.keras` | SHA256 tableaux numériques |
| --- | --- | --- |
| LSTM / historical | ad68e3fc053c53d5df22c46a252fde321df95dcc27931bd2e62bf9c0266c8bee | ea7182fb463738881339e2f2010a6f5a998f778dafe26b825520937a5a146e46 |
| LSTM / phase6_new | c3b5f1a8a5ad5d4a9abde99e42776358c52764efba4834c7bcef6ad345c86308 | ea7182fb463738881339e2f2010a6f5a998f778dafe26b825520937a5a146e46 |
| LSTM / phase7_reconstructed | 9e9731d50881b22c256a1503cb12517dc7f54e2aae3243306abc02c7e42121b2 | ea7182fb463738881339e2f2010a6f5a998f778dafe26b825520937a5a146e46 |
| GRU / historical | 7d5f73850064bbf44e1693f4b6c03946f9aa8a3d469ab2feb0d05102ace874b8 | 63830a2b12f74a8fb30ee79b761f04e1344a619afac49e9add9387cffdff1dc5 |
| GRU / phase6_new | eb933c5e0a9c34352d0bdda298cf52df11fa385fae1046320013999886560ab0 | 63830a2b12f74a8fb30ee79b761f04e1344a619afac49e9add9387cffdff1dc5 |
| GRU / phase7_reconstructed | 587d65dab9f6caf052177271704b2ce682b4ab80c2b18cb136f3610e91c68304 | 727ecc3d3bdcccd42f3092de9675a311a5d12d25d4a7079e9c806a0ea2ea2ba2 |

`historical` : `.cache/phase6/<réseau>_train_refit.keras` dans la référence,
chargé par la Phase 7 historique (`loaded_from_phase6_cache`). `phase6_new` :
refit réellement exécuté dans le sandbox. `phase7_reconstructed` :
`.cache/phase7/<réseau>_reconstructed.keras`, réellement utilisé par le nouveau
runner (`reconstructed_from_locked_specification`, seed 42, TRAIN-only).

Les ZIP Phase 6 diffèrent par `date_saved` et `shared_object_id` dans les
métadonnées/configurations ; `model.weights.h5` est identique octet pour octet
pour chaque réseau. Le loader original exige le SHA du fichier `.keras`
pré-déclaré : cette condition échoue pour les deux nouveaux fichiers et déclenche
sa reconstruction existante avant l’ouverture TEST. La tolérance et les SHA
historiques n’ont pas été remplacés.

Le champ `cache_file_sha256` du nouveau journal décrit le **fichier Phase 6
examiné**, pas le fichier Phase 7 reconstruit utilisé. Il ne doit pas être cité
comme SHA des poids reconstruits. Le tableau ci-dessus donne les deux niveaux.
LSTM reconstruit : poids numériques identiques. GRU reconstruit : **12865/14282**
paramètres différents, maximum absolu **2.8312206268310547e-07**.

| Horizon | Métrique | Historique | Reproduit | Écart signé | Écart relatif absolu | ≤ 1e-6 |
| --- | --- | --- | --- | --- | --- | --- |
| 5 | MSE | 187.607668905215 | 187.607608044477 | -6.08607375340853e-05 | 3.24404316e-07 | False |
| 5 | RMSE | 13.6969948859308 | 13.6969926642485 | -2.22168231012176e-06 | 1.62202171e-07 | False |
| 5 | MAE | 10.7658801047529 | 10.7658796312305 | -4.73522407062887e-07 | 4.39836226e-08 | True |
| 5 | MAPE | 5.31127353152912 | 5.31127330202199 | -2.29507136850771e-07 | 4.32113194e-08 | True |
| 10 | MSE | 215.000788270131 | 215.00070419752 | -8.40726115143298e-05 | 3.91033969e-07 | False |
| 10 | RMSE | 14.6629051783789 | 14.6629023115316 | -2.86684728223463e-06 | 1.95517003e-07 | False |
| 10 | MAE | 11.1723230600881 | 11.1723225148812 | -5.45206853885816e-07 | 4.87997752e-08 | True |
| 10 | MAPE | 5.46427498591563 | 5.46427479377908 | -1.92136549337363e-07 | 3.51623134e-08 | True |

Les quatre écarts MSE/RMSE dépassent le seuil descriptif absolu original ; les
quatre écarts MAE/MAPE existent aussi et restent sous ce seuil. Les écarts relatifs
de MSE/RMSE sont compris entre 1.622e-7 et 3.911e-7. **304/422** prévisions GRU
changent, écart prix absolu maximal **0.00012678739417992801 USD**, relatif maximal
**5.770626833748083e-7** ; les erreurs quadratiques changent aussi, maximum absolu
**0.005633408811490881**. Ce sont de vrais changements numériques.

TensorFlow **2.21.0 CPU**, Keras **3.15.1** ; source : opérations déterministes
demandées, seed 42, pipeline `tf.data` déterministe et `shuffle=False`.
Les journaux neuronaux signalent oneDNN activé et des ordres de calcul susceptibles
de changer les arrondis. Ce message ne prouve pas la cause de cette variation.
La [documentation primaire TensorFlow](https://www.tensorflow.org/api_docs/python/tf/config/experimental/enable_op_determinism)
conditionne le déterminisme à la reproduction du matériel, de l’environnement,
des seeds et de l’état ; elle ne garantit pas l’identité entre versions.
Le mécanisme propre au GRU reconstruit reste **non établi** : aucune nouvelle
expérience, désactivation oneDNN, modification de seed ou tolérance durant 9C3.
La petitesse des écarts et la stabilité des décisions ne valent pas identité
bit-for-bit ni test d’équivalence scientifique.

## Diebold–Mariano et recommandation

| Comparaison | h | DM historique → reproduit | p historique → reproduit | Décision reproduite (inchangée) |
| --- | --- | --- | --- | --- |
| GRU C / Naive | 5 | 3.7966173884650525 → 3.796616093589111 | 0.0001919621997004312 → 0.0001919631371684025 | reject_equal_accuracy |
| GRU C / LSTM C | 5 | -4.6039073612686225 → -4.603907926808417 | 7.17661213959966e-06 → 7.176594434217795e-06 | reject_equal_accuracy |
| GRU C / Naive | 10 | 3.2736788869726974 → 3.273682481415023 | 0.00124137874454141 → 0.0012413637297965202 | reject_equal_accuracy |
| GRU C / LSTM C | 10 | 1.675475610507911 → 1.6754748918456956 | 0.09532925155626369 → 0.09532939265503194 | not_rejected |

Quatre lignes DM impliquant GRU changent numériquement. Maximum absolu :
statistique DM corrigée **3.5944423255607205e-06**, p-value brute
**1.4109876825263434e-07**, p-value Holm **6.005897955959488e-08** (2 lignes),
variance HAC **0.522956931614317**, relatif maximal **4.219903529151569e-06**
pour cette variance. Les décisions `raw_reject_5pct`, `decision_5pct`, le meilleur
modèle moyen et la base de décision sont inchangés dans les 10 lignes.
Les ratios moyens MAE/RMSE de GRU changent dans `recommendation_checks` ; aucun
challenger ne satisfait tous les critères pré-déclarés. **Naive reste final**.
Les sorties historiques et les recommandations du rapport ne sont pas remplacées.

## Figures différentes

| Figure Phase 7 | Pixels différents / 2 160 000 | Écart canal max |
| --- | --- | --- |
| phase7_absolute_errors_over_time_h10.png | 249 | 1 |
| phase7_absolute_errors_over_time_h5.png | 168 | 1 |
| phase7_actual_vs_forecasts_h10.png | 73 | 1 |
| phase7_actual_vs_forecasts_h5.png | 88 | 1 |

Ce sont les quatre graphiques de prévisions/erreurs Phase 7 alimentés par un panel
GRU différent ; classés `plot_rendering` pour l’artefact image, avec incidence
des données explicitement indiquée. Aucun autre graphique des 210 n’a changé.

## Pipeline exécuté et contrôles documentaires

| Journal dans `.cache/phase9c/logs/` | Action réellement exécutée | Code | Secondes |
| --- | --- | --- | --- |
| 00_preparation_01_data_preparation_.json | python/01_data_preparation.py | 0 | 1.592 |
| 01_eda_01_data_eda_.json | python/01_data_eda.py | 0 | 11.782 |
| 02_arima_02_arima_.json | python/02_arima.py | 0 | 21.946 |
| 03_arima_02_arima_.json | r/02_arima.R | 0 | 5.230 |
| 04_arima_02_arima_--compare-r.json | python/02_arima.py --compare-r | 0 | 6.325 |
| 05_arima_02_arima_--summarize.json | python/02_arima.py --summarize | 0 | 5.521 |
| 06_validation_02b_arima_validation_.json | python/02b_arima_validation.py | 0 | 104.576 |
| 07_validation_02b_arima_validation_.json | r/02b_arima_validation.R | 0 | 20.219 |
| 08_validation_02b_arima_validation_--summarize.json | python/02b_arima_validation.py --summarize | 0 | 6.487 |
| 09_var_03_var_vecm_.json | python/03_var_vecm.py | 0 | 7.375 |
| 10_var_03_var_vecm_.json | r/03_var_vecm.R | 0 | 12.243 |
| 11_var_03_var_vecm_--summarize.json | python/03_var_vecm.py --summarize | 0 | 6.058 |
| 12_garch_04_garch_.json | python/04_garch.py | 0 | 5.304 |
| 13_garch_04_garch_.json | r/04_garch.R | 0 | 2.267 |
| 14_garch_04_garch_--summarize.json | python/04_garch.py --summarize | 0 | 7.021 |
| 15_neural_05_lstm_gru_.json | python/05_lstm_gru.py | 0 | 491.242 |
| 16_evaluation_06_evaluation_.json | python/06_evaluation.py | 0 | 123.876 |

Les summaries listés sont des étapes réellement exécutées après les nouveaux
scripts R/Python, non la seule consultation de sorties historiques. Phase 6 :
**491.242 s** pour la commande complète ; Phase 7 : **123.876 s**, incluant les
deux reconstructions neuronales prévues par le loader. Somme des 17 commandes :
**839.065 s (13.98 min)** ; avec add/commit/gate :
**845.982 s**. Ce n’est pas une mesure du temps mural total FULL :
copies, archive, imports/contrôles et audit documentaire ne sont pas tous inclus.

`checkpoint_add.json`, `checkpoint_commit.json`, `fresh_protocol_gate.json`
ont aussi le code 0 (0.290 / 0.258 / 6.369 s). Quatre probes environnement
(`python_environment`, `pip_check`, `r_environment`, `r_parse`) ont le code 0 :
ce sont imports/versions/parsing de préparation, pas des estimations.
`r/01_data_eda.R` reste un placeholder seulement parsé ; EDA exécutée en Python.
`acquisition_restore.json` confirme les sept snapshots restaurés, aucun nouveau
téléchargement Yahoo. Les sources réelles et commandes exactes sont dans le JSON.

Les 24 journaux ont été lus : aucun code non nul ni traceback. Les stderr
contiennent les avertissements statsmodels `acorr_lm` FutureWarning, remplacement
S3 quantmod, TensorFlow oneDNN/reset_default_graph/absence de GPU natif et
normalisation Git CRLF/LF ; ils ne sont pas assimilés à des échecs d’exécution.
Les warnings diagnostiques scientifiques conservés dans les CSV ne sont pas
supprimés sous prétexte du code 0.

Le contrôle `check_llm` est interne au runner, sans journal de subprocess dédié.
Le code exécuté l’appelle après Phase 7 et avant la sauvegarde du résultat final :
le chemin terminal réussi implique son retour sans exception. Sa vérification
documentaire a aussi été répétée ici en lecture seule : réponse SHA historique,
35 identifiants/affirmations supportés, présence fidèle dans le texte et sources
existantes. **Pas de nouvelle réponse LLM**, pas de certification indépendante
des nouvelles valeurs GRU par les 35 affirmations historiques.

## Gate, gel et changement de provenance d’implémentation

Le protocole original conserve le commit pré-déclaré
`1e5ad76c6834f4e24fee825c894261597c94c917` et ses deux SHA.
Nouveau gate : **2026-10-09T20:47:24.736428+00:00**, working tree propre vérifié,
`test_read_before_this_gate=False`. Journaux du nouvel évaluateur :
TRAIN 20:47:31.154763 ; modèles gelés 20:48:36.955795 ; accès TEST au même
timestamp après l’événement de gel ; prédictions gelées 20:49:25.837858 ;
métriques 20:49:26.207674 (UTC). Tous les indicateurs `frozen` sont TRUE,
et scalers/features correspondent à l’historique. Cela concerne le nouvel
**évaluateur** ; EDA/PREFLIGHT ont auparavant lu ou hashé les snapshots comme
prévu, ce n’est pas la prétention qu’aucun byte TEST n’a jamais été lu sur l’hôte.

Source enregistrée lors des anciennes prévisions :
`e3ab3fc5ad7a12ae2067a471a0a964c1fe84eea61e1ff7925c59c90ae2f4f93e`.
Source actuelle de référence et sandbox :
`8c9dfe8026997c6483b055910b247c1cb6be8c04e1bfbfae4a7e1844b0bb2f4f`.
Ce changement préexiste à 9C3. Lecture du diff complet et comparaison AST :
`verify_protocol_commit`, `summarize`, `run` changent pour la persistance des
audits/gates et la traçabilité des anciennes prévisions ; les fonctions de fit,
reconstruction, prévision, métriques, DM et recommandation sont inchangées.
Le nouveau run utilise un gate frais, pas le replay historique : preuve dans
`fresh_protocol_gate.json` et le runtime. Le changement de SHA d’implémentation
est donc expliqué, sans prétendre que les deux sources complètes sont identiques.

## Protection, validations et limites restantes

Les **358/358 fichiers** du manifeste original ont été relus et rehashés,
aucune mutation : sorties 1–8, protocoles, FAST, réponse LLM, rapport MD/DOCX/PDF,
sources historiques. Les sept snapshots sont identiques dans les deux racines.
Les nouveaux fichiers Phase 9C ne font pas partie de ce manifeste historique.
Les SHA des livrables critiques et du manifeste technique sont dans le JSON.
Le notebook conserve `SOURCE_REVISION = "v0.13.0-phase9b"` ; pour un futur clone
basé sur une autre révision locale, harmoniser ce paramètre avec son `state.json`.
`--execute-notebook` ne l’injecte pas. Cette adaptation de la copie isolée et sa
validation restent à faire lors d’un futur essai autorisé, pas pendant 9C3.

Validations dans le venv de référence : **Ruff PASS**, **pytest 402 PASS,
4 avertissements statsmodels `acorr_lm` existants (36.37 s)**,
**`git diff --check` PASS**. Le registre documentaire a aussi été contrôlé :
210 chemins uniques, schéma exact, totaux/catégories cohérents, SHA des 210
archives/sorties relus et **358 fichiers protégés + 7 snapshots** rehashés après
les modifications documentaires. Aucun nouveau test scientifique de modèle.

Blocages restants §8.3 : installation et exécution sur machine vierge à démontrer,
notebook exécuté FULL intégralement à conserver, variation numérique du GRU
reconstruit à expliquer si l’on demande une identité stricte. Ne pas modifier
les tolérances ou résultats historiques pour obtenir un PASS. Les journaux bruts,
archives et poids sont locaux et ignorés par Git : conserver ce sandbox ou en
faire ultérieurement une archive externe immuable ; les seules empreintes
documentaires ne permettent pas de relire des fichiers supprimés.

Aucune relance n’est prescrite ni exécutée dans cette mission. Le prochain essai
éventuel nécessite un nouveau clone isolé et son propre manifeste ; le sandbox
déjà FULL est une preuve à préserver. Aucune publication GitHub, PR, merge ou tag.
