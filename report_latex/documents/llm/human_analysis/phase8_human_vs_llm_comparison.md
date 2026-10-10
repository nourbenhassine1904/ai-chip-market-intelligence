# Phase 8 — Human/Team Baseline vs LLM Comparison

## 1. Where do the baseline interpretation and LLM agree?

Les documents de référence sont les **team-reviewed baseline interpretations produced during model development**. Ils ne constituent pas un contrôle humain indépendant ou aveugle. Cette comparaison documentaire évalue l'interprétation d'un dossier déjà connu; elle ne certifie ni une lecture humaine indépendante de la réponse, ni une compétition expérimentale humain/IA.

Les accords matériels sont les suivants; les identifiants renvoient aux citations verbatim de l'[audit](phase8_hallucination_audit.csv) et à leurs sources précises.

| Point | Accord vérifié | Référence baseline |
| --- | --- | --- |
| Stationnarité et ARIMA | Non-stationnarité soutenue en niveaux, stationnarité soutenue des rendements, première différence d=1; les non-rejets ne sont pas des preuves (A01–A02). | phase2_interpretation.md §7–8; phase3a_arima_interpretation.md §1, §3 |
| SARIMA et ARCH | Gate saisonnier FALSE; pas de SARIMA; non-normalité et ARCH après ARIMA (A02–A03). | phase3a_arima_interpretation.md §5–6, §8 |
| Sélection interne | Naive verrouillé en Phase 3B selon une règle multi-horizons/langages, avec warning résiduel conservé (A04, D08). | phase3b_arima_validation_interpretation.md §5–7 |
| VAR/Granger | VAR(9) stable; SOXX apporte de l'information prédictive conditionnelle à NVDA et AMD, sans causalité économique (A05–A06). | phase4_var_vecm_interpretation.md §2–6 |
| Johansen/VECM | Rang nul dans les spécifications testées; VECM non justifié, pas de paramètres fabriqués (A07). | phase4_var_vecm_interpretation.md §8–10 |
| GARCH | Variance/volatilité distincte de la direction; lock Normal dépendant de la règle malgré l'avantage AIC/BIC Student-t (A08–A10, B06). | phase5_garch_interpretation.md §2, §4–6, §11 |
| Réseaux et décision finale | LSTM C/GRU C inférieurs à Naive dans les comparaisons étudiées; recommandation finale Naive malgré le meilleur RMSE ARIMA à h10 (A11, C02, D07). | phase6_lstm_gru_interpretation.md §10–11; phase7_final_evaluation_interpretation.md §3–6, §11 |

Les comparaisons portent sur les étapes correspondantes. Le holdout encore futur dans la baseline Phase 6 et désormais terminé dans la réponse ne constituent pas un désaccord: c'est une différence de chronologie documentée.

## 2. Where do they disagree?

**Aucun désaccord factuel matériel n'est identifié** sur les diagnostics, les modèles retenus, les métriques citées ou la recommandation finale.

Une différence réelle de prudence apparaît dans la conclusion de [phase5_garch_interpretation.md](phase5_garch_interpretation.md) §13: la baseline écrit que les effets ARCH « disparaissent ». Le LLM A et D écrit qu'aucun ARCH résiduel n'est détecté aux lags testés, sans preuve d'absence universelle. Cette restriction correspond mieux à docs/phase5_garch.md, Standardized residual diagnostics; elle ne contredit aucun chiffre (A09, D04). La baseline donne elle-même des réserves dans ses sections précédentes.

Le LLM propose en B plusieurs explications possibles des pertes neuronales, mais les désigne explicitement comme plausibles et non démontrées. Elles prolongent les limitations de docs/phase6_lstm_gru.md; ce sont des informations compatibles avec les faits, pas un désaccord ni une cause établie (B07).

Des différences de couverture demeurent: les baselines détaillent davantage les folds, scalers, échecs de convergence, coûts et comparaisons de réseaux. La réponse synthétise davantage les précautions transversales. Une omission n'est pas automatiquement une affirmation fausse.

