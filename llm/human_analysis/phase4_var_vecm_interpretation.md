# Human Interpretation — Phase 4

> Team working interpretation. This document summarizes our understanding
> of the VAR, Granger causality and cointegration results. It should be
> reviewed and understood by the team before the final defense.

## 1. Why use returns in the VAR?

Nous avons estimé le VAR sur les log-rendements de NVDA, AMD et SOXX et non
directement sur leurs log-prix.

Ce choix vient des résultats de Phase 2. Les log-prix ont été identifiés comme
non stationnaires, alors que leurs premières différences, c'est-à-dire les
log-rendements, sont compatibles avec la stationnarité.

Un VAR standard doit être estimé sur des séries stationnaires afin d'éviter
des relations artificielles liées uniquement à des tendances communes.

Le système VAR utilise donc :

- NVDA_Log_Return
- AMD_Log_Return
- SOXX_Log_Return

soit 1 979 observations utilisables sur TRAIN.

---

## 2. How was the VAR lag selected?

Les critères d'information AIC, BIC, HQIC et FPE proposent tous un VAR de
retard 1.

Cependant, nous ne retenons pas automatiquement le lag qui minimise un critère
d'information. Nous vérifions également les diagnostics des résidus.

Pour VAR(1), les p-values du test Portmanteau sont environ :

- lag 20 : 0,00021
- lag 30 : 0,00138

Elles sont très inférieures à 0,05. Nous rejetons donc l'absence
d'autocorrélation résiduelle. VAR(1) est trop simple pour capturer toute la
dynamique temporelle du système.

Le même problème persiste pour les lags 2 à 8. Pour VAR(8), par exemple,
la p-value à l'horizon 20 est encore environ 0,0357.

VAR(9) est le premier modèle qui satisfait les diagnostics retenus :

- horizon 20 : p ≈ 0,0588
- horizon 30 : p ≈ 0,1568

VAR(10) satisfait également les diagnostics, mais VAR(9) est plus parcimonieux.

Nous retenons donc **VAR(9)** : ce choix n'est pas basé uniquement sur AIC ou
BIC mais sur un compromis entre parcimonie, stabilité et qualité des résidus.

---

## 3. Is the VAR stable?

Oui, le VAR(9) retenu satisfait la condition de stabilité.

Le module maximal des racines de la matrice compagnon est d'environ :

**0,8402**

Il est inférieur à 1.

Cela signifie que les effets des innovations du système s'atténuent au cours
du temps au lieu d'exploser indéfiniment.

Cette propriété permet également d'interpréter les IRF et la FEVD dans le
cadre du VAR estimé.

---

## 4. What do the residual diagnostics show?

Les tests Portmanteau du VAR(9) donnent :

- horizon 10 : p ≈ 0,290
- horizon 20 : p ≈ 0,0588
- horizon 30 : p ≈ 0,157

Nous ne rejetons donc pas l'hypothèse d'absence d'autocorrélation résiduelle
globale aux horizons testés.

Le résultat à l'horizon 20 reste toutefois assez proche du seuil de 5 %,
donc l'interprétation doit rester prudente.

En revanche, les tests de normalité multivariée rejettent fortement la
normalité des résidus.

Cela est cohérent avec les résultats obtenus précédemment pour les rendements
financiers : queues épaisses, observations extrêmes et volatilité variable.

Nous considérons donc le VAR comme acceptable pour étudier la dynamique
linéaire multivariée, tout en conservant une limite importante concernant
la distribution des résidus.

---

## 5. What does Granger causality mean here?

La causalité de Granger ne représente pas une causalité économique ou
structurelle.

Dire que X Granger-cause Y signifie uniquement que les valeurs passées de X
apportent une information prédictive supplémentaire pour Y, conditionnellement
aux autres variables et aux retards déjà présents dans le VAR.

Nous devons donc éviter des formulations telles que :

"SOXX provoque les mouvements de NVDA."

La formulation correcte est plutôt :

