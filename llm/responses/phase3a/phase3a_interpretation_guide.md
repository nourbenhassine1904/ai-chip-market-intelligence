# Phase 3A — Guide pédagogique d’interprétation

Ce guide explique les résultats déjà produits pour NVDA. Il repose sur la
[documentation Phase 3A](phase3a_arima_identification.md), les 34 tables
`outputs/tables/phase3_*.csv`, les 12 figures Phase 3 et la lecture des scripts
[Python](../python/02_arima.py) et [R](../r/02_arima.R).
Aucun modèle, test statistique ou résultat prédictif supplémentaire n’a été
calculé pour le rédiger. Les valeurs présentées sont celles des sorties
existantes, parfois arrondies pour faciliter la lecture.

Le travail porte exclusivement sur les 1 980 observations TRAIN, du
2018-01-02 au 2025-11-14. R est l’implémentation pédagogique de référence ;
Python constitue une réplication indépendante. Leurs modèles sélectionnés
restent des **provisional selected mean models**, c’est-à-dire des modèles
de moyenne retenus provisoirement, sans validation prédictive.

Le fichier d’interprétation humaine reste réservé à l’équipe. Ce document
donne les éléments nécessaires pour comprendre et discuter les résultats.

## 1. Why d = 1?

### Comprendre AR, I et MA

Dans **ARIMA(p,d,q)**, les trois lettres décrivent des rôles différents :

| Partie | Signification | Intuition |
| --- | --- | --- |
| AR, ordre `p` | Autorégression | La variable stationnaire dépend linéairement de ses `p` valeurs passées. |
| I, ordre `d` | Intégration, traitée par différenciation | On applique `d` différences pour travailler sur une série dont la stationnarité est plausible. |
| MA, ordre `q` | Moyenne mobile des innovations | La variable dépend de l’innovation actuelle et des `q` innovations passées. |

Une innovation est la partie inattendue de l’observation, compte tenu du
modèle et du passé. La partie MA ne désigne pas une moyenne glissante des
prix comme un indicateur de trading : elle porte sur les chocs du modèle.

Notre série est `y_t = log(NVDA Adjusted Close_t)`. Avec `d=1`, on modélise
la dynamique de `x_t = y_t - y_(t-1)`. C’est le log-rendement quotidien
**divisé par 100**, puisque la Phase 2 exprime les log-rendements en pourcent.
Les 1 980 log-prix donnent donc 1 979 différences.

Le logarithme change l’échelle ; la différence retire l’accumulation des
variations dans le niveau. Ce sont deux opérations distinctes. Prendre le
logarithme ne rend pas automatiquement une série stationnaire.

### Ce que disent les diagnostics existants

Une série faiblement stationnaire possède notamment une moyenne et une
structure de covariance qui ne dépendent pas de la date. ADF et KPSS
apportent ici des indices complémentaires, avec des hypothèses nulles
différentes : ADF teste une racine unitaire ; KPSS teste la stationnarité
autour des termes déterministes spécifiés.

| Série NVDA sur TRAIN | ADF | KPSS | Lecture conjointe |
| --- | --- | --- | --- |
| Log_Price | p=0,461103 : racine unitaire non rejetée | p affichée=0,01, valeur réelle plus petite : stationnarité rejetée | Non-stationnarité soutenue |
| Log_Return | p=7,91143e-27 : racine unitaire rejetée | p affichée=0,10, valeur réelle plus grande : stationnarité non rejetée | Stationnarité soutenue |

Les tests Phase 2 incluent constante et tendance pour le log-prix, une
constante pour les rendements. Les p-values KPSS de bord sont des bornes,
pas des probabilités exactes. Ne pas rejeter une hypothèse ne la prouve pas.

Comme `Log_Return = 100 × première différence du log-prix`, ces résultats
soutiennent une différenciation : **`d=1` est cohérent**, sans démontrer que
le processus réel est exactement un ARIMA intégré d’ordre un.

### Le rôle de ndiffs()

R utilise `forecast::ndiffs()` comme vérification auxiliaire. Les trois
spécifications exportées — KPSS niveau, KPSS tendance, ADF tendance —
donnent toutes **1**. La table conserve séparément la conclusion Phase 2,
le résultat auxiliaire et `final_d=1`.

L’automatisme ne remplace pas la justification : le résultat dépend du test,
des termes déterministes, des retards et de la période. Différencier trop
peut créer une dépendance artificielle et perdre de l’information ; ne pas
différencier suffisamment peut laisser une dynamique non stationnaire.
Ici, `d=1` est fixé avant la recherche automatique des ordres AR/MA.

Sources : [évidence Phase 2 reprise en Phase 3](../outputs/tables/phase3_d_phase2_evidence.csv)
et [vérifications ndiffs](../outputs/tables/phase3_d_justification_r.csv).

## 2. ACF / PACF : lire la mémoire de la série

L’**ACF** au retard `k` mesure la corrélation entre une observation et celle
située `k` séances plus tôt. Cette association peut passer par les retards
intermédiaires. La **PACF** mesure l’association linéaire restante une fois
les retards 1 à `k-1` pris en compte. Ce ne sont pas des mesures de causalité.

L’ACF du log-prix reste visuellement proche de un à de nombreux retards.
Deux niveaux successifs partagent presque toute leur histoire accumulée :
leur forte corrélation ne signifie pas que les rendements sont aisément
prévisibles. Cette persistance est cohérente avec les diagnostics de
non-stationnarité ; le graphique seul ne suffit pas à les remplacer.