Enfin, quelques citations locales sont trop larges: A cite phase4_r_python_summary.csv après un paragraphe contenant la corrélation NVDA/SOXX, et phase5_garch_standardized_residual_diagnostics.csv après les quatre persistances; ces chiffres résident respectivement dans les CSV Phase 2 et de comparaison GARCH. D cite FEVD après un paragraphe contenant également la corrélation. Les sources correctes sont indiquées dans A05, A08 et D02. Les nombres existent dans le dossier fourni: défaut de traçabilité, pas hallucination numérique.

## 3. Did the LLM invent any statistics?

**Aucune hallucination numérique n'a été détectée après vérification des nombres matériels effectivement cités.** Les reprises à six chiffres significatifs et les arrondis 3.17 % / 5.76 sont acceptables. Les tests de présentation numérique confrontent ces valeurs aux cellules contextualisées des CSV, sans recalcul statistique.

| Famille | Nombres ou éléments effectivement cités et contrôlés | Sources du projet / audit |
| --- | --- | --- |
| Stationnarité/ARIMA | d=1; ordres (2,1,2), (3,1,3), (1,1,1); Ljung-Box lags 10/20; p Jarque-Bera numérique 0, expliqué comme sous-flux. Aucune p-value ADF/KPSS chiffrée nouvelle. | phase8_project_facts.md, tables stationarity/arima_r/arima_python; A01–A03, D05 |
| ARCH-LM R | 1.50217×10^-12, 9.44313×10^-12, 1.06283×10^-10 aux lags 5/10/20. | outputs/tables/phase3_arima_residual_diagnostics_r.csv; A03 |
| Validation interne | 59 origines; seuil pratique 1 % RMSE et MAE aux deux horizons/langages; Naive (0,1,0) sans drift. | docs/phase3b_arima_validation.md; A04 |
| Corrélation/VAR | NVDA/SOXX 0.819116; proposition lag 1; VAR(9); module maximal 0.840223. | outputs/tables/phase2_return_correlation_train.csv; outputs/tables/phase4_r_python_summary.csv; A05 |
| Granger/Johansen | Holm SOXX→NVDA 0.000394246 et SOXX→AMD 0.0458338; rang nul principal/sensibilités et gate VECM FALSE. | outputs/tables/phase4_granger_causality_comparison.csv; outputs/tables/phase4_johansen_rank_comparison.csv; A06–A07 |
| FEVD | SOXX dans NVDA: 1.8921 % à h20, ordre NVDA/AMD/SOXX. | outputs/tables/phase4_var_fevd.csv; D02 |
| GARCH | Persistances Normal R/Python 0.964177/0.964503, Student-t 0.974285/0.974512; sigma quotidienne environ 3.17 % à h10 depuis 14/11/2025; degrés de liberté Student-t proches de 5.76. | outputs/tables/phase5_garch_model_comparison.csv; outputs/tables/phase5_volatility_forecast_train_end.csv; A08, B06, D09 |
| LSTM/GRU | Feature de volatilité sur 20 séances, une seed principale, trois configurations; aucune nouvelle métrique neuronale chiffrée. | docs/phase6_lstm_gru.md, Feature set/Hyperparameters; A11, D09 |
| Holdout et métriques | 211 origines; Naive RMSE/MAE h5 9.68557/7.68782, h10 11.4858/9.07453 USD; ARIMA RMSE h10 11.4396 USD. | outputs/tables/phase7_final_metrics.csv; outputs/tables/phase7_holdout_manifest.csv; B08, C02 |
| DM | Brute ARIMA/Naive h10 0.936111; Holm LSTM/Naive h5 4.85686×10^-5, GRU/Naive h5 0.000575887, GRU/Naive h10 0.00496551, LSTM/Naive h10 0.224206; brutes GRU/LSTM h5 7.17661×10^-6 et h10 0.0953293. | outputs/tables/phase7_diebold_mariano.csv; C02, D06 |
| Intervalles ARIMA | Couverture empirique 100 %, nominale 95 %; largeurs moyennes 54.2024 USD à h5 et 77.3901 USD à h10. | outputs/tables/phase7_arima_interval_coverage.csv; D10 |

