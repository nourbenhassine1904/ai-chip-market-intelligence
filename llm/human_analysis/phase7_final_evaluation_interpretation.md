# Human Interpretation — Phase 7

> Team working interpretation. This document summarizes our understanding
> of the final holdout evaluation. It should be reviewed and understood by
> the team before the final defense.

## 1. Why was the holdout protected until Phase 7?

Le holdout final représente la partie des données que nous avons volontairement
gardée totalement à l'écart pendant le développement des modèles.

Toutes les décisions précédentes concernant ARIMA, VAR, GARCH, LSTM et GRU
ont été prises uniquement à partir de TRAIN.

Cette séparation est importante parce que consulter les performances du
holdout pendant le développement aurait pu influencer le choix des modèles et
créer une forme de fuite d'information.

Avant d'ouvrir le holdout, nous avons donc écrit et commité un protocole
d'évaluation final.

Le commit du protocole est :

`1e5ad76c6834f4e24fee825c894261597c94c917`

Le holdout n'a été ouvert qu'après ce commit.

Cette procédure nous permet de considérer les résultats de Phase 7 comme une
véritable évaluation hors échantillon plutôt que comme une nouvelle étape de
tuning.

---

## 2. What is frozen walk-forward evaluation?

Dans notre évaluation finale, les paramètres des modèles restent gelés.

Cela signifie que :

- les coefficients ARIMA ne sont pas réestimés ;
- les coefficients VAR ne sont pas réestimés ;
- les poids LSTM et GRU ne sont pas réentraînés ;
- les scalers des réseaux ne sont pas recalculés.

À chaque origine temporelle, les observations déjà réalisées jusqu'à cette
date peuvent être utilisées comme nouvelle information.

En revanche, les observations futures après cette origine restent interdites.

Cette approche reproduit donc une utilisation réaliste :

nous avançons dans le temps en mettant à jour l'information disponible, tout
en conservant les modèles décidés avant l'ouverture du holdout.

Nous avons utilisé 211 origines communes et exactement les mêmes dates cibles
pour tous les modèles.

---

## 3. Which model has the lowest RMSE at h=5?

À l'horizon de cinq séances, le modèle Naive obtient le meilleur RMSE :

- Naive : 9,686 USD
- ARIMA : 9,695 USD
- VAR : 9,764 USD
- GRU : 13,697 USD
- LSTM : 16,581 USD

Naive est donc classé premier à h=5.

ARIMA et VAR restent relativement proches du naïf, alors que les deux réseaux
neuronaux présentent des erreurs nettement plus élevées.

Le résultat montre qu'à court horizon, prévoir simplement le dernier prix
observé reste extrêmement difficile à battre.

---

## 4. Which model has the lowest RMSE at h=10?

À l'horizon de dix séances, ARIMA obtient le RMSE le plus faible :

- ARIMA : 11,440 USD
- Naive : 11,486 USD
- VAR : 11,505 USD
- LSTM : 13,478 USD
- GRU : 14,663 USD

Cependant, l'écart entre ARIMA et Naive est très faible.

Le gain RMSE d'ARIMA sur Naive est d'environ 0,4 % seulement à cet horizon.

De plus, ARIMA présente une MAE supérieure :

- Naive : 9,075 USD
- ARIMA : 9,404 USD

Enfin, le test de Diebold-Mariano ne montre aucune différence significative
de précision prédictive entre ARIMA et Naive.

Le plus petit RMSE ponctuel ne suffit donc pas à conclure qu'ARIMA est
réellement meilleur.

---

## 5. What do MAE and MAPE add?

RMSE pénalise davantage les grandes erreurs parce qu'elles sont mises au carré.

MAE mesure directement l'erreur absolue moyenne et est moins dominée par les
observations extrêmes.

MAPE exprime l'erreur en pourcentage du prix réellement observé.

Ces métriques donnent donc des perspectives complémentaires.

Par exemple à h=10, ARIMA a un RMSE légèrement inférieur à celui du Naive,
mais sa MAE est supérieure.

Cela montre pourquoi une décision finale ne doit pas être basée sur une seule
métrique.

Naive fournit globalement un compromis très compétitif entre RMSE, MAE et
MAPE.

---

## 6. What does the Diebold-Mariano test show?

Le test de Diebold-Mariano compare les pertes de prévision de deux modèles.

L'hypothèse nulle est que les deux modèles ont la même précision prédictive
attendue.

À h=5 :

- ARIMA vs Naive : p ≈ 0,966
- VAR vs Naive : p ≈ 0,769
- LSTM vs Naive : p Holm ≈ 0,000049
- GRU vs Naive : p Holm ≈ 0,000576

Nous n'avons donc aucune preuve qu'ARIMA ou VAR soient meilleurs que Naive.

En revanche, Naive présente une perte significativement plus faible que LSTM
et GRU à cet horizon.

À h=10 :

- ARIMA vs Naive : p ≈ 0,936
- VAR vs Naive : p ≈ 0,974
- LSTM vs Naive : p Holm ≈ 0,224
- GRU vs Naive : p Holm ≈ 0,00497

ARIMA et VAR ne présentent toujours aucune supériorité statistiquement
démontrée sur Naive.

GRU est significativement moins performant que Naive.

Pour LSTM, la différence à h=10 n'est pas statistiquement significative après
correction Holm, même si sa RMSE ponctuelle reste plus élevée.