La première différence représente la variation entre deux séances. Elle
retire cette accumulation et son ACF est beaucoup plus proche de zéro.
Il reste toutefois des associations faibles mais détectables.

| Retard, en séances | ACF des différences | PACF des différences |
| ---: | ---: | ---: |
| 1 | -0,081476 | -0,081476 |
| 2 | 0,047813 | 0,041449 |
| 3 | -0,037549 | -0,030693 |
| 5 | 0,014469 | 0,014759 |
| 7 | 0,055862 | 0,051107 |
| 8 | -0,045153 | -0,035200 |
| 9 | 0,046479 | 0,035657 |
| 10 | -0,025300 | -0,013103 |
| 15 | -0,026976 | -0,020160 |
| 20 | 0,021551 | 0,026894 |

La borne indicative à 95 % est environ ±0,044059, **pour chaque retard
pris séparément**. Examiner vingt retards multiplie les occasions de voir
un dépassement par hasard. Le pic négatif au retard 1 suggère une faible
dépendance linéaire de court terme ; il n’impose pas un ordre précis.

Pour des processus stationnaires idéaux, une PACF qui s’interrompt après
`p` peut suggérer un AR(p), et une ACF qui s’interrompt après `q` peut
suggérer un MA(q). Sur des observations finies, ces coupures sont rarement
nettes. Un ARMA peut faire décroître les deux fonctions progressivement.
Ici, les signaux motivent des candidats de faible ordre, puis une comparaison
des critères et des résidus. Ils ne justifient ni un ordre sept à partir du
pic au lag 7, ni une saisonnalité hebdomadaire.

Sources : [valeurs numériques](../outputs/tables/phase3_acf_pacf_numeric.csv),
[ACF/PACF du log-prix](../outputs/figures/phase3/nvda_log_price_acf_pacf_train.png),
[ACF/PACF des différences](../outputs/figures/phase3/nvda_delta_log_price_acf_pacf_train.png)
et [version R en quatre panneaux](../outputs/figures/phase3/nvda_log_price_acf_pacf_train_r.png).

## 3. Manual candidates : ce que chaque modèle suppose

### Drift et dynamique de court terme

Pour `d=1`, le **drift** représente une variation moyenne du log-prix par
séance. Dans ces spécifications, il correspond à la moyenne de long terme
de la différence, lorsque la partie ARMA est stationnaire. Un drift positif
ne signifie pas que chaque séance est positive : les chocs peuvent être
bien plus grands que cette moyenne.

La formulation pédagogique est `x_t = µ + u_t`, où `x_t` est la différence
du log-prix, `µ` le drift et `u_t` une dynamique ARMA autour de zéro.
Les paramètres AR portent donc sur les différences centrées ; les paramètres
MA portent sur les innovations passées.

| Candidat manuel | Intuition après une différence | Drift | Paramètres `k`, variance comprise |
| --- | --- | --- | ---: |
| ARIMA(0,1,0) sans drift | `y_t = y_(t-1) + ε_t` : marche aléatoire sans variation moyenne imposée | Non | 1 |
| ARIMA(0,1,0) avec drift | `y_t = y_(t-1) + µ + ε_t` : marche aléatoire avec variation moyenne | Oui | 2 |
| ARIMA(1,1,0) | La différence centrée dépend de sa valeur à la séance précédente | Oui dans les scripts | 3 |
| ARIMA(0,1,1) | La différence centrée dépend du choc actuel et du choc précédent | Oui dans les scripts | 3 |
| ARIMA(1,1,1) | Une différence passée et un choc passé décrivent ensemble la mémoire de court terme | Oui dans les scripts | 4 |

Les deux marches aléatoires servent de références simples. Les trois autres
modèles comparent des façons de représenter la faible dépendance observée.
Les cinq estimations manuelles convergent dans les deux langages. Cela
confirme l’aboutissement numérique, pas la validité statistique de chaque
spécification : les marches aléatoires laissent de l’autocorrélation résiduelle.

### Autres ordres effectivement explorés

Les recherches automatiques ont examiné les 16 couples `p,q` allant de 0 à
3, avec `d=1`, chacun sans puis avec drift. Les variantes sans drift des
ordres AR(1), MA(1) et ARMA(1,1) ont donc aussi été tentées. Les douze ordres
supplémentaires, au-delà des quatre ordres distincts du tableau manuel, sont :

| Ordre ARIMA | Intuition, toujours sur les différences centrées |
| --- | --- |
| (0,1,2) | Aucun terme AR ; deux chocs passés MA |
| (0,1,3) | Aucun terme AR ; trois chocs passés MA |
| (1,1,2) | Une différence passée et deux chocs passés |
| (1,1,3) | Une différence passée et trois chocs passés |
| (2,1,0) | Deux différences passées, sans terme MA |
| (2,1,1) | Deux différences passées et un choc passé |
| (2,1,2) | Deux différences passées et deux chocs passés |
| (2,1,3) | Deux différences passées et trois chocs passés |
| (3,1,0) | Trois différences passées, sans terme MA |
| (3,1,1) | Trois différences passées et un choc passé |
| (3,1,2) | Trois différences passées et deux chocs passés |
| (3,1,3) | Trois différences passées et trois chocs passés |

Pour chacun, la version avec drift autorise une moyenne `µ` ; la version
sans drift fixe cette moyenne à zéro. Ces ordres appartiennent à la recherche
automatique et ne constituent pas douze candidats manuels supplémentaires.

Les traces R rejettent les deux tentatives `(3,1,3)` avec un critère `Inf`.
Les sorties Python conservent deux tentatives non convergentes, `(1,1,0)`
et `(0,1,1)` sans drift ; elles sont exclues de la sélection automatique.
Une tentative réalisée ne doit pas être décrite comme une estimation réussie.

