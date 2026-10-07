# Human Interpretation — Phase 3A

> Team working interpretation. This text is intended to be reviewed,
> understood and reformulated by the team before the final submission.

## 1. Why d=1?

Dans cette phase, nous avons choisi de modéliser le logarithme du prix ajusté
de NVDA avec un modèle ARIMA.

Un modèle ARIMA est noté ARIMA(p,d,q) :

- `p` représente le nombre de termes autorégressifs ;
- `d` représente le nombre de différenciations nécessaires ;
- `q` représente le nombre de termes de moyenne mobile liés aux innovations
  passées.

Le choix de `d=1` ne vient pas simplement d'un algorithme automatique.

En Phase 2, les tests ADF et KPSS ont montré que le log-prix de NVDA présente
des caractéristiques de non-stationnarité. Pour le log-prix, la p-value ADF
est d'environ 0,461, ce qui ne permet pas de rejeter l'hypothèse de racine
unitaire, tandis que KPSS rejette la stationnarité.

En revanche, après une première différence, qui correspond au log-rendement
à un facteur 100 près, les diagnostics changent. L'ADF rejette fortement la
racine unitaire avec une p-value d'environ 7,9 × 10^-27, tandis que KPSS ne
rejette pas la stationnarité.

Les trois vérifications réalisées avec `ndiffs()` en R retournent également
une différenciation égale à 1.

Nous retenons donc `d=1` parce que les diagnostics statistiques indiquent que
le niveau du log-prix est non stationnaire alors que sa première différence
est compatible avec la stationnarité.

Ce choix a été réalisé avant la recherche automatique de `p` et `q`, ce qui
évite de laisser `auto.arima()` décider seul de toute la structure du modèle.

---

## 2. ACF/PACF and manual candidate choice

L'ACF mesure la corrélation entre une série et ses valeurs passées.

La PACF mesure la relation avec un retard particulier après avoir retiré
l'effet linéaire des retards intermédiaires.

Sur le log-prix NVDA non différencié, l'ACF reste très proche de 1 pendant
de nombreux retards. Cela correspond à une série très persistante et est
cohérent avec les résultats de non-stationnarité obtenus en Phase 2.

Après une différenciation, l'ACF et la PACF deviennent beaucoup plus proches
de zéro. Le premier retard présente une autocorrélation d'environ -0,0815,
et quelques autres pics apparaissent, mais aucun schéma très net ne permet
d'imposer directement un unique ordre AR ou MA.

Nous avons donc choisi de tester plusieurs modèles simples et interprétables :

- ARIMA(0,1,0) sans drift ;
- ARIMA(0,1,0) avec drift ;
- ARIMA(1,1,0) avec drift ;
- ARIMA(0,1,1) avec drift ;
- ARIMA(1,1,1) avec drift.

Le modèle ARIMA(0,1,0) correspond à une marche aléatoire et constitue une
référence simple.

Les autres modèles permettent d'ajouter progressivement une dépendance aux
variations passées ou aux innovations passées.

Le drift représente une variation moyenne du log-prix au cours du temps.
Il ne signifie pas que le prix doit augmenter à chaque séance.

Nous considérons donc l'ACF et la PACF comme des outils permettant de proposer
des candidats raisonnables, mais pas comme une méthode donnant automatiquement
un ordre unique `(p,q)`.

---

## 3. Manual vs automatic selection

Nous avons comparé deux approches.

La première approche consiste à construire manuellement quelques modèles
simples à partir des diagnostics ACF/PACF.

La seconde utilise des procédures automatiques :

- `auto.arima()` du package `forecast` en R ;
- `auto_arima()` de `pmdarima` en Python.

Ces méthodes automatiques explorent plusieurs combinaisons de `p` et `q` et
utilisent notamment des critères d'information comme AICc.

En R, `auto.arima()` sélectionne :

**ARIMA(2,1,2) avec drift.**

Ses critères sont approximativement :

- AIC = -7974,458 ;
- AICc = -7974,415 ;
- BIC = -7940,916.

Ce modèle constitue notre modèle pédagogique principal provisoire en R.

En Python, `auto_arima()` propose automatiquement :

**ARIMA(3,1,3) sans drift.**

Cependant, notre règle de sélection ne choisit pas automatiquement le modèle
ayant le plus petit AICc.

Le modèle Python ARIMA(1,1,1) avec drift possède :

- AIC = -7963,736 ;
- AICc = -7963,715 ;
- BIC = -7941,374.

Le modèle ARIMA(3,1,3) est meilleur selon AICc, mais son avantage est inférieur
à environ deux unités d'AICc par rapport à ARIMA(1,1,1).

L'écart est d'environ 1,98.