Les valeurs de kurtosis, alpha/beta, les critères AIC/BIC détaillés et les autres métriques du projet ne sont pas chiffrés dans la réponse. Leur absence n'est ni un nombre inventé ni une vérification implicite d'une citation inexistante. Les relations qualitatives AIC/BIC, ARCH et pertes neuronales sont vérifiées dans A09–A11 et D09.

## 4. Did the LLM overstate Granger causality?

**Non.** A, B, C et D limitent Granger à une information prédictive supplémentaire, conditionnellement au système estimé. La réponse refuse une interprétation mécanique économique et ne dérive pas de stratégie de trading garantie (A06, B03, C04). D rappelle aussi la dépendance IRF/FEVD à l'ordre de Cholesky (D02).

Cette prudence concorde avec phase4_var_vecm_interpretation.md §5–6 et docs/phase4_var_vecm.md, Granger causality/FEVD. Il reste utile de compléter l'explication orale par les réserves de ce dernier document: tests Wald conventionnels sous hypothèses de variance et sélection préalable du lag. La réponse n'expose pas ces limites aussi précisément; elle ne formule cependant aucun overclaim causal.

## 5. Did the LLM misuse non-significant p-values?

**Non.** Le LLM indique explicitement que p>0.05 ne prouve pas l'égalité des performances, que Johansen non rejeté ne démontre pas l'absence absolue de relation et que Ljung-Box/ARCH-LM non rejetés ne prouvent ni iid ni absence universelle d'ARCH (A07, A09, D03–D04).

Les zéros Jarque-Bera sont correctement reliés au sous-flux numérique (A03, D05). La p-value ARIMA/Naive h10 0.936111 est explicitement brute; elle n'est pas appelée Holm. Les quatre valeurs Holm versus Naive et les deux valeurs brutes GRU/LSTM sont correctement distinguées (C02, D06; outputs/tables/phase7_diebold_mariano.csv). LSTM/Naive à h10 reste non significatif après Holm, sans preuve d'égalité.

La réponse ne décrit pas toute la calibration HAC/HLN ni ses limites sous dépendance, pertes lourdes et modèles imbriqués. docs/phase7_final_evaluation.md, Diebold-Mariano/Limitations, et phase7_final_evaluation_interpretation.md §12 complètent ce point. Il s'agit d'un manque de détail méthodologique, pas d'une p-value mal interprétée.

## 6. Did the LLM oversimplify stationarity or cointegration?

Les simplifications pédagogiques sont globalement appropriées. La définition de stationnarité en B conserve les hypothèses nulles différentes d'ADF/KPSS et la distinction non-rejet/preuve. A et D limitent le rang Johansen aux spécifications testées; aucun VECM ni relation de long terme certaine n'est fabriqué (A01, A07, B01, B04, D03).

Deux raccourcis demandent du contexte lors d'une présentation: la volatilité glissante « 20 jours » en A désigne les 20 séances observées de la feature officielle; et « ARCH-LM détectent cette structure » en B désigne une détection d'effets ARCH dans les innovations, non une preuve générale de tout clustering. Le texte précise les diagnostics et horizons testés; ces formulations ne justifient pas un classement oversimplification erronée (A11, B05).

Pour un exposé plus complet, docs/phase2_eda_stationarity.md, ADF/KPSS, précise la composante déterministe et les p-values KPSS censurées; docs/phase4_var_vecm.md, Johansen cointegration, détaille K=3, les sensibilités et les tables critiques natives. La réponse n'en reprend pas tous les détails. **Aucune oversimplification matérielle trompeuse n'est retenue dans l'audit.**

## 7. Did the LLM correctly separate price forecasting from volatility forecasting?