Sources : [candidats manuels Python](../outputs/tables/phase3_arima_manual_candidates_python.csv),
[candidats manuels R](../outputs/tables/phase3_arima_manual_candidates_r.csv),
[recherche Python](../outputs/tables/phase3_auto_arima_python.csv)
et [trace R](../outputs/tables/phase3_auto_arima_trace_r.csv).

## 4. Auto.arima R vs Python : comprendre les trois décisions

Il faut distinguer une proposition issue d’un critère automatique et la
sélection provisoire après diagnostics. La recherche est bornée et lisible :
`d=1`, `p,q <= 3`, absence de composante saisonnière, recherche non stepwise,
AICc comme critère automatique. R désactive aussi l’approximation.

| Étape | Résultat réel |
| --- | --- |
| `forecast::auto.arima` en R | ARIMA(2,1,2) avec drift |
| Recherche `pmdarima.auto_arima` en Python, après filtrage de convergence | ARIMA(3,1,3) sans drift |
| Sélection provisoire Python après application de la règle du projet | ARIMA(1,1,1) avec drift |
| Sélection provisoire R, référence pédagogique | ARIMA(2,1,2) avec drift |

Le meilleur modèle de la recherche Python **avec** drift est `(0,1,3)`.
Le meilleur des deux ensembles de recherche, avec et sans drift, est toutefois
`(3,1,3)` sans drift. C’est ce dernier qui porte `selected_by_auto=True`.

### La règle exacte, vérifiée dans le code

`select_candidate()` dans Python, et le bloc `valid / adequate / near` dans
R, appliquent la règle suivante :

1. Garder les estimations convergentes avec AICc et BIC finis.
2. Privilégier celles dont les deux Ljung–Box donnent `p >= 0.05`. Si aucune
   ne satisfait ces conditions, le code revient aux estimations valides,
   avec des diagnostics qui resteraient insuffisants.
3. Garder les modèles situés à au plus **deux unités d’AICc** du meilleur
   de cet ensemble admissible.
4. Trier d’abord par nombre de paramètres `k`, puis par BIC, AICc et identifiant
   du modèle pour départager les égalités.

La sélection provisoire Python porte sur **les cinq candidats manuels plus
le seul gagnant automatique**, réestimé avec statsmodels. Elle ne refait pas
une sélection diagnostique sur les 32 lignes de la recherche automatique.
Le modèle R `(2,1,2)` et les ajustements de sensibilité n’entrent pas dans
cette sélection Python indépendante.

### Application aux deux modèles Python encore admissibles

Les marches aléatoires, AR(1) et MA(1) échouent au Ljung–Box à lag 10.
Parmi les six lignes du pool Python, les deux suivantes passent les deux
contrôles :

| Modèle dans le pool statsmodels | Convergence | AICc | BIC | `k` | p LB10 | p LB20 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| (1,1,1) avec drift | Oui | -7963,715481 | -7941,374357 | 4 | 0,067465 | 0,118122 |
| (3,1,3) sans drift, réestimation du gagnant automatique | Oui | -7965,698022 | -7926,622418 | 7 | 0,570307 | 0,611709 |

Le modèle `(3,1,3)` possède le meilleur AICc. Mais l’écart avec `(1,1,1)`
est environ **1,98254**, donc inférieur à deux. Les deux restent admissibles,
et le tri retient **quatre paramètres plutôt que sept**. Le BIC favorise
aussi `(1,1,1)`, mais intervient après `k` dans le code : ce n’est pas lui
qui départage en premier ces deux modèles.

**Le modèle automatique n’a donc pas été éliminé pour nonconvergence ou
échec résiduel. Le choix final Python découle de la fenêtre AICc de deux
unités, puis de la parcimonie.** Le gagnant automatique passe même les tests
avec des p-values plus élevées ; maximiser ces p-values n’est pas la règle
de sélection, et une p-value plus grande ne mesure pas une meilleure prévision.

Le CSV pmdarima affiche AICc=-7965,698051 pour `(3,1,3)`. Le pool de sélection
statsmodels affiche -7965,698022, car sa correction utilise un effectif
différent. Il faut employer la seconde valeur pour expliquer la décision
du pool. Cette différence minuscule ne modifie pas l’appartenance à la fenêtre.

### Pourquoi R conserve (2,1,2)

Dans le pool R, `(1,1,1)` avec drift et `(2,1,2)` avec drift passent tous deux
les Ljung–Box. Mais leurs AICc sont respectivement -7963,715534 et -7974,415400 :
le premier est à environ 10,70 unités du second, donc hors de la fenêtre de
deux. R conserve `(2,1,2)`, même si son BIC est légèrement moins favorable
que celui du modèle manuel plus simple.

La justification du choix Python est donc explicite dans le code et les
tables : elle ne nécessite pas le statut « needs clarification before
Phase 3A validation ». Il reste une **vigilance** : 1,98254 est très proche
de la limite de deux. Cette règle est un choix de méthode, pas une loi
statistique, et ne prouve aucune supériorité prédictive.

Sources : fonction `select_candidate()` et construction du pool dans
[Python](../python/02_arima.py), bloc de sélection dans [R](../r/02_arima.R),
[pool Python](../outputs/tables/phase3_arima_selection_pool_python.csv),
[pool R](../outputs/tables/phase3_arima_selection_pool_r.csv)
et [comparaison globale](../outputs/tables/phase3_arima_selection_comparison.csv).

