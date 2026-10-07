# Human Interpretation — Phase 5

> Team working interpretation. This document summarizes our understanding
> of the GARCH volatility results. It should be reviewed and understood by
> the team before the final defense.

## 1. Why was GARCH justified?

La Phase 5 est directement motivée par les résultats des phases précédentes.

En Phase 2, les rendements NVDA montraient déjà un phénomène de volatility
clustering ainsi qu'une autocorrélation des rendements au carré.

En Phase 3A, les résidus du modèle de moyenne présentaient des effets ARCH
très significatifs. Les tests ARCH-LM donnaient des p-values extrêmement
faibles, de l'ordre de 10^-13 à 10^-10.

Dans cette phase, après filtrage de la moyenne par un ARMA(1,1), les tests
ARCH-LM restent encore très significatifs :

- lag 5 : p ≈ 1,10 × 10^-13
- lag 10 : p ≈ 1,02 × 10^-13
- lag 20 : p ≈ 2,02 × 10^-12

Nous rejetons donc fortement l'hypothèse d'absence d'effets ARCH.

Cela signifie que la variance des innovations n'est pas constante dans le
temps et dépend de l'information passée.

L'utilisation d'un modèle GARCH est donc statistiquement justifiée.

---

## 2. What is the difference between mean and variance modeling?

Le modèle de moyenne et le modèle de variance répondent à deux questions
différentes.

L'équation de moyenne cherche à représenter la direction ou l'évolution
moyenne des rendements.

Dans cette phase, nous utilisons un ARMA(1,1) comme filtre de moyenne commun
en R et Python.

Le modèle GARCH ne cherche pas à prévoir directement si le rendement sera
positif ou négatif.

Il cherche à modéliser :

**la variance conditionnelle**, donc l'intensité du risque ou de la volatilité
attendue.

Nous séparons donc :

- dynamique de moyenne ;
- dynamique de volatilité.

Cela permet de traiter le volatility clustering qui reste présent après le
modèle de moyenne.

---

## 3. What do omega, alpha and beta mean?

Un GARCH(1,1) peut être écrit sous la forme :

sigma_t² = omega + alpha * epsilon_(t-1)² + beta * sigma_(t-1)²

Les trois paramètres principaux ont une interprétation simple.

### Omega

`omega` représente la composante de base de la variance conditionnelle.

Elle contribue au niveau de long terme de volatilité.

### Alpha

`alpha` mesure la réaction immédiate de la volatilité aux nouvelles
innovations ou chocs.

Une valeur élevée signifie qu'un choc récent influence fortement la
volatilité suivante.

Pour le modèle Normal retenu :

- R : alpha ≈ 0,1126
- Python : alpha ≈ 0,1116

### Beta

`beta` mesure la mémoire de la volatilité passée.

Pour le modèle Normal :

- R : beta ≈ 0,8516
- Python : beta ≈ 0,8529

Beta est ici beaucoup plus élevé qu'alpha, ce qui indique que la volatilité
passée joue un rôle important dans la volatilité future.

---

## 4. What does alpha + beta mean?

La somme :

alpha + beta

mesure la persistance de la volatilité.

Pour GARCH(1,1)-Normal :

- R : environ 0,9642
- Python : environ 0,9645

Ces valeurs sont proches de 1 mais restent inférieures à 1.

Cela signifie que les chocs de volatilité sont très persistants mais que leur
effet finit théoriquement par disparaître.

La demi-vie estimée d'un choc est d'environ :

- 19,0 séances en R
- 19,2 séances en Python

Cela signifie qu'il faut environ 19 séances de marché pour que l'effet d'un
choc de volatilité soit réduit de moitié, selon ce modèle.

Pour Student-t, la persistance est encore plus forte, autour de 0,9745, avec
une demi-vie proche de 27 séances.

---

## 5. Why compare Normal and Student-t?

Les phases précédentes ont montré que les rendements NVDA présentent :

- des queues épaisses ;
- des observations extrêmes ;
- une kurtosis élevée ;
- un rejet de la normalité par Jarque-Bera.

Il était donc naturel de comparer deux distributions d'innovations :

- Normal ;
- Student-t.

La distribution Student-t peut mieux représenter des observations extrêmes
grâce à ses queues plus épaisses.

Les degrés de liberté estimés sont proches de :