"Dans le VAR estimé, les valeurs passées de SOXX apportent une information
prédictive supplémentaire sur les rendements futurs de NVDA."

---

## 6. Which Granger relations are statistically supported?

Six directions ont été testées.

Les résultats significatifs sont :

### SOXX → NVDA

- p-value brute ≈ 0,0000657
- p-value corrigée de Holm ≈ 0,000394
- H0 rejetée

Nous trouvons donc une relation de précédence prédictive de SOXX vers NVDA.

### SOXX → AMD

- p-value brute ≈ 0,00917
- p-value corrigée de Holm ≈ 0,0458
- H0 rejetée

Cette relation reste significative après correction pour tests multiples,
mais elle est plus proche du seuil de 5 %.

Les quatre autres relations ne sont pas significatives :

- NVDA → AMD : p ≈ 0,464
- NVDA → SOXX : p ≈ 0,464
- AMD → NVDA : p ≈ 0,232
- AMD → SOXX : p ≈ 0,737

Ces résultats sont identiques dans R et Python.

La conclusion principale est donc que SOXX apporte une information prédictive
supplémentaire sur NVDA et AMD dans le système VAR retenu.

Cela ne démontre aucune causalité économique.

---

## 7. Why test cointegration on log-prices?

Le VAR principal est construit sur les rendements parce qu'ils sont
stationnaires.

La cointégration répond à une autre question : plusieurs séries non
stationnaires peuvent-elles partager une relation d'équilibre de long terme ?

Nous utilisons donc les log-prix :

- NVDA_Log_Price
- AMD_Log_Price
- SOXX_Log_Price

car Phase 2 a montré qu'ils sont non stationnaires tandis que leurs premières
différences sont stationnaires.

Si une combinaison linéaire stationnaire de ces log-prix existait, cela
soutiendrait une relation de cointégration et pourrait justifier un VECM.

---

## 8. What is the Johansen rank?

Le test principal Johansen utilise trois séries et trois retards en niveaux,
soit deux retards de différences.

Pour l'hypothèse de rang 0, la statistique de trace est environ :

**21,57**

En R, la valeur critique à 5 % est environ :

**31,52**

En Python, elle est environ :

**29,80**

Dans les deux cas, la statistique est inférieure à la valeur critique.

Nous ne rejetons donc pas l'hypothèse de rang 0.

R et Python sélectionnent tous deux :

**cointegration rank = 0**

Des analyses de sensibilité avec deux et quatre retards en niveaux donnent
également un rang 0.

La conclusion apparaît donc relativement robuste aux spécifications de lag
examinées.

---

## 9. Is VECM justified?

Non.

Pour trois séries I(1), un VECM serait justifié si le rang de cointégration
était strictement supérieur à 0 et inférieur à 3.

Ici :

**rank = 0**

Cela signifie que nous n'avons pas trouvé suffisamment de preuves
statistiques d'une relation de cointégration entre les trois log-prix dans
la spécification étudiée.

La décision est donc :

**VECM justified = FALSE**

Nous n'avons volontairement estimé aucun VECM.

Cette absence de VECM n'est pas un manque dans le projet. Elle constitue au
contraire une décision statistique : le modèle ne doit être utilisé que si
la cointégration est démontrée.

---

## 10. How should alpha and beta be interpreted?

Aucun coefficient alpha ou beta n'est interprété dans notre projet parce
qu'aucun VECM n'a été estimé.

Dans un VECM justifié :

- beta représenterait les relations de cointégration de long terme ;
- alpha représenterait les vitesses d'ajustement vers ces équilibres.

Comme le rang de cointégration est nul, produire des coefficients alpha ou
beta aurait été méthodologiquement incorrect.

Notre conclusion est donc simplement que ces paramètres ne s'appliquent pas
dans cette phase.

---

## 11. What do IRF results show?

Les fonctions de réponse impulsionnelle décrivent comment une innovation dans
une variable est associée à la trajectoire future des variables du système
VAR estimé.