Dans la comparaison globale, `selected_candidate` identifie l’ordre retenu
par langage ; une même spécification peut apparaître comme estimation
manuelle et estimation automatique. Cela ne signifie pas que deux modèles
Python différents ont été retenus. `selected_by_auto` désigne le gagnant
du critère automatique, ce qui est une autre information.

## 5. AIC / AICc / BIC : ajustement et parcimonie

Ajouter des paramètres peut améliorer l’ajustement sur TRAIN, y compris en
capturant du bruit. Les critères d’information mettent en balance cet
ajustement, via la log-vraisemblance `ℓ`, et une pénalité de complexité.
Pour les conventions utilisées ici :

```text
AIC  = -2ℓ + 2k
AICc = AIC + 2k(k+1)/(n-k-1)
BIC  = -2ℓ + k log(n)
```

`k` comprend les paramètres AR/MA, le drift éventuel et la variance des
innovations. AICc ajoute une correction lorsque l’effectif est limité par
rapport au nombre de paramètres. BIC pénalise davantage les paramètres
dans notre échantillon.

**Plus faible est généralement préférable**, lorsque les modèles sont
comparables : mêmes observations, même variable et conventions compatibles.
Pour des nombres négatifs, -7974 est plus faible que -7963. Un critère négatif
n’est pas une erreur : la vraisemblance porte sur une densité continue et
les valeurs absolues dépendent aussi de l’échelle utilisée.

| Modèle provisoire | AIC | AICc | BIC |
| --- | ---: | ---: | ---: |
| R : (2,1,2), drift | -7974,458 | -7974,415 | -7940,916 |
| Python : (1,1,1), drift | -7963,736 | -7963,715 | -7941,374 |

L’AIC/AICc favorise ici l’ajustement R `(2,1,2)` ; le BIC favorise légèrement
le Python `(1,1,1)`, plus simple. Dans le même langage R, la comparaison
avec son propre `(1,1,1)` donne également ce désaccord AICc/BIC. Il ne s’agit
donc pas simplement d’une différence d’arrondi entre logiciels.

Ces critères ne sont ni des erreurs de prévision ni des p-values. Le meilleur
AIC n’assure ni la convergence vers un optimum global, ni l’absence
d’autocorrélation, ni la normalité, ni la stabilité de la variance. La
parcimonie réduit la complexité quand l’amélioration d’ajustement est limitée,
mais ne dispense pas des diagnostics ou d’une validation prédictive future.

Pour les ajustements manuels R/statsmodels, `n=1979` après différenciation.
Pour l’AICc pmdarima exporté, `aicc_package_nobs=1980`. Les petites différences
correspondantes sont documentées ; elles n’expliquent pas les écarts de
vraisemblance de plusieurs unités entre optimisations.

## 6. Seasonality gate : pourquoi aucun SARIMA ?

Un SARIMA ajoute une structure répétée à une période donnée. Cette complexité
doit répondre à une saisonnalité crédible, et pas seulement à la possibilité
technique d’estimer des paramètres supplémentaires.

| Élément existant | Résultat | Ce qu’il apporte |
| --- | --- | --- |
| Hypothèse STL Phase 2, période 5 ; recomputations exportées en Phase 3 | Force saisonnière tronquée à zéro dans les deux langages | La composante dessinée ne démontre pas un cycle stable |
| ACF des différences aux lags 5 / 10 / 15 / 20 | 0,014469 / -0,025300 / -0,026976 / 0,021551 | Aucun dépassement de la borne corrigée ±0,056146 |
| `nsdiffs`, fréquence 5 | 0 avec `seas`, et 0 avec OCSB | Pas de différence saisonnière recommandée par ces contrôles auxiliaires |
| Analyse des jours de semaine | Moyennes différentes descriptivement ; ANOVA auxiliaire p=0,431880 | Pas d’élément convaincant de différence des moyennes ; limites liées aux queues et variances |

Les moyennes quotidiennes de log-rendement Phase 2 sont 0,211997 % lundi,
0,255431 % mardi, 0,262920 % mercredi, 0,286513 % jeudi et -0,095332 % vendredi.
La valeur négative du vendredi ne suffit pas à démontrer un effet systématique.
Il faut tenir compte de la dispersion et de l’incertitude.

STL produit une composante saisonnière parce qu’on lui demande une
décomposition à période cinq. L’existence de cette composante n’est donc
pas une preuve autonome. Inversement, `nsdiffs=0` ne prouve pas l’absence
de toute saisonnalité : il concerne la nécessité d’une différenciation
saisonnière, et des effets calendaires pourraient avoir une autre forme.

Le code prévoit un gate conservateur combinant force saisonnière, plusieurs
ACF saisonnières, analyse weekday et, en R, `nsdiffs`. Ici, les éléments vont
tous dans le sens d’une preuve insuffisante : **`sarima_justified=FALSE`**.
Aucun modèle SARIMA n’a donc été estimé.

La période cinq représente **cinq séances observées**, pas cinq jours
calendaires. Les jours fériés empêchent d’assimiler automatiquement une
périodicité de cinq observations à un même jour de la semaine.

Sources : [gate consolidé](../outputs/tables/phase3_seasonality_gate.csv)
et [gate R](../outputs/tables/phase3_seasonality_gate_r.csv).
Le fichier intermédiaire Python garde le texte « pending R execution » pour
`nsdiffs` ; ce n’est pas un diagnostic R manquant dans le résultat consolidé,
qui contient bien les deux valeurs nulles exportées par R.

## 7. Ljung–Box : reste-t-il une mémoire linéaire dans les résidus ?