Une p-value supérieure à 0,05 ne prouve pas que deux modèles sont identiques.
Elle indique simplement que nous ne démontrons pas statistiquement une
différence de précision.

---

## 7. Does complexity improve forecasting accuracy?

Non, pas dans notre expérience.

Le benchmark Naive n'a aucun paramètre à apprendre et son coût de calcul est
pratiquement nul.

Pourtant, il reste meilleur ou statistiquement impossible à distinguer des
modèles classiques plus complexes.

Les réseaux neuronaux sont particulièrement illustratifs.

LSTM et GRU ont demandé des entraînements beaucoup plus coûteux mais leurs
performances finales restent inférieures à la baseline.

Ainsi, une complexité algorithmique supérieure ne garantit pas une précision
prédictive supérieure.

Cette observation est particulièrement importante pour les séries financières
fortement persistantes.

---

## 8. How do LSTM and GRU behave on the final holdout?

Les résultats du holdout confirment globalement les conclusions de la
validation interne Phase 6.

À h=5 :

- GRU RMSE ≈ 13,697 USD
- LSTM RMSE ≈ 16,581 USD

GRU est donc nettement meilleur que LSTM.

Le test de Diebold-Mariano GRU vs LSTM donne une p-value très faible à h=5,
ce qui soutient cette différence.

À h=10 :

- LSTM RMSE ≈ 13,478 USD
- GRU RMSE ≈ 14,663 USD

Cette fois, LSTM obtient un RMSE inférieur à GRU.

Cependant, la différence GRU vs LSTM n'est pas statistiquement significative
au seuil de 5 % à h=10.

Surtout, aucun des deux réseaux ne surpasse le modèle Naive.

Nous ne pouvons donc pas recommander un réseau neuronal pour la prévision
finale du prix.

---

## 9. What is the role of VAR in the final comparison?

VAR avait surtout pour objectif de modéliser les interdépendances entre NVDA,
AMD et SOXX.

En Phase 4, il avait montré que le passé de SOXX apporte une information
prédictive supplémentaire pour NVDA et AMD.

Cependant, cette information supplémentaire n'entraîne pas automatiquement
une amélioration importante de la prévision du prix NVDA.

Sur le holdout :

- VAR RMSE h5 ≈ 9,764 USD
- Naive RMSE h5 ≈ 9,686 USD

et :

- VAR RMSE h10 ≈ 11,505 USD
- Naive RMSE h10 ≈ 11,486 USD

Les différences sont très faibles et Diebold-Mariano ne montre aucune
supériorité du VAR.

VAR reste donc utile pour analyser les interactions multivariées, mais pas
comme meilleur modèle final de prévision de prix.

---

## 10. Why is GARCH excluded from the price ranking?

GARCH répond à une question différente des autres modèles.

Naive, ARIMA, VAR, LSTM et GRU produisent des prévisions de prix.

GARCH produit des prévisions de variance ou de volatilité conditionnelle.

Une RMSE de volatilité et une RMSE de prix ne représentent donc pas la même
cible statistique et ne peuvent pas être classées ensemble.

La Phase 5 reste importante pour l'analyse du risque, mais GARCH est
volontairement exclu du classement final des modèles de prix.

---

## 11. Which price model is finally recommended and why?

Le modèle finalement recommandé est :

**Naive / Random Walk**

Cette décision ne repose pas uniquement sur le fait qu'il soit simple.

À h=5, il possède directement le meilleur RMSE.

À h=10, ARIMA obtient un RMSE légèrement inférieur, mais l'amélioration est
très faible et sa MAE est supérieure.

Le test de Diebold-Mariano ne montre aucune supériorité statistique d'ARIMA
sur Naive.

VAR n'apporte également aucun gain significatif.

LSTM et GRU sont nettement plus coûteux et moins performants.

Naive combine donc :

- très bonnes performances ;
- stabilité ;
- absence de tuning complexe ;
- interprétabilité maximale ;
- coût de calcul pratiquement nul.

Selon notre règle pré-déclarée, la petite différence RMSE d'ARIMA à h=10 ne
justifie pas sa complexité supplémentaire.

Le modèle Naive constitue donc la recommandation finale pour la prévision du
prix NVDA dans ce projet.

---

## 12. What are the main limitations?

Notre évaluation finale repose sur un seul holdout historique.

Les conclusions pourraient être différentes sur une autre période de marché.

Les origines de prévision se chevauchent, particulièrement aux horizons 5 et
10, ce qui crée une dépendance entre certaines erreurs.

Le test de Diebold-Mariano utilise donc une correction HAC, mais cette méthode
repose elle-même sur des hypothèses statistiques.

Les réseaux neuronaux ont été développés avec une seule seed principale et une
grille d'hyperparamètres volontairement limitée.

Les intervalles ARIMA ont une couverture de 100 %, mais ils sont très larges :
environ 54 USD à h=5 et 77 USD à h=10.

Une forte couverture avec des intervalles très larges ne signifie donc pas que
la prévision est particulièrement précise.

Enfin, nos résultats concernent NVDA, AMD et SOXX sur la période étudiée et ne
doivent pas être généralisés automatiquement à d'autres actifs ou régimes de
marché.

La conclusion finale est :

> Le benchmark Naive reste le meilleur compromis entre précision,
> robustesse, interprétabilité et coût de calcul. ARIMA et VAR n'apportent
> pas d'amélioration statistiquement démontrée, tandis que LSTM et GRU sont
> nettement plus coûteux sans améliorer la prévision finale du prix.
