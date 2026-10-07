# Human Interpretation — Phase 3B

> Team working interpretation. This text is intended to be reviewed,
> understood and reformulated by the team before the final submission.

## 1. Why rolling-origin validation?

Dans cette phase, nous ne cherchons pas encore à évaluer définitivement le
modèle sur le holdout final. L’objectif est plus limité et plus pédagogique :
nous voulons comparer plusieurs spécifications ARIMA sur la partie TRAIN
uniquement, en respectant la nature temporelle des données.

Une validation classique aléatoire n’est pas adaptée aux séries temporelles,
car elle mélange le passé et le futur. Cela créerait une fuite d’information
et donnerait une vision artificiellement optimiste de la qualité prédictive.

Nous avons donc utilisé une validation de type **rolling-origin avec fenêtre
expansive**. Le principe est le suivant :

- on choisit une fenêtre d’apprentissage initiale ;
- on estime les modèles sur cette fenêtre ;
- on produit des prévisions à horizon 5 et 10 séances ;
- on avance ensuite l’origine dans le temps ;
- on répète ce processus plusieurs fois.

Dans notre cas, la fenêtre initiale contient **1 386 observations**. Ensuite,
l’origine avance toutes les **10 séances**, ce qui conduit à **59 origines**
de validation. Les origines s’étendent du **06/07/2023** au **27/10/2025**,
et la dernière cible observée reste bien à l’intérieur de TRAIN.

Cette approche est plus réaliste qu’un unique split interne, car elle permet
de tester les modèles dans plusieurs contextes de marché successifs. Elle
reproduit mieux la situation réelle d’un analyste qui ré-estime un modèle au
cours du temps puis prédit les jours à venir.

Cette phase est donc une **validation prédictive interne**, réalisée
strictement sur TRAIN, et non une évaluation finale.

---

## 2. Why naive baseline?

La baseline officielle de cette phase est le modèle **naïf**, c’est-à-dire
**ARIMA(0,1,0) sans drift**, aussi appelé random walk sans dérive.

Ce choix est fondamental en séries financières. Un modèle plus complexe ne doit
pas être considéré comme meilleur simplement parce qu’il a plus de paramètres
ou une structure plus sophistiquée. Il doit prouver qu’il apporte réellement
un gain prédictif par rapport à une règle très simple :

> **prévoir que le prochain prix sera égal au dernier prix observé.**

Cette baseline est particulièrement importante pour les prix financiers,
car ceux-ci sont souvent très persistants. Il n’est donc pas rare qu’un modèle
naïf soit difficile à battre sur des horizons courts.

Comparer les modèles ARIMA à cette baseline permet d’éviter une conclusion
trop rapide du type : “ARIMA est plus avancé, donc il est forcément meilleur”.
Au contraire, le projet cherche à montrer qu’un modèle complexe doit justifier
sa complexité par une amélioration mesurable des performances de prévision.

Dans cette phase, la question centrale n’est donc pas seulement :

> “Quel modèle ARIMA a les meilleures métriques ?”

mais surtout :

> “Est-ce qu’un modèle ARIMA complexe fait réellement mieux qu’un naïf,
> de façon robuste et reproductible ?”

---

## 3. Which model performs best at h=5?

À l’horizon **h = 5 séances**, les résultats montrent une image globalement
prudente.

### Côté R

Les performances sont les suivantes :

- Naïf : **RMSE 7,724**, **MAE 5,856**, **MAPE 5,639**
- ARIMA(0,1,0) avec drift : RMSE 7,814, MAE 5,917
- ARIMA(1,1,1) avec drift : RMSE 7,848, MAE 5,934
- ARIMA(2,1,2) avec drift : RMSE 7,847, MAE 5,938
- ARIMA(3,1,3) sans drift : RMSE 7,764, MAE 5,884

Le modèle naïf est donc **meilleur en R à h=5**, à la fois en RMSE et en MAE.

### Côté Python

Les performances sont :

- Naïf : **RMSE 7,724**, **MAE 5,856**, **MAPE 5,639**
- ARIMA(0,1,0) avec drift : RMSE 7,814, MAE 5,917
- ARIMA(1,1,1) avec drift : RMSE 7,838, MAE 6,032
- ARIMA(2,1,2) avec drift : **RMSE 7,351**, **MAE 5,434**
- ARIMA(3,1,3) sans drift : RMSE 7,732, MAE 5,826

En Python, le modèle **ARIMA(2,1,2) avec drift** semble le plus performant
à h=5.

Cependant, cette performance doit être interprétée avec prudence pour deux
raisons :