Les résidus sont les innovations estimées du modèle. S’ils gardent une
autocorrélation importante, une partie de la dynamique de moyenne reste
potentiellement inexpliquée.

**H0 : absence d’autocorrélation globale des résidus jusqu’au retard testé.**
À lag 10, on examine conjointement les retards 1 à 10, pas uniquement le
retard 10. Le même principe vaut pour lag 20.

| Modèle provisoire | p-value lag 10 | p-value lag 20 | Décision au seuil 5 % |
| --- | ---: | ---: | --- |
| R (2,1,2), drift | 0,869791 | 0,784385 | H0 non rejetée aux deux horizons |
| Python (1,1,1), drift | 0,067465 | 0,118122 | H0 non rejetée aux deux horizons |

Une p-value décrit la compatibilité de la statistique observée avec H0,
sous les hypothèses du test. **Elle n’est pas la probabilité que H0 soit vraie.**
Avec le seuil fixé à 0,05, `p > 0.05` ne fournit pas assez d’éléments pour
rejeter H0. On peut donc dire « diagnostic compatible avec l’absence
d’autocorrélation linéaire globale aux horizons examinés ».

Les degrés de liberté tiennent compte de `p+q` : 6 et 16 pour R, 8 et 18
pour Python aux lags 10 et 20. Drift et variance ne sont pas soustraits dans
ce réglage. Les tests formels portent sur 1 979 innovations, après exclusion
de la première innovation d’initialisation dans les deux langages.

Ce résultat ne rend pas le modèle parfait : on ne teste pas toutes les
dépendances, tous les horizons ou les performances futures. Le p=0,067465
Python est proche du seuil retenu. Les effets ARCH et les queues épaisses
limitent aussi la lecture des tests asymptotiques usuels. Enfin, ces diagnostics
ont participé à la sélection : ils ne constituent pas une validation indépendante.

La colonne `white_noise_mean_supported=True` doit être lue comme une synthèse
des seuls contrôles de corrélation de la moyenne. Elle ne prouve pas que les
résidus soient indépendants, gaussiens ou de variance conditionnelle constante.

Sources : [diagnostics R](../outputs/tables/phase3_arima_residual_diagnostics_r.csv)
et [diagnostics Python](../outputs/tables/phase3_arima_residual_diagnostics_python.csv).

## 8. Jarque–Bera : la distribution des résidus est-elle normale ?

**H0 : normalité des résidus.** Jarque–Bera utilise l’asymétrie et la
kurtosis : une distribution normale a une asymétrie nulle et une kurtosis
égale à trois, soit un excès de kurtosis nul.

| Modèle provisoire | Statistique Jarque–Bera | p-value enregistrée |
| --- | ---: | ---: |
| R (2,1,2), drift | 1704,152267 | 0 numérique |
| Python (1,1,1), drift | 1776,106839 | 0 numérique |

Ces très grandes statistiques conduisent à rejeter la normalité. Les zéros
proviennent du sous-flux numérique pour des probabilités extrêmement petites ;
il ne faut pas dire que la probabilité mathématique est exactement zéro.

Les deux QQ-plots montrent des extrémités beaucoup plus éloignées de la
droite normale que le centre. Cela concorde avec les queues épaisses et les
observations extrêmes décrites en Phase 2. Jarque–Bera seul ne permet pas
d’identifier une loi alternative précise ni de séparer exactement l’effet
de l’asymétrie de celui des queues.

Une moyenne conditionnelle ARIMA peut rester utile même si les innovations
ne sont pas normales. La qualité d’une prévision ponctuelle dépend aussi de
la spécification de la moyenne. **Son utilité n’est toutefois pas démontrée
ici**, puisque la validation prédictive n’a pas eu lieu. Les hypothèses
gaussiennes derrière certains intervalles, tests et erreurs standards sont
fragilisées ; la vraisemblance utilisée et cette limite doivent être signalées.
Une hétéroscédasticité conditionnelle peut également contribuer à des queues
épaisses dans la distribution non conditionnelle des résidus.

## 9. ARCH-LM : la taille des erreurs garde-t-elle une mémoire ?

**H0 : absence d’effets ARCH jusqu’à l’ordre testé.** Intuitivement, on
cherche si les résidus au carré peuvent être expliqués par leurs valeurs
passées. Au lag 5, le test utilise les cinq premiers retards des carrés ;
il ne porte pas exclusivement sur le retard cinq.

| Nombre de retards | p-value R | p-value Python |
| ---: | ---: | ---: |
| 5 | 1,50217e-12 | 1,09996e-13 |
| 10 | 9,44313e-12 | 1,02156e-13 |
| 20 | 1,06283e-10 | 2,02698e-12 |

Ces valeurs sont très inférieures à 0,05 pour les deux modèles. On rejette
fortement l’absence d’effets ARCH aux trois ordres examinés. Les résultats
soutiennent une dépendance de la variance conditionnelle : la taille des
chocs est liée au passé, même lorsque leur signe reste difficile à prévoir.

C’est le lien avec le **volatility clustering** : des périodes de grandes
variations absolues se regroupent, comme les périodes de faibles variations.
Les ACF des rendements au carré de Phase 2 suggéraient ce phénomène ; les
ACF des résidus au carré Phase 3 montrent qu’il reste présent après estimation
du modèle de moyenne. ARCH-LM apporte ici un diagnostic formel supplémentaire.

Il n’y a pas de contradiction avec Ljung–Box : une série peut être peu
autocorrélée alors que son carré l’est. De même, des effets ARCH peuvent
exister dans un processus stationnaire ; une variance **conditionnelle**
variable n’exige pas automatiquement une variance non conditionnelle instable.
ADF/KPSS ne constituent pas des tests d’absence d’ARCH.