- R : nu ≈ 5,76
- Python : nu ≈ 5,76

Cette valeur relativement faible est compatible avec une distribution plus
épaisse dans les queues qu'une loi normale.

Student-t améliore fortement les critères d'information.

Par exemple en R :

- AIC Normal ≈ 10025,94
- AIC Student-t ≈ 9864,42

et en Python :

- AIC Normal ≈ 10025,87
- AIC Student-t ≈ 9864,19

Student-t fournit donc un meilleur ajustement de vraisemblance.

---

## 6. Which GARCH model was retained and why?

Le modèle verrouillé est :

**GARCH(1,1) avec innovations normales.**

Ce choix peut sembler surprenant puisque Student-t améliore fortement AIC et
BIC.

Cependant, une règle de sélection avait été définie avant estimation.

Pour préférer Student-t, il fallait notamment :

1. que le modèle soit valide dans les deux langages ;
2. que AIC et BIC s'améliorent suffisamment ;
3. que les diagnostics soient au moins aussi bons ;
4. que le score de représentation des queues, `tail_quantile_rmse`, s'améliore
   dans les deux langages.

La condition 4 n'est pas satisfaite.

En R :

- Normal : tail RMSE ≈ 0,1511
- Student-t : tail RMSE ≈ 0,1551

Student-t est légèrement moins bon.

En Python :

- Normal : ≈ 0,1495
- Student-t : ≈ 0,1393

Student-t est meilleur.

Comme l'amélioration n'apparaît pas dans les deux langages, la règle commune
de supériorité Student-t n'est pas satisfaite.

Nous conservons donc GARCH(1,1)-Normal comme spécification partagée
verrouillée.

Il faut toutefois documenter une limite importante :

**Student-t obtient une vraisemblance et des critères AIC/BIC nettement
meilleurs, donc le choix de Normal dépend fortement de la règle de sélection
pré-déclarée.**

Nous ne devons donc pas conclure que la loi normale représente forcément
mieux les queues de la distribution.

---

## 7. Do standardized residuals still show autocorrelation?

Après estimation GARCH, nous étudions les résidus standardisés :

z_t = epsilon_t / sigma_t

Pour le modèle Normal retenu, les tests Ljung-Box donnent en R :

- lag 10 : p ≈ 0,220
- lag 20 : p ≈ 0,419

et en Python :

- lag 10 : p ≈ 0,223
- lag 20 : p ≈ 0,425

Toutes les p-values sont supérieures à 0,05.

Nous ne rejetons donc pas l'hypothèse d'absence d'autocorrélation résiduelle
aux horizons testés.

Le modèle de moyenne et de variance semble donc avoir supprimé l'essentiel
de la structure linéaire détectable dans les innovations standardisées.

---

## 8. Do standardized squared residuals still show ARCH effects?

C'est l'un des diagnostics les plus importants.

Si GARCH a correctement capturé la dynamique de volatilité, les carrés des
résidus standardisés ne devraient plus présenter une dépendance importante.

Les tests Ljung-Box sur z_t² donnent des p-values très élevées.

Pour GARCH-Normal en R :

- lag 10 : p ≈ 0,904
- lag 20 : p ≈ 0,994

Les tests ARCH-LM post-GARCH donnent également :

- lag 5 : p ≈ 0,891
- lag 10 : p ≈ 0,966
- lag 20 : p ≈ 0,998

Les résultats Python sont pratiquement identiques.

Nous ne rejetons donc plus l'hypothèse d'absence d'effets ARCH.

C'est une amélioration majeure par rapport au pré-GARCH, où les p-values
étaient extrêmement faibles.

Nous concluons donc que GARCH(1,1) capture correctement l'essentiel de la
dynamique de variance conditionnelle détectée dans les données TRAIN.

---

## 9. Was a higher GARCH order justified?

Non.

La règle pré-déclarée autorisait l'ouverture de modèles GARCH plus complexes
uniquement si GARCH(1,1) laissait encore :

- des effets ARCH significatifs ;
- ou une dépendance significative des résidus standardisés au carré.

Ce n'est pas le cas.

Le higher-order gate est donc :

**FALSE**

Aucun GARCH(2,1), GARCH(1,2) ou GARCH(2,2) n'a été estimé.

Ce choix respecte le principe de parcimonie :