1. il ne couvre que **54 prévisions utilisables**, contre 59 pour le naïf ;
2. Python présente des **échecs de convergence** sur certains folds.

Ainsi, même si le score Python du ARIMA(2,1,2) paraît meilleur, il ne constitue
pas à lui seul une preuve suffisante pour verrouiller ce modèle.

La lecture correcte est donc :

- **en R**, le naïf est meilleur à h=5 ;
- **en Python**, ARIMA(2,1,2) semble meilleur à h=5 ;
- mais cette amélioration n’est ni complète, ni robuste, ni confirmée dans les
  deux langages.

---

## 4. Which model performs best at h=10?

À l’horizon **h = 10 séances**, les résultats sont légèrement différents mais
restent nuancés.

### Côté R

Les scores principaux sont :

- Naïf : **RMSE 9,369**, **MAE 7,253**, **MAPE 7,126**
- ARIMA(0,1,0) avec drift : RMSE 9,105, MAE 6,760
- ARIMA(1,1,1) avec drift : RMSE 9,081, MAE 6,731
- ARIMA(2,1,2) avec drift : **RMSE 9,080**, **MAE 6,729**
- ARIMA(3,1,3) sans drift : RMSE 9,385, MAE 7,295

En R, le modèle **ARIMA(2,1,2) avec drift** est très légèrement meilleur
à h=10, suivi de très près par **ARIMA(1,1,1) avec drift**.

### Côté Python

Les scores observés sont :

- Naïf : **RMSE 9,369**, **MAE 7,253**, **MAPE 7,126**
- ARIMA(0,1,0) avec drift : RMSE 9,105, MAE 6,760
- ARIMA(1,1,1) avec drift : RMSE 8,780, MAE 6,496
- ARIMA(2,1,2) avec drift : **RMSE 8,672**, **MAE 6,619**
- ARIMA(3,1,3) sans drift : RMSE 9,317, MAE 7,215

En Python, **ARIMA(2,1,2) avec drift** semble également le meilleur en RMSE
à h=10, tandis que **ARIMA(1,1,1)** est légèrement meilleur en MAE.

Malgré cela, ces résultats ne suffisent pas à verrouiller un ARIMA complexe.
En effet :

- l’amélioration n’est pas stable sur **les deux horizons** ;
- elle n’est pas systématiquement confirmée dans **les deux langages** ;
- les modèles Python les plus performants ont des **fits manquants**.

La bonne interprétation est donc :

> à horizon 10, certains ARIMA complexes semblent meilleurs que le naïf,
> surtout ARIMA(2,1,2) avec drift, mais cet avantage ne satisfait pas la
> règle stricte de sélection définie avant lecture des résultats.

---

## 5. Does ARIMA beat the naive benchmark?

La réponse globale est :

> **non, pas de manière assez robuste pour justifier le verrouillage d’un ARIMA complexe.**

Cette conclusion ne signifie pas que les ARIMA sont “mauvais”.
Elle signifie simplement qu’ils ne battent pas le naïf de façon suffisamment
claire selon la règle prédéfinie.

La règle de sélection exigeait notamment :

- une convergence satisfaisante ;
- un gain d’au moins **1 %** en **RMSE et MAE** ;
- ce gain devait être observé à **h=5 et h=10** ;
- et la conclusion devait être cohérente **dans les deux langages**.

Or, ce n’est pas ce que nous observons.

À **h=5**, les challengers ne dominent pas le naïf de façon robuste. En R,
aucun modèle complexe ne fait mieux que le naïf. En Python, certains modèles
semblent meilleurs, mais la couverture est incomplète.

À **h=10**, certains ARIMA font mieux que le naïf, mais là encore l’avantage
n’est pas suffisamment généralisable au regard de la règle choisie.

Le projet adopte donc une position prudente et défendable :

> un modèle plus complexe ne doit être retenu que si son avantage est clair,
> stable et reproductible.

Comme ce n’est pas le cas ici, le modèle naïf reste le choix verrouillé.

---

## 6. Are R and Python consistent?

La réponse est :

> **oui, globalement, mais pas parfaitement.**

Les deux langages partagent :

- les mêmes données TRAIN ;
- les mêmes origines ;
- les mêmes horizons ;
- les mêmes spécifications ;
- les mêmes métriques principales.

La comparaison R/Python sur les origines appariées montre des écarts modestes :

- écart maximal de **0,733 % en RMSE**
- écart maximal de **1,093 % en MAE**

Ces écarts restent raisonnables.