R emploie `FinTS::ArchTest(demean=FALSE)` ; Python emploie `het_arch(ddof=0)`.
Ce choix rapproche les conventions du test LM sur les mêmes innovations.
Les résidus n’ont pas été filtrés par un modèle de variance.

Ces constats motivent l’**hypothèse d’un futur modèle GARCH**, qui pourrait
représenter une variance conditionnelle dynamique. Ils ne déterminent ni
son ordre, ni sa distribution d’innovations, ni son intérêt prédictif ;
ruptures ou autres mécanismes peuvent aussi produire une dépendance des carrés.
Aucune estimation GARCH n’a été faite dans cette phase ou pour ce guide.

## 10. Residual figures : comment lire les quatre diagnostics

Les figures sans suffixe décrivent le modèle R `(2,1,2)` avec drift.
Celles portant `_python` décrivent le modèle Python `(1,1,1)` avec drift.
Les titres précisent le modèle ; les différences visuelles ne doivent pas
être attribuées uniquement au langage, puisque les ordres ne sont pas les mêmes.

### 10.1 Résidus dans le temps

![Résidus du modèle R sur TRAIN](../outputs/figures/phase3/nvda_arima_residuals.png)

La courbe montre les innovations en unités de log-prix. Il faut regarder leur
centrage, les successions de signes, les périodes d’amplitude élevée et les
observations extrêmes. Les deux figures montrent des fluctuations autour de
zéro, avec des groupes plus agités et des pointes de grande amplitude.

La [figure Python](../outputs/figures/phase3/nvda_arima_residuals_python.png)
présente le même type de phénomène. Les moyennes déjà exportées sont
-0,0000223294 en R et 0,0000071808 en Python ; les écarts-types sont environ
0,032177 et 0,032298. Ces valeurs décrivent l’échantillon, sans démontrer que
la moyenne théorique est exactement nulle.

On peut relever visuellement un regroupement des amplitudes. On ne peut
pas prouver l’indépendance, attribuer les pointes à des événements économiques
précis ou identifier un ordre GARCH à partir de cette courbe seule. Les
résidus TRAIN ne sont pas des erreurs de prévision du holdout final.

### 10.2 ACF des résidus

![ACF des résidus R](../outputs/figures/phase3/nvda_arima_residual_acf.png)

Les barres représentent les corrélations résiduelles selon le retard.
On recherche une décroissance persistante ou une suite de pics structurée,
en tenant compte des bandes indicatives. Dans la figure R, les corrélations
sont faibles, généralement à l’intérieur des bandes, avec un dépassement
isolé autour du lag 40. Cela ne contredit pas automatiquement les tests
formels, qui portent ici sur les lags 10 et 20.

La [figure Python](../outputs/figures/phase3/nvda_arima_residual_acf_python.png)
montre aussi des corrélations faibles, avec quelques pics isolés, notamment
autour du lag 7. Son axe vertical va de -1 à 1, alors que l’axe R est beaucoup
plus resserré : il faut comparer les valeurs et les bandes, pas la seule
hauteur apparente des barres.

On peut conclure à une faible mémoire linéaire visible, compatible avec les
Ljung–Box non significatifs aux horizons retenus. On ne peut pas conclure
à une absence de toute dépendance, surtout celle des amplitudes, ni considérer
un dépassement isolé comme une preuve suffisante d’un nouvel ordre ARIMA.

### 10.3 QQ-plot normal

![QQ-plot des résidus R](../outputs/figures/phase3/nvda_arima_residual_qqplot.png)

L’axe horizontal contient les quantiles théoriques normaux et l’axe vertical
les résidus ordonnés. Une distribution proche d’une normale devrait suivre
approximativement la droite de référence. Il faut regarder le centre et,
surtout ici, les deux extrémités.

En R comme dans le [QQ-plot Python](../outputs/figures/phase3/nvda_arima_residual_qqplot_python.png),
la queue gauche passe nettement sous la droite et la queue droite au-dessus.
Les valeurs extrêmes dépassent celles attendues sous la référence normale.
La lecture est compatible avec des queues épaisses et le rejet Jarque–Bera.

Le graphique ne choisit pas une distribution de Student ou une autre loi à
notre place. Il ne décrit pas la succession temporelle des chocs et ne permet
pas, à lui seul, de diagnostiquer ARCH ou la qualité des prévisions futures.

### 10.4 ACF des résidus au carré

![ACF des résidus au carré R](../outputs/figures/phase3/nvda_arima_squared_residual_acf.png)

Les carrés éliminent le signe et accentuent les grandes amplitudes. On
cherche si une grande erreur tend à être suivie d’autres grandes erreurs,
et pas nécessairement d’erreurs du même signe.

Dans les deux figures, de nombreuses corrélations des carrés sont positives,
plusieurs dépassent les bandes indicatives, et la dépendance est plus visible
que dans l’ACF des résidus bruts. La [version Python](../outputs/figures/phase3/nvda_arima_squared_residual_acf_python.png)
utilise là aussi un axe plus large ; la lecture qualitative est similaire.
Cette persistance des amplitudes concorde avec ARCH-LM.

On peut soutenir la présence de dépendance dans la variance. On ne peut pas
identifier le meilleur modèle GARCH, son ordre, une loi d’innovations ou une
amélioration hors échantillon à partir de ces barres seules.

### 10.5 La figure pédagogique checkresiduals de R