Dans notre système, les IRF sont calculées jusqu'à 20 séances.

Par exemple, à une séance, les réponses estimées de NVDA à une innovation sur
AMD et SOXX sont approximativement :

- innovation AMD → réponse NVDA : -0,064 point
- innovation SOXX → réponse NVDA : -0,265 point

Ces valeurs décrivent la dynamique du VAR estimé et ne doivent pas être
interprétées comme des effets causaux économiques.

Les IRF sont également sensibles à l'identification utilisée. Dans notre cas,
l'orthogonalisation de Cholesky utilise l'ordre :

**NVDA → AMD → SOXX**

Cet ordre constitue donc une limite importante de l'interprétation.

---

## 12. What does FEVD show?

La FEVD décompose l'incertitude des erreurs de prévision de chaque variable
selon les innovations du système.

À l'horizon de 20 séances, la variance d'erreur de prévision de NVDA est
approximativement répartie ainsi :

- innovations propres à NVDA : **97,52 %**
- innovations AMD : **0,59 %**
- innovations SOXX : **1,89 %**

Cela signifie que, dans ce VAR et avec cette identification, l'incertitude de
prévision de NVDA est principalement associée à ses propres innovations.

Cette conclusion n'est pas contradictoire avec le résultat Granger
SOXX → NVDA.

Le test de Granger demande si le passé de SOXX apporte une information
prédictive supplémentaire statistiquement significative.

La FEVD mesure plutôt l'importance quantitative des innovations dans la
variance des erreurs de prévision.

Une relation peut donc être statistiquement significative tout en expliquant
une proportion relativement faible de la variance totale.

---

## 13. Are R and Python consistent?

Oui, R et Python donnent des conclusions principales très proches.

Ils utilisent le même TRAIN et produisent pratiquement les mêmes résultats
pour :

- la sélection des critères d'information ;
- le choix de VAR(9) selon les diagnostics ;
- la stabilité ;
- les tests Granger ;
- les statistiques de trace Johansen ;
- le rang de cointégration ;
- la décision de ne pas estimer VECM.

Les statistiques numériques VAR sont pratiquement identiques.

Pour Johansen, les statistiques de trace sont elles aussi presque identiques,
mais R et Python utilisent des tables de valeurs critiques différentes.

Malgré cette différence de convention, les deux langages donnent ici la même
décision : rang 0.

Nous considérons donc la réplication R/Python comme cohérente, tout en
documentant les différences d'implémentation.

---

## 14. What are the main limitations?

Plusieurs limites doivent être conservées.

Premièrement, VAR(9) est beaucoup plus complexe que VAR(1), qui était préféré
par tous les critères d'information. VAR(9) a été retenu parce qu'il est le
premier modèle à fournir des diagnostics résiduels acceptables, mais cette
complexité doit être mentionnée.

Deuxièmement, la p-value Portmanteau à l'horizon 20 est environ 0,0588, donc
relativement proche du seuil de 5 %.

Troisièmement, la normalité des résidus est fortement rejetée.

Quatrièmement, les tests Granger sont réalisés après une sélection de modèle
et ne démontrent pas une causalité économique.

Cinquièmement, le rang Johansen dépend de la spécification du test, même si
nos sensibilités avec différents retards donnent toutes rang 0.

Sixièmement, les IRF et FEVD orthogonalisées dépendent de l'ordre de Cholesky
NVDA/AMD/SOXX.

Enfin, toutes les analyses de cette phase utilisent uniquement TRAIN. Le
holdout final reste protégé et aucune performance finale de prévision n'est
encore établie.

La conclusion principale de cette phase est donc :

> Les rendements NVDA, AMD et SOXX présentent des interdépendances dynamiques
> de court terme dans un VAR(9) stable. SOXX fournit une information
> prédictive supplémentaire pour NVDA et AMD selon les tests de Granger.
> En revanche, les log-prix ne présentent pas de cointégration statistiquement
> soutenue dans les spécifications étudiées, donc aucun VECM n'est justifié.