Ils indiquent que les implémentations R et Python racontent globalement la même
histoire : les performances sont proches et la hiérarchie des modèles est assez
cohérente, même si elle n’est pas identique à tous les détails près.

La principale différence concerne la **convergence**.

- En **R**, aucun échec de fit n’a été signalé.
- En **Python**, il y a **11 fits non convergents** :
  - 6 pour ARIMA(1,1,1)
  - 5 pour ARIMA(2,1,2)

Cela ne remet pas totalement en cause les résultats Python, mais cela réduit
leur force probante. Une bonne performance obtenue sur un sous-ensemble de
folds n’a pas le même poids qu’une performance obtenue de manière complète et
stable.

Nous pouvons donc dire que :

- R et Python sont **globalement cohérents** sur le plan scientifique ;
- mais Python présente une **fragilité de convergence** sur certains modèles
  plus complexes.

---

## 7. Why was the locked ARIMA specification selected?

Le modèle verrouillé de cette phase est :

> **Naïf / ARIMA(0,1,0) sans drift**

Ce choix n’a pas été fait parce qu’il est le plus simple “par défaut”, mais
parce qu’il satisfait mieux la règle de sélection définie à l’avance.

Les raisons sont les suivantes :

### 1. Convergence complète

Le modèle naïf ne présente pas de problème de convergence dans les validations
menées. Il est donc stable sur toutes les origines et tous les horizons.

### 2. Référence robuste

Il constitue la baseline officielle et fournit des performances de référence
réalistes pour une série de prix financiers.

### 3. Aucun challenger ne le bat de façon suffisamment robuste

Certains ARIMA complexes montrent des améliorations locales, surtout à h=10,
mais aucune spécification ne satisfait simultanément :

- la convergence satisfaisante,
- l’amélioration suffisante en RMSE,
- l’amélioration suffisante en MAE,
- la cohérence aux deux horizons,
- la cohérence inter-langages.

### 4. Principe de parcimonie

Lorsqu’un modèle plus complexe n’apporte pas un gain clair et stable, il est
méthodologiquement préférable de retenir le modèle le plus simple.

### 5. Cohérence avec les limites Phase 3A

En Phase 3A, les diagnostics avaient déjà montré :

- non-normalité des résidus ;
- effets ARCH significatifs ;
- limites du modèle ARIMA pour décrire complètement la variance.

Il est donc cohérent qu’un ARIMA plus sophistiqué n’apporte pas
nécessairement un avantage prédictif suffisant sur les prix à court terme.

La conclusion de cette phase est donc prudente mais solide :

> pour la validation prédictive interne sur TRAIN, le modèle à verrouiller est
> le naïf / ARIMA(0,1,0) sans drift.

---

## 8. What remains unproven before final holdout evaluation?

Même si cette phase apporte une information importante, plusieurs éléments
restent encore non démontrés.

### 1. La performance finale hors échantillon

La Phase 3B est une validation interne sur TRAIN.  
Elle ne constitue pas une évaluation finale sur le holdout réservé.

Nous ne pouvons donc pas encore affirmer quel modèle sera le meilleur sur les
données finales jamais utilisées.

### 2. La supériorité définitive du naïf

Le naïf est verrouillé pour la suite comme **spécification ARIMA retenue**,
mais cela ne signifie pas qu’il sera forcément le meilleur modèle de tout le
projet au sens final.

Cela signifie seulement qu’à ce stade, sur validation interne TRAIN, aucun
ARIMA complexe n’a montré une supériorité assez solide pour être retenu.

### 3. Le rôle de la volatilité conditionnelle

Les diagnostics précédents ont montré des **effets ARCH**.
Cela suggère que la dynamique de variance reste importante et qu’un modèle de
type GARCH pourrait être plus pertinent pour la partie volatilité.

Autrement dit, l’échec relatif des ARIMA complexes ne signifie pas qu’il n’y a
plus rien à modéliser ; cela signifie peut-être qu’une partie du signal utile
se trouve davantage dans la variance que dans la moyenne.

### 4. Les comparaisons avec d’autres familles de modèles

Cette phase ne compare que quelques spécifications ARIMA.
Elle ne tranche pas encore contre les futurs modèles multivariés ou non
linéaires prévus dans le projet.

### 5. La robustesse complète inter-langages

Même si R et Python sont globalement cohérents, la présence de fits non
convergents en Python invite à la prudence avant toute conclusion définitive.

La conclusion la plus juste est donc :

> la Phase 3B verrouille une spécification ARIMA simple et robuste pour la
> suite, mais elle ne remplace pas l’évaluation finale sur holdout, ni
> l’étude future d’autres familles de modèles.