Notre règle considère donc les deux modèles comme suffisamment proches selon
AICc, puis privilégie le modèle utilisant moins de paramètres.

ARIMA(1,1,1) utilise quatre paramètres dans cette comparaison alors que
ARIMA(3,1,3) en utilise sept.

Python retient donc provisoirement :

**ARIMA(1,1,1) avec drift.**

Cette décision montre pourquoi nous ne devons pas utiliser `auto.arima()`
comme une boîte noire.

Les critères AIC, AICc et BIC mesurent un compromis entre ajustement et
complexité, mais ils ne mesurent pas directement la qualité des prévisions
hors échantillon.

La sélection reste donc provisoire et devra être complétée plus tard par une
validation temporelle.

---

## 4. Residual independence

Après estimation d'un modèle ARIMA, il faut vérifier si les résidus conservent
encore une dépendance temporelle.

Pour cela, nous avons utilisé le test de Ljung-Box.

L'hypothèse nulle est :

**H0 : absence d'autocorrélation globale des résidus jusqu'au retard étudié.**

Pour le modèle R ARIMA(2,1,2) avec drift :

- lag 10 : p-value ≈ 0,870 ;
- lag 20 : p-value ≈ 0,784.

Pour le modèle Python ARIMA(1,1,1) avec drift :

- lag 10 : p-value ≈ 0,067 ;
- lag 20 : p-value ≈ 0,118.

Toutes ces valeurs sont supérieures au seuil de 5 %.

Nous ne rejetons donc pas l'hypothèse d'absence d'autocorrélation résiduelle
aux horizons testés.

Les graphiques ACF des résidus donnent une conclusion cohérente : la majorité
des autocorrélations résiduelles sont faibles et ne montrent pas de structure
persistante importante.

Le résultat Python au lag 10 reste toutefois assez proche de 0,05. Nous
préférons donc rester prudents.

Nous ne disons pas que les résidus sont parfaitement indépendants.

Nous concluons plutôt que les diagnostics sont compatibles avec l'absence
d'une autocorrélation linéaire résiduelle importante aux lags 10 et 20.

Cela suggère que l'ARIMA a raisonnablement capturé une partie importante de
la dynamique linéaire de la moyenne.

---

## 5. Residual normality

Nous avons également vérifié si les résidus pouvaient être considérés comme
normalement distribués.

Le test utilisé est Jarque-Bera.

Son hypothèse nulle est :

**H0 : les résidus sont compatibles avec une distribution normale.**

Les statistiques obtenues sont très élevées :

- R : environ 1704,15 ;
- Python : environ 1776,11.

Les p-values calculées sont numériquement extrêmement proches de zéro.

Nous rejetons donc clairement l'hypothèse de normalité des résidus.

Les QQ-plots confirment cette conclusion.

Au centre de la distribution, plusieurs observations restent relativement
proches de la droite théorique. En revanche, dans les deux extrémités,
les points s'écartent fortement de cette droite.

Cela indique la présence de queues plus épaisses et d'observations extrêmes.

Ce résultat est cohérent avec l'analyse exploratoire de Phase 2, où les
rendements NVDA présentaient déjà une kurtosis excédentaire élevée et plusieurs
observations extrêmes.

Le rejet de la normalité constitue donc une limite importante.

Cependant, cela ne signifie pas automatiquement que le modèle ARIMA est
inutile pour représenter la dynamique de moyenne.

Cela signifie surtout que les hypothèses gaussiennes doivent être utilisées
avec prudence, notamment pour les intervalles de prévision, l'inférence et
certaines mesures d'incertitude.

---

## 6. ARCH effects

L'un des résultats les plus importants de cette phase concerne la variance
des résidus.

Nous avons réalisé un test ARCH-LM.

L'hypothèse nulle est :

**H0 : absence d'effets ARCH.**

Pour le modèle R, les p-values sont approximativement :

- lag 5 : 1,50 × 10^-12 ;
- lag 10 : 9,44 × 10^-12 ;
- lag 20 : 1,06 × 10^-10.

Pour le modèle Python :

- lag 5 : 1,10 × 10^-13 ;
- lag 10 : 1,02 × 10^-13 ;
- lag 20 : 2,03 × 10^-12.

Toutes ces valeurs sont très largement inférieures à 0,05.

Nous rejetons donc très fortement l'hypothèse d'absence d'effets ARCH.

Les graphiques des résidus au carré donnent la même impression : plusieurs
autocorrélations sont positives et dépassent les bandes de référence.

Ce résultat est cohérent avec ce que nous avions observé en Phase 2 avec le
volatility clustering.

Les résidus peuvent donc avoir peu d'autocorrélation linéaire alors que leur
amplitude reste dépendante dans le temps.

Autrement dit, le modèle ARIMA semble mieux représenter la dynamique de la
moyenne que celle de la variance.