**Oui.** La réponse décrit les modèles Naive/ARIMA/VAR/LSTM/GRU comme des candidats à la prévision du prix, et GARCH comme une analyse séparée de variance/volatilité conditionnelle. Aucun score de volatilité n'est classé avec une RMSE de prix (A08–A11, B05–B06, C03, D09).

La sigma proche de 3.17 % est quotidienne au dixième horizon depuis la fin de TRAIN. Elle n'est ni +3.17 %, ni -3.17 %, ni un rendement, gain ou profit attendu. Elle ne représente pas un cumul de risque sur dix séances. outputs/tables/phase5_volatility_forecast_train_end.csv et docs/phase5_garch.md, TRAIN-end volatility forecast, soutiennent cette lecture. La réponse précise également qu'aucune performance de volatilité holdout n'a été mesurée, conformément à docs/phase7_final_evaluation.md, Why GARCH is evaluated separately.

## 8. Did the LLM understand why Naive was finally recommended?

**Oui.** C et D distinguent le meilleur RMSE Naive à h5 du meilleur RMSE ponctuel ARIMA à h10. La MAE ARIMA à h10 est plus élevée et la différence DM ARIMA/Naive n'est pas démontrée; la petite baisse du RMSE ne suffit donc pas à remplacer Naive (C02, D07).

La formulation « amélioration compatible » résume la règle; la condition exacte est: RMSE et MAE non pires à chacun des deux horizons, gain d'au moins 1 % sur la moyenne des deux ratios RMSE, réduction de perte soutenue par Holm à au moins un horizon et aucun horizon significativement pire. Source: docs/phase7_final_evaluation_protocol.md, Final recommendation rule. La réponse ne contredit pas cette condition et comprend le rôle de la parcimonie et du fallback.

Le warning Ljung-Box du random walk demeure explicite (D08). La réponse ne transforme ni la recommandation en preuve d'un vrai processus random walk, ni les pertes neuronales en loi universelle sur la finance. Elle aurait pu rendre plus explicite le lien entre le lock Naive de Phase 3B et l'inclusion d'ARIMA(2,1,2) comme challenger Phase 3A prévu au protocole Phase 7; ce lien figure dans les faits officiels et docs/phase7_final_evaluation_protocol.md, Fixed panel and target.

## 9. Was the simulated investment interpretation appropriately cautious?

**Oui.** La section C se présente comme une simulation académique pour un investisseur hypothétique. Elle n'ordonne aucun achat/vente, ne propose aucune allocation et ne promet ni rendement ni performance future. Les mots achat et vente apparaissent pour rejeter une stratégie automatique garantie, pas pour la recommander (C04, C06).

Elle cite un seul holdout historique, l'absence de système de trading exécuté, les frais non évalués et la distinction risque/direction (C01–C06). Slippage et fiscalité sont des exemples de coûts non étudiés, sans estimation inventée. Cette prudence concorde avec phase8_investment_disclaimer.md et docs/phase7_final_evaluation.md, Limitations.

La phrase initiale sur l'absence de signal directionnel robuste doit se lire comme absence de validation fournie, et non comme résultat d'un test directionnel: le projet compare des pertes de prix et ne rapporte pas de hit-rate directionnel. La réponse ne prétend pas avoir calculé cette métrique (C01).

Le suffixe isolé « phase8_investment_disclaimer » à la fin de C est un défaut éditorial. Il n'ajoute aucun résultat ou conseil; l'artefact officiel reste inchangé.

## 10. What useful insight did the LLM add?

La contribution utile du LLM est principalement une synthèse transversale. Il relie adéquation de la moyenne, variance conditionnelle, validation interne et évaluation finale, tout en maintenant les avertissements (A03–A04, A08–A10, B08). Sa prudence après GARCH est plus précise que la formulation finale « disparaissent » de la baseline Phase 5 (§13), même si celle-ci comporte déjà des réserves.

