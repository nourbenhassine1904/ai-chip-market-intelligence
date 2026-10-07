# Human Interpretation — Phase 6

> Team working interpretation. This document summarizes our understanding
> of the LSTM and GRU temporal validation. It should be reviewed and
> understood by the team before the final defense.

## 1. Why use LSTM and GRU?

LSTM et GRU sont deux architectures de réseaux neuronaux récurrents conçues
pour traiter des données séquentielles.

Contrairement à un modèle classique qui utilise seulement une relation
paramétrique prédéfinie, ces réseaux peuvent apprendre des relations
temporelles non linéaires à partir d'une succession d'observations passées.

Le cahier des charges demande explicitement de comparer LSTM et GRU.

Nous les avons donc appliqués à la prévision du log-prix NVDA en utilisant
également des informations historiques sur les rendements, la volatilité,
AMD et SOXX.

Notre objectif n'était pas de supposer que le deep learning serait meilleur,
mais de vérifier empiriquement s'il apporte un gain prédictif par rapport à
une baseline naïve.

---

## 2. What is a sliding window?

Un réseau LSTM ou GRU ne reçoit pas directement toute la série temporelle en
une seule fois.

Nous construisons des fenêtres glissantes.

Pour une origine temporelle t, le modèle observe uniquement les valeurs
passées comprises dans :

t - lookback + 1 jusqu'à t.

À partir de cette fenêtre, il prédit directement les dix prochains log-prix :

t+1 jusqu'à t+10.

Par exemple, avec un lookback de 60, chaque observation d'entrée contient
les 60 dernières séances disponibles avant l'origine de prévision.

Aucune information située après l'origine n'entre dans les variables
explicatives.

Les configurations verrouillées LSTM C et GRU C utilisent toutes deux un
lookback de 60 séances.

---

## 3. Why is scaling important?

Les variables utilisées par le réseau n'ont pas la même échelle.

Par exemple, un log-prix, un rendement quotidien et une volatilité glissante
ont des distributions et des amplitudes différentes.

Sans normalisation, une variable ayant une grande amplitude numérique peut
avoir une influence disproportionnée pendant l'entraînement.

Nous utilisons donc une standardisation des variables X ainsi qu'une
standardisation séparée de la cible y.

La standardisation aide également l'optimiseur à travailler dans des plages
numériques plus stables.

Cependant, en séries temporelles, la normalisation doit être réalisée sans
utiliser d'informations provenant du futur.

---

## 4. How was leakage prevented?

La prévention du leakage a été une contrainte centrale de cette phase.

Pour chaque fold, les scalers X et y sont ajustés uniquement sur la partie
TRAIN du fold.

Par exemple :

Fold 1 :
le scaler utilise uniquement les observations allant du 31/01/2018 au
14/07/2023.

Fold 2 :
le scaler utilise uniquement les observations allant du 31/01/2018 au
24/04/2024.

Fold 3 :
le scaler utilise uniquement les observations allant du 31/01/2018 au
05/02/2025.

Les données de validation ne sont donc jamais utilisées pour calculer les
moyennes ou écarts-types des scalers.

Les fenêtres utilisent seulement le passé et les cibles se situent toujours
après l'origine de prévision.

L'early stopping utilise également une partie interne de TRAIN et non le bloc
de validation externe.

Enfin, le holdout final officiel n'a jamais été lu.

Les 17 contrôles du holdout guard sont PASS.

---

## 5. Why use temporal folds instead of K-fold?

Un K-fold classique mélange généralement les observations temporelles.

Cela serait incorrect pour notre problème, car un modèle pourrait alors être
entraîné sur des observations futures pour prédire une période plus ancienne.

Nous avons utilisé trois folds chronologiques avec fenêtre expansive.

Fold 1 entraîne le modèle jusqu'au 14/07/2023 puis valide sur la période
17/07/2023–24/04/2024.

Fold 2 entraîne jusqu'au 24/04/2024 puis valide sur
25/04/2024–05/02/2025.

Fold 3 entraîne jusqu'au 05/02/2025 puis valide sur
06/02/2025–14/11/2025.