Cela fournit une justification statistique pour étudier ultérieurement un
modèle GARCH.

Cependant, cette Phase 3A ne permet pas encore de choisir un ordre GARCH ni
de conclure qu'un GARCH améliorera forcément les prévisions.

Nous avons donc seulement identifié une motivation statistique forte pour
la future phase de volatilité.

---

## 7. R vs Python

Une partie intéressante du projet est que R et Python ne sélectionnent pas
exactement le même modèle.

En R, le modèle provisoire principal est :

**ARIMA(2,1,2) avec drift.**

En Python, le modèle provisoire indépendant est :

**ARIMA(1,1,1) avec drift.**

La recherche automatique Python avait également proposé ARIMA(3,1,3) sans
drift.

Nous avons vérifié que cette divergence ne vient pas de données différentes.

Les deux langages utilisent exactement les mêmes observations TRAIN, les
mêmes dates et les mêmes transformations.

Sur une même spécification ARIMA(1,1,1), les coefficients R et Python sont
également très proches.

La divergence semble donc provenir principalement des différences
d'implémentation, d'initialisation et d'optimisation.

Une analyse de sensibilité a été réalisée pour ARIMA(2,1,2) avec drift.

Avec l'initialisation Python par défaut, la log-vraisemblance est environ :

3985,91.

Lorsque Python est initialisé à partir des coefficients obtenus en R, la
log-vraisemblance devient environ :

3993,23,

soit pratiquement la même valeur que celle du modèle R :

3993,23.

Cela montre que l'optimisation est sensible au point de départ et qu'il peut
exister plusieurs optima locaux.

Cette vérification ne prouve toutefois pas que le modèle R correspond au
maximum global.

Elle dépend également du résultat R et ne constitue donc pas une réplication
Python totalement indépendante.

Nous avons choisi de conserver et de documenter cette divergence plutôt que
de forcer artificiellement les deux logiciels à produire exactement le même
résultat.

Malgré la différence des ordres, les conclusions principales sont les mêmes
dans les deux langages :

- pas d'autocorrélation linéaire résiduelle importante détectée aux lags
  étudiés ;
- normalité rejetée ;
- effets ARCH fortement présents.

---

## 8. Is the ARIMA model statistically acceptable?

Notre conclusion sur le modèle ARIMA doit rester nuancée.

Plusieurs éléments sont positifs.

Premièrement, la différenciation `d=1` est justifiée par les tests de
stationnarité et confirmée par `ndiffs()`.

Deuxièmement, nous n'avons pas imposé de SARIMA.

Les diagnostics réalisés sur TRAIN n'apportent pas suffisamment de preuves
d'une saisonnalité stable à cinq séances :

- `nsdiffs()` retourne 0 ;
- les autocorrélations aux lags saisonniers restent faibles ;
- la STL avec période 5 était exploratoire ;
- les différences entre jours de semaine ne fournissent pas de preuve
  statistique convaincante.

Nous conservons donc un ARIMA non saisonnier.

Troisièmement, les tests de Ljung-Box ne rejettent pas l'absence
d'autocorrélation résiduelle aux horizons étudiés.

Cela suggère que les modèles retenus décrivent raisonnablement la dynamique
linéaire de moyenne sur la période d'apprentissage.

Cependant, plusieurs limites importantes subsistent.

La normalité des résidus est fortement rejetée.

Les QQ-plots montrent des queues épaisses et des observations extrêmes.

De plus, ARCH-LM montre clairement que la variance conditionnelle n'est pas
correctement représentée par une variance constante.

Enfin, R et Python ne sélectionnent pas exactement le même ordre ARIMA, ce
qui montre une certaine sensibilité de l'estimation et de l'optimisation.

Nous considérons donc le modèle ARIMA comme :

**un modèle provisoirement acceptable pour représenter la dynamique linéaire
de la moyenne, mais incomplet pour représenter la variance conditionnelle.**

Nous ne pouvons pas encore dire qu'ARIMA est le meilleur modèle de prévision.

Aucune comparaison prédictive finale sur le holdout n'a été réalisée.

Le jeu de test final a volontairement été protégé pendant toute cette phase,
avec 14 contrôles anti-leakage validés.

La suite du projet devra donc conserver deux idées distinctes :

1. évaluer ultérieurement si le modèle ARIMA fournit réellement de bonnes
   prévisions hors échantillon ;
2. étudier séparément la dynamique de volatilité puisque les effets ARCH
   restent très importants.

La conclusion centrale de cette Phase 3A est donc :

> ARIMA semble capturer raisonnablement la dynamique linéaire de moyenne de
> NVDA, mais il ne décrit pas complètement la distribution ni la variance
> conditionnelle de ses innovations.