La réponse rapproche aussi le lock GARCH dépendant d'une politique, la séparation prix/risque et la non-universalité de la recommandation Naive (C02–C03, D07–D10). C'est utile pédagogiquement, sans constituer une nouvelle découverte statistique. Les baselines Phase 4 (§14), Phase 5 (§6, §13), Phase 6 (§14) et Phase 7 (§6, §12) contiennent déjà une grande partie de ces idées. Il serait abusif de les attribuer exclusivement au LLM ou de présenter ses hypothèses comme prospectives.

## 11. What did the team interpret better than the LLM?

Les baselines apportent une meilleure granularité sur plusieurs points. phase3b_arima_validation_interpretation.md §3–6 explique les couvertures incomplètes et les échecs de convergence Python; phase6_lstm_gru_interpretation.md §4–5, §8–12 détaille scalers par fold, calendrier, paramètres, choix de C, ratios et coût CPU. Le LLM reprend les conclusions, mais ne développe pas ces mécanismes de validation ou les coûts.

phase4_var_vecm_interpretation.md §2, §8, §12, §14 explicite le compromis lag/diagnostics, les valeurs critiques Johansen et la différence Granger/importance FEVD. phase7_final_evaluation_interpretation.md §2, §8, §12 détaille les paramètres gelés, la comparaison GRU/LSTM selon l'horizon et la dépendance des erreurs traitée par HAC. La réponse est correcte sur les p-values GRU/LSTM mais explique moins le changement de classement entre horizons.

Ces avantages de détail ne démontrent pas une supériorité humaine indépendante: les fichiers sont des baselines de développement, et la comparaison n'est pas aveugle. Les CSV et protocoles restent l'arbitre lorsqu'une formule pédagogique d'un côté ou de l'autre paraît trop absolue.

## 12. Final critical assessment of the LLM

L'audit documentaire comporte **35 claims matériels regroupés**, couvrant A (11), B (8), C (6) et D (10). Les répétitions d'une même idée ne sont pas des observations indépendantes. Les comptes suivants portent sur les lignes du CSV, pas sur une mesure expérimentale de fiabilité générale du LLM.

| issue_type | Nombre de claims |
| --- | --- |
| supported | 35 |
| invented_number | 0 |
| causal_overclaim | 0 |
| pvalue_misinterpretation | 0 |
| oversimplification | 0 |
| unsupported_financial_claim | 0 |
| other | 0 |

**Aucune hallucination numérique n'a été détectée dans les nombres matériels vérifiés.** Aucun overclaim causal, mauvaise interprétation de p-value ou claim financier non soutenu n'est retenu. Les simplifications recensées en §6 sont acceptables dans leur contexte; elles ne sont pas transformées artificiellement en anomalies.

La qualité globale est bonne pour une interprétation rétrospective: résultats fidèles, prudence sur les non-rejets, distinction raw/Holm, prix/volatilité et justification Naive cohérentes. Les réserves documentées restent les citations locales imprécises (A05, A08, D02), le suffixe éditorial en C, le lien lock/challenger peu explicite, et le développement limité des coûts et des hypothèses d'inférence (voir §2, §5, §8, §11). Elles ne rendent pas les affirmations correspondantes fausses.

Le LLM a reçu les résultats **après la modélisation et l'évaluation finale**; ses propositions sont rétrospectives. Les baselines sont team-reviewed, sans contrôle humain indépendant aveugle. Cette comparaison évalue la qualité d'interprétation, pas une compétition expérimentale pure humain/IA. L'audit est une revue documentaire préparée dans le dépôt; aucune seconde revue humaine indépendante n'est attestée. Les métadonnées exactes du modèle ChatGPT et de génération ne sont pas fournies: le commit de réponse atteste son enregistrement, pas son heure de génération ni l'identité précise du modèle.

La réponse officielle demeure figée au commit `67d60efba09c05ec571cd6907014e08ada9a2cd6`, SHA-256 `eecb0de3e0dd8e152e93db70ff71f9dad87024b7b2f3e1bee1ede05225f6f3b4`. Aucun modèle, statistique, holdout ou réponse officielle n'a été recalculé ou régénéré pour cet audit.