La [figure checkresiduals](../outputs/figures/phase3/nvda_arima_checkresiduals_r.png)
combine les résidus dans le temps, leur ACF et un histogramme avec une
référence normale. Elle aide à lire simultanément dynamique et distribution.
Elle emploie la convention native R incluant l’innovation initiale, tandis
que les tables formelles l’excluent. Cela explique le léger écart du
Ljung–Box lag 20 annoncé par `checkresiduals` — environ 0,7842 — par rapport
à 0,784385 dans la table. Les conclusions sont identiques.

## 11. R vs Python : différence de résultat ou erreur ?

### Vérifier d’abord la comparabilité

Les manifestes existants indiquent les mêmes 1 980 lignes, mêmes dates et
même empreinte MD5 `23b4e319310d569b6f2ebb52c98539e7` pour TRAIN.
La différence ne vient donc pas de séries d’apprentissage différentes selon
les contrôles exportés. Les transformations et `d=1` sont également communs.

Une comparaison sur la même spécification manuelle `(1,1,1)` montre une
bonne proximité numérique :

| Coefficient | R | Python |
| --- | ---: | ---: |
| AR1 | -0,47041736 | -0,47198453 |
| MA1 | 0,38851955 | 0,39015882 |
| Drift | 0,0018439071 | 0,0018381295 |

Cela rend moins plausible une erreur générale de transformation ou de
convention de signe. Les coefficients de modèles d’ordres différents ne
doivent pas être comparés terme à terme comme s’ils estimaient les mêmes
paramètres.

### Pourquoi les recherches peuvent diverger

| Source possible | Ce qui est établi ou limité dans notre cas |
| --- | --- |
| Optimisation et initialisation | Même ordre `(2,1,2)`, mais vraisemblances différentes selon le point de départ ; sensibilité exportée ci-dessous |
| Drift/intercept | R `drift` et statsmodels ARIMA `x1` représentent une pente du log-prix ; l’intercept SARIMAX/pmdarima a une autre paramétrisation |
| AICc | pmdarima utilise 1 980 observations ; le calcul manuel R/statsmodels utilise 1 979 observations effectives |
| Convergence | Deux tentatives automatiques Python sans drift ne convergent pas ; les deux gagnants automatiques retenus convergent |
| Implémentation et filtres de recherche | R et Python ont des initialisations, optimiseurs et contrôles d’acceptation différents ; R exporte `Inf` pour ses deux essais `(3,1,3)` |

Une convergence numérique signifie que les conditions d’arrêt de l’algorithme
sont satisfaites. Elle n’assure pas que le maximum global de vraisemblance
a été trouvé. Les traces `Inf` prouvent un rejet dans la recherche R, mais
n’en identifient pas à elles seules la cause technique précise : il ne faut
pas inventer une cause certaine, telle qu’une racine inadmissible.

Avec notre paramétrisation, l’intercept d’une équation sur les différences
est relié au drift par `intercept = drift × (1 - somme des coefficients AR)`.
Comparer directement l’intercept pmdarima à la colonne drift R peut donc
donner une fausse impression de désaccord. Les différences d’erreurs standards
ou de `sigma2` doivent aussi tenir compte des estimateurs de covariance et
corrections de variance propres aux implémentations.

### Ce que montre la sensibilité déjà calculée

La fonction `compare_r_optimizer()` produit une comparaison supplémentaire
au même ordre `(2,1,2)` avec drift. On lit les résultats existants :

| Ajustement | Log-vraisemblance | AICc |
| --- | ---: | ---: |
| R, modèle sélectionné | 3993,228998 | -7974,415400 |
| Python, initialisation indépendante par défaut | 3985,905488 | -7959,768380 |
| Python, initialisé avec les coefficients R | 3993,229479 | -7974,416362 |

La troisième ligne retrouve presque la vraisemblance R. Ses Ljung–Box,
p=0,869850 et 0,784482, sont également très proches des diagnostics R.
Cela soutient une sensibilité à l’initialisation et aux optima locaux comme
explication concrète d’une partie importante du désaccord. Les petites
différences d’AICc ne peuvent pas expliquer à elles seules cet écart.

**L’ajustement initialisé avec R dépend de R : il n’est pas une réplication
indépendante.** Il ne remplace pas le résultat automatique Python et ne
modifie pas le choix provisoire `(1,1,1)`. On ne peut pas affirmer à partir
de cette vérification que le meilleur optimum possible a été trouvé.

Malgré les ordres différents, les conclusions qualitatives des modèles
provisoires concordent : autocorrélation linéaire non détectée aux lags
10/20, normalité rejetée et effets ARCH soutenus. Une divergence d’ordre
est donc un point à comprendre et documenter, pas nécessairement une erreur.

Sources : [coefficients R](../outputs/tables/phase3_arima_coefficients_r.csv),
[coefficients Python](../outputs/tables/phase3_arima_coefficients_python.csv),
[sensibilité d’optimisation](../outputs/tables/phase3_optimizer_sensitivity_python.csv),
[coefficients de sensibilité](../outputs/tables/phase3_optimizer_sensitivity_coefficients_python.csv)
et [diagnostics de sensibilité](../outputs/tables/phase3_optimizer_sensitivity_diagnostics_python.csv).

## 12. What the team must be able to explain orally

Ces formulations servent de repères de compréhension. L’équipe doit pouvoir
les reformuler et les justifier à partir des sorties du projet.