Le passé est donc toujours utilisé pour prévoir une période future.

Chaque fold fournit 187 origines de validation communes aux modèles.

Cette structure donne 561 prévisions comparables par horizon pour chaque
architecture et chaque configuration.

---

## 6. Why were these features selected?

Nous avons volontairement utilisé un nombre limité de variables afin de garder
le modèle interprétable et d'éviter une sélection opportuniste de nombreuses
features.

Les cinq variables sont :

NVDA_Log_Price :
elle représente le niveau récent de la cible.

NVDA_Log_Return :
elle représente la dynamique récente des rendements NVDA.

NVDA_Rolling_Vol_20D :
elle fournit une information sur l'état récent de volatilité.

AMD_Log_Return :
elle ajoute une information provenant d'un concurrent important.

SOXX_Log_Return :
elle apporte une information sectorielle.

Le choix de SOXX est également cohérent avec la Phase 4, où son passé
apportait une information prédictive supplémentaire pour NVDA selon le test
de Granger.

Cela ne signifie cependant pas que SOXX cause économiquement les mouvements
de NVDA.

---

## 7. What do the loss curves show?

Les courbes de loss montrent l'évolution de l'erreur MSE pendant
l'entraînement.

Pour les configurations verrouillées C, la loss d'entraînement et la loss
de validation interne diminuent fortement pendant les premières epochs puis
se stabilisent à des niveaux faibles.

Sur le Fold 3, l'epoch restaurée est 38 pour LSTM C et 38 pour GRU C.

Nous n'observons pas une divergence massive et persistante entre la loss
d'entraînement et la loss de validation interne dans ces courbes.

L'early stopping empêche de continuer l'entraînement inutilement lorsque la
loss de validation interne ne s'améliore plus.

Cependant, de bonnes loss curves ne prouvent pas que le réseau généralise
bien sur une période future.

C'est précisément pourquoi nous évaluons ensuite les modèles sur les blocs
de validation temporelle externes.

---

## 8. Which LSTM configuration was retained?

Trois configurations LSTM ont été testées.

Configuration A :
lookback 20, 32 unités, dropout 0,10.

Configuration B :
lookback 60, 32 unités, dropout 0,10.

Configuration C :
lookback 60, 64 unités, dropout 0,20.

La règle définie avant lecture des résultats compare la moyenne de six ratios
RMSE :

3 folds × 2 horizons.

Les scores moyens obtenus sont :

A : environ 2,816

B : environ 3,391

C : environ 2,319

Une valeur plus faible est préférable.

La configuration LSTM C est donc verrouillée.

Elle contient 18 570 paramètres entraînables et son best epoch médian est 38.

Le fait que C soit verrouillée signifie uniquement qu'elle est la meilleure
des trois configurations LSTM testées selon notre règle.

Cela ne signifie pas qu'elle est meilleure que la baseline naïve.

---

## 9. Which GRU configuration was retained?

Les mêmes configurations A, B et C ont été testées pour GRU.

Les scores moyens des six ratios RMSE sont :

A : environ 2,008

B : environ 2,269

C : environ 1,652

La configuration GRU C obtient le score le plus faible.

Elle est donc verrouillée.

Elle utilise :

lookback = 60

units = 64

dropout = 0,20

Elle possède 14 282 paramètres entraînables et son best epoch médian est 36.

Comme pour LSTM, ce verrouillage compare uniquement les trois configurations
GRU testées.

---

## 10. Do LSTM and GRU beat the naive benchmark?

Non.

C'est l'un des résultats principaux de cette phase.

À l'horizon 5 :

Naïf :
RMSE ≈ 7,37 USD.

LSTM C :
RMSE ≈ 15,25 USD.

GRU C :
RMSE ≈ 10,52 USD.

LSTM dégrade donc le RMSE d'environ 106,9 % par rapport au naïf.

GRU le dégrade d'environ 42,6 %.

À l'horizon 10 :

Naïf :
RMSE ≈ 10,05 USD.

LSTM C :
RMSE ≈ 15,07 USD.