un modèle plus complexe n'est pas nécessaire lorsqu'un GARCH(1,1) fournit
déjà des diagnostics satisfaisants.

---

## 10. What does conditional volatility show through time?

La volatilité conditionnelle estimée varie fortement au cours du temps.

Elle augmente pendant les périodes de grands mouvements et diminue pendant
les périodes plus calmes.

Cela correspond au phénomène de volatility clustering observé dès la Phase 2.

Le modèle GARCH transforme donc ce phénomène visuel en une estimation
quantitative de sigma_t pour chaque séance.

Il faut toutefois noter que les sigmas historiques de cette phase sont
estimés à partir de paramètres ajustés sur tout TRAIN.

Ils doivent donc être interprétés comme des estimations rétrospectives
in-sample et non comme des prévisions historiques réellement disponibles
en temps réel à chaque date.

---

## 11. What does the h=10 volatility forecast mean?

À partir de la dernière observation TRAIN, le 14/11/2025, nous avons prévu la
variance conditionnelle jusqu'à 10 séances.

Pour la spécification verrouillée GARCH(1,1)-Normal, à h=10 :

### R

- variance ≈ 10,0552 points de pourcentage²
- sigma quotidienne ≈ 3,1710 %

### Python

- variance ≈ 10,0390
- sigma quotidienne ≈ 3,1684 %

Les deux langages donnent donc une prévision très proche.

La valeur d'environ 3,17 % signifie que le modèle anticipe une volatilité
conditionnelle quotidienne d'environ 3,17 % à cet horizon.

Cela ne signifie PAS :

- que NVDA va gagner 3,17 % ;
- que NVDA va perdre 3,17 %.

GARCH prévoit l'ampleur conditionnelle du risque, pas la direction du prix.

Cette prévision est produite uniquement depuis la fin de TRAIN.

Aucune réalisation du holdout final n'a été utilisée.

---

## 12. Are R and Python consistent?

Oui, les résultats sont très proches.

Pour GARCH-Normal :

R :
- omega ≈ 0,4417
- alpha ≈ 0,1126
- beta ≈ 0,8516

Python :
- omega ≈ 0,4371
- alpha ≈ 0,1116
- beta ≈ 0,8529

Les persistances sont presque identiques :

- R ≈ 0,9642
- Python ≈ 0,9645

Les diagnostics post-GARCH donnent également les mêmes conclusions.

Les prévisions de volatilité h=10 sont :

- R ≈ 3,171 %
- Python ≈ 3,168 %

La réplication R/Python est donc très cohérente.

Une divergence reste toutefois visible dans la comparaison Normal / Student-t :
Python favorise davantage Student-t sur le score de queues, alors que R ne
montre pas cette amélioration.

Cette divergence est conservée explicitement.

---

## 13. What are the main limitations?

Plusieurs limites doivent être mentionnées.

Premièrement, l'estimation est réalisée en deux étapes :

1. estimation du filtre de moyenne ARMA(1,1) ;
2. estimation GARCH sur les innovations gelées.

L'incertitude liée à l'estimation de la moyenne n'est donc pas propagée dans
l'estimation de variance.

Deuxièmement, les distributions normales restent imparfaites pour représenter
les queues épaisses observées dans les rendements financiers.

Student-t améliore très fortement AIC/BIC, même si la règle de sélection
commune ne l'a pas retenue.

Troisièmement, le score de queues utilisé pour départager Normal et Student-t
est descriptif et in-sample ; ce n'est pas un test de calibration hors
échantillon.

Quatrièmement, les sigmas historiques utilisent des paramètres estimés sur
l'ensemble de TRAIN et sont donc rétrospectifs.

Cinquièmement, aucune performance finale de volatilité n'a encore été mesurée
sur le holdout.

Enfin, GARCH modélise la volatilité conditionnelle et non la direction du prix.

La conclusion principale de cette phase est :

> Les rendements NVDA présentent une forte hétéroscédasticité conditionnelle.
> Un GARCH(1,1) capture efficacement cette dynamique puisque les effets ARCH
> disparaissent dans les résidus standardisés. La volatilité reste très
> persistante, avec alpha + beta proche de 0,964 pour le modèle Normal retenu.
> Student-t améliore fortement l'ajustement global mais n'est pas retenue par
> la règle commune pré-déclarée car son score de queues ne s'améliore pas dans
> les deux langages.