| Notion | Explication à savoir donner |
| --- | --- |
| ARIMA(p,d,q) | `p` décrit la mémoire des valeurs de la série différenciée, `d` le nombre de différences, `q` la mémoire des chocs. |
| d=1 | Les tests Phase 2 soutiennent un log-prix non stationnaire et une première différence stationnaire ; les trois ndiffs confirment un. |
| Drift | Une variation moyenne du log-prix par séance, qui n’impose pas une hausse à chaque séance. |
| ACF/PACF | Corrélation totale selon le retard, puis association linéaire après retrait des retards intermédiaires ; elles suggèrent des candidats. |
| AIC/AICc/BIC | Compromis entre vraisemblance et complexité ; les valeurs plus faibles sont préférées dans une comparaison compatible. |
| auto.arima | Une recherche bornée selon un critère, à contrôler par l’identification, la convergence et les résidus. |
| Choix Python | Le `(3,1,3)` converge et passe Ljung–Box, mais `(1,1,1)` est dans la fenêtre de deux AICc et utilise quatre paramètres plutôt que sept. |
| Ljung–Box | Les p-values au-dessus de 5 % permettent une non-réjection de l’absence d’autocorrélation globale aux horizons examinés, sans prouver l’indépendance. |
| Jarque–Bera | Les grandes statistiques et p-values numériquement nulles rejettent la normalité ; les QQ-plots montrent des queues épaisses. |
| ARCH-LM | Les très petites p-values soutiennent une dépendance de la variance conditionnelle, même lorsque la moyenne est peu autocorrélée. |
| SARIMA non retenu | STL, ACF saisonnière, weekdays et nsdiffs n’apportent pas de preuve conjointe suffisante ; cinq séances ne sont pas cinq jours calendaires. |
| Future hypothèse GARCH | Les amplitudes restent dépendantes après estimation de la moyenne ; un modèle de variance devient une hypothèse à étudier ultérieurement. |
| R/Python | Les données concordent ; les recherches et optima peuvent diverger. Une initialisation R rapprochant Python constitue une sensibilité dépendante. |
| Frontière de validation | Les diagnostics portent sur TRAIN ; aucune supériorité prédictive ou performance sur le holdout n’est encore établie. |

Une explication centrale à maîtriser est : « la moyenne peut sembler
correctement décrite aux horizons testés, alors que la distribution et la
variance des innovations restent mal représentées par des hypothèses
gaussiennes et homoscédastiques ».

## 13. Phase 3A validation checklist

`PASS` signifie que le point est étayé par les preuves demandées. `WARNING`
signale une limite ou une fragilité à conserver dans l’interprétation.
`NEEDS CLARIFICATION` serait utilisé pour une justification manquante ou une
contradiction empêchant d’expliquer la décision. Cette revue concerne les
diagnostics Phase 3A, pas une autorisation de lancer une nouvelle phase.

| Question | Statut | Justification |
| --- | --- | --- |
| stationarity logic correct? | PASS | Hypothèses ADF/KPSS distinguées ; non-stationnarité du niveau et stationnarité des différences soutenues, sans certitude absolue. |
| d justified? | PASS | d=1 fondé sur Phase 2 et confirmé par trois ndiffs ; aucune décision silencieuse par auto.arima. |
| seasonality gate justified? | PASS | Preuves convergentes insuffisantes : nsdiffs=0, ACF saisonnière faible, STL non probante et weekdays sans soutien convaincant. |
| candidate selection justified? | PASS | Règle vérifiée dans le code et les pools ; le choix Python vient de la fenêtre AICc puis de k. Vigilance sur la proximité du seuil de deux. |
| residual autocorrelation acceptable? | WARNING | Ljung–Box non significatif à 10/20 dans les deux langages, mais p Python à lag 10 proche de 0,05 ; portée limitée et hypothèses asymptotiques fragilisées par ARCH. |
| normality limitation documented? | PASS | Normalité rejetée, zéros numériques expliqués, queues épaisses visibles et conséquences pour l’inférence signalées. |
| ARCH effects documented? | PASS | Rejet aux trois ordres dans les deux langages ; lien aux amplitudes expliqué, sans estimation GARCH. |
| R/Python divergence explained? | WARNING | Même TRAIN et forte sensibilité à l’initialisation documentés ; optimum global non établi et causes fines des rejets Inf non identifiées dans les traces. |
| holdout protected? | PASS | Les 14 contrôles exportés sont PASS ; listes de lecture et provenance concordent. Cette rédaction lit uniquement code, tables et figures, sans accéder au holdout. |

**Validation globale Phase 3A : WARNING.** La sélection provisoire est
explicable et les éléments attendus sont documentés. Les limites portent
sur la normalité, la variance conditionnelle, la sensibilité de l’optimisation
et la frontière proche du seuil de parcimonie Python ; elles empêchent de
présenter le modèle comme entièrement validé.

Aucune justification manquante n’a été constatée pour expliquer pourquoi
le choix provisoire Python diffère du gagnant automatique. Les points de
discussion pour l’équipe sont le caractère conventionnel du seuil de deux,
le désaccord AICc/BIC en R et le degré de confiance accordé à des optimisations
sensibles au point de départ. Les résultats ne permettent pas encore de
départager les modèles par leur capacité prédictive.

Sources de contrôle : [holdout guard existant](../outputs/tables/phase3_holdout_guard.csv),
[manifestes TRAIN](../outputs/tables/phase3_train_manifest.csv)
et [synthèse diagnostique](../outputs/tables/phase3_arima_diagnostic_summary.csv).
Le fichier d’interprétation humaine, les scripts, les sorties statistiques
et le holdout restent inchangés. Aucun nouveau calcul statistique, modèle,
forecast final, commit ou push n’est réalisé pour ce guide.