GRU C :
RMSE ≈ 13,27 USD.

Les dégradations sont d'environ :

LSTM : 49,9 %

GRU : 32,0 %

Les MAE et MAPE racontent également la même histoire générale.

Nous concluons donc qu'aucun des deux réseaux ne surpasse la baseline naïve
sur cette validation temporelle interne.

Ce résultat est conservé tel quel et n'a pas été masqué ou corrigé après
observation.

---

## 11. Which architecture performs better internally?

Entre les deux réseaux verrouillés, GRU C est clairement meilleur que
LSTM C.

Son score moyen RMSE ratio est :

GRU C ≈ 1,652

contre :

LSTM C ≈ 2,319.

GRU possède également moins de paramètres :

14 282

contre :

18 570 pour LSTM.

À h=5 et h=10, GRU obtient aussi des RMSE inférieurs à ceux de LSTM.

Nous pouvons donc dire que GRU est le meilleur des deux réseaux dans notre
validation interne.

Cependant, nous ne l'appelons pas meilleur modèle final du projet, car le
naïf reste meilleur et le holdout final n'a pas encore été évalué.

---

## 12. What is the computational cost?

Cette phase est beaucoup plus coûteuse que les modèles statistiques
classiques précédents.

Le protocole principal comporte :

2 architectures × 3 configurations × 3 folds

soit 18 entraînements principaux.

Deux refits supplémentaires ont ensuite été réalisés sur tout TRAIN pour les
configurations verrouillées.

Le temps total mesuré est d'environ :

1 208 secondes

soit environ :

20,1 minutes sur CPU.

Le LSTM C utilise 18 570 paramètres et le GRU C en utilise 14 282.

Malgré ce coût de calcul nettement supérieur à celui du naïf, aucun réseau
n'améliore ses performances prédictives dans la validation interne.

Cela constitue un résultat important pour la comparaison finale entre
performance, complexité et coût de calcul.

---

## 13. What remains unproven before final holdout evaluation?

Cette phase est uniquement une phase de développement sur TRAIN.

Nous n'avons pas encore démontré la performance finale de LSTM, GRU ou du
naïf sur le holdout officiel.

Les prévisions produites depuis le 14/11/2025 sont seulement des prévisions
TRAIN-end.

Les prix futurs réellement observés n'ont pas été consultés pour les évaluer.

Nous ne pouvons donc pas affirmer que le naïf sera nécessairement le meilleur
sur le holdout final.

Nous pouvons seulement conclure qu'il est largement meilleur dans la
validation temporelle interne réalisée jusqu'ici.

L'évaluation finale devra utiliser les mêmes cibles, les mêmes dates et les
mêmes horizons pour tous les modèles comparés.

---

## 14. What are the main limitations?

Plusieurs limites doivent être conservées.

Les réseaux sont entraînés avec une seule seed, 42. Un réseau neuronal peut
présenter une certaine variabilité selon l'initialisation.

La grille d'hyperparamètres est volontairement limitée à trois
configurations. Cela rend la comparaison reproductible mais ne garantit pas
que nous ayons trouvé l'architecture optimale possible.

Les fenêtres de validation se chevauchent, ce qui signifie que les erreurs
de prévision agrégées ne doivent pas être considérées comme des observations
statistiquement indépendantes.

Les réseaux prédisent directement le log-prix, qui est une série fortement
persistante et non stationnaire en niveau. Cela peut rendre l'extrapolation
plus difficile pour un réseau que la simple persistance du dernier prix.

Les réseaux ont également un coût de calcul beaucoup plus élevé que le
benchmark naïf.

Enfin, la validation finale sur le holdout officiel reste à effectuer.

La conclusion principale de cette phase est donc :

> Parmi les réseaux étudiés, GRU C est plus performant et plus parcimonieux
> que LSTM C. Cependant, aucun des deux réseaux ne surpasse le benchmark naïf
> pendant la validation temporelle interne. Dans ce cas, une architecture
> plus complexe et plus coûteuse ne conduit pas automatiquement à une
> meilleure prévision financière.
