# Phase 3A — Draft for Human Interpretation

**Brouillon pédagogique en français, à comprendre, discuter et reformuler par
l’équipe.** Les paragraphes « Suggested student wording » sont des propositions
de rédaction ; ils ne constituent pas l’interprétation humaine finale et
n’attestent pas que l’équipe maîtrise déjà les résultats.

Le périmètre est la dynamique univariée de moyenne du log-prix ajusté NVDA sur
TRAIN : **1 980 observations, du 2018-01-02 au 2025-11-14**, soit 1 979 premières
différences. R est la référence pédagogique ; Python est la réplication
indépendante. Les modèles retenus restent des **provisional selected mean
models**, sans validation prédictive finale.

Ce document utilise uniquement le code, les tables et les figures déjà
présents. Aucun modèle ou test statistique n’a été recalculé, aucune prévision
n’a été produite et aucune observation du holdout n’a été lue pour cette
rédaction. Le fichier `llm/human_analysis/phase3a_arima_interpretation.md` reste
réservé à la version finale de l’équipe et inchangé.

Sources de départ : [documentation Phase 3A](phase3a_arima_identification.md),
[guide pédagogique](phase3a_interpretation_guide.md),
[documentation Phase 2](phase2_eda_stationarity.md),
[script Python](../python/02_arima.py) et [script R](../r/02_arima.R).
Les huit sections d’interprétation sont suivies des deux annexes demandées :
défense orale et checklist.

## 1. Why d=1?

### Concept

Un ARIMA(p,d,q) décrit une série après `d` différenciations. La partie
**autorégressive**, d’ordre `p`, relie cette série à ses valeurs passées. La
partie **moyenne mobile des innovations**, d’ordre `q`, relie la série au choc
actuel et aux chocs passés ; ce n’est pas une moyenne glissante des prix.
Une innovation représente ce qui reste inattendu compte tenu du modèle et
des informations passées.

Ici, `y_t = log(P_t)`, où `P_t` est le prix ajusté NVDA. Une différenciation
donne `Δy_t = y_t − y_(t−1)`. Dans le projet,
`Log_Return_t = 100 × Δy_t` : le rendement est exprimé en pourcent, alors
que l’ARIMA travaille sur les log-prix et leurs différences sans facteur 100.
Le logarithme et la différenciation ont des rôles différents ; le logarithme
ne garantit pas, à lui seul, la stationnarité.

Une série stationnaire possède des propriétés statistiques qui ne changent
pas systématiquement avec la date. ADF teste l’hypothèse nulle d’une racine
unitaire ; KPSS teste la stationnarité autour des termes déterministes
spécifiés. Leur lecture complémentaire aide à justifier la différenciation,
sans démontrer avec certitude que le processus est exactement intégré
d’ordre un. Des effets ARCH peuvent subsister dans une série stationnaire :
une variance conditionnelle variable n’implique pas automatiquement une
variance inconditionnelle non constante.

### What our results show

Les diagnostics Phase 2 sur TRAIN donnent :

| Série NVDA | ADF | KPSS | Lecture combinée |
| --- | --- | --- | --- |
| Log-prix | p=0,461103 : racine unitaire non rejetée | p affichée=0,01, valeur réelle plus petite : stationnarité rejetée | Non-stationnarité du niveau soutenue |
| Log-rendement | p=7,91143e-27 : racine unitaire rejetée | p affichée=0,10, valeur réelle plus grande : stationnarité non rejetée | Stationnarité de la première différence soutenue |

Les tests du log-prix comportent une constante et une tendance ; ceux des
rendements comportent une constante. Les valeurs KPSS aux limites sont des
bornes de table, pas des p-values exactes. Multiplier une série par 100 ne
change pas sa propriété de stationnarité : les résultats des log-rendements
s’appliquent donc à la première différence du log-prix.

Les trois vérifications R `ndiffs()` — KPSS niveau, KPSS tendance et ADF
tendance — retournent toutes **1**. Elles confortent la décision issue de
Phase 2. Les deux recherches automatiques reçoivent explicitement `d=1` ;
elles n’en constituent pas la justification initiale. On évite ainsi de
choisir une différenciation sans comprendre les diagnostics, ou de
différencier davantage sans preuve de nécessité.

Sources : [preuves ADF/KPSS](../outputs/tables/phase3_d_phase2_evidence.csv)
et [justification R de d](../outputs/tables/phase3_d_justification_r.csv).

### Suggested student wording

Dans ARIMA(p,d,q), p représente les valeurs passées utilisées, d le nombre
de différenciations et q les chocs passés utilisés. Nous retenons d=1 parce
que les diagnostics Phase 2 soutiennent un log-prix non stationnaire et une
première différence stationnaire. Le log-rendement du projet vaut 100 fois
cette différence, ce qui explique le changement d’unité. ADF et KPSS donnent
des indications complémentaires en faveur de cette décision. Les trois
contrôles ndiffs en R confirment une différenciation. Ce choix est donc
justifié avant la recherche automatique, tout en restant une conclusion
statistique assortie de limites.

## 2. ACF/PACF and manual candidate choice

### Concept

L’**ACF** mesure la corrélation entre la série et ses valeurs décalées.
La **PACF** mesure l’association linéaire avec un retard donné après prise
en compte des retards intermédiaires. Un lag correspond ici à une séance
observée, pas nécessairement à un jour calendaire.

Une ACF qui décroît lentement dans le niveau est un signe de persistance.
Après différenciation, on recherche une dépendance plus courte. Dans des
cas théoriques simples, une PACF qui s’arrête après p suggère un AR(p), et
une ACF qui s’arrête après q suggère un MA(q). Sur un échantillon réel, ces
motifs sont bruités : les graphiques proposent des candidats plutôt qu’un
ordre unique obligatoire. Les bandes ponctuelles à 95 % ne garantissent pas
que tous les retards examinés simultanément restent dans les bandes.

Le **drift** autorise une variation moyenne non nulle du log-prix par séance.
Il n’impose ni une hausse à chaque séance ni un rendement futur garanti.
Sans drift, la moyenne de la différence est fixée à zéro dans ces modèles.

### What our results show

La [figure du log-prix](../outputs/figures/phase3/nvda_log_price_acf_pacf_train.png)
montre une ACF proche de un qui diminue très lentement. Dans la
[figure de la première différence](../outputs/figures/phase3/nvda_delta_log_price_acf_pacf_train.png),
ACF et PACF sont beaucoup plus proches de zéro. La
[figure R à quatre panneaux](../outputs/figures/phase3/nvda_log_price_acf_pacf_train_r.png)
confirme ce contraste. Quelques valeurs exportées, arrondies :

| Lag | ACF de Δlog-prix | PACF de Δlog-prix |
| ---: | ---: | ---: |
| 1 | -0,081476 | -0,081476 |
| 2 | 0,047813 | 0,041449 |
| 3 | -0,037549 | -0,030693 |
| 5 | 0,014469 | 0,014759 |
| 7 | 0,055862 | 0,051107 |
| 8 | -0,045153 | -0,035200 |
| 9 | 0,046479 | 0,035657 |
| 10 | -0,025300 | -0,013103 |

La borne ponctuelle indicative est ±0,044059. Le lag 1 négatif et quelques
pics isolés motivent des modèles de faible ordre ; ils ne définissent pas
une coupure suffisamment nette pour imposer un seul couple p/q.

Les **cinq candidats manuels**, convergents dans les deux langages, sont :

| Modèle | Lecture intuitive après une différence | Drift | k, variance comprise |
| --- | --- | --- | ---: |
| ARIMA(0,1,0) | Marche aléatoire : aucune mémoire AR/MA des différences | Non | 1 |
| ARIMA(0,1,0) | Marche aléatoire avec variation moyenne | Oui | 2 |
| ARIMA(1,1,0) | La différence dépend de la différence précédente | Oui | 3 |
| ARIMA(0,1,1) | La différence dépend du choc précédent et du choc actuel | Oui | 3 |
| ARIMA(1,1,1) | Une différence passée et un choc passé interviennent | Oui | 4 |

Les recherches automatiques explorent aussi les autres ordres réellement
tracés : `(0,1,2)`, `(0,1,3)`, `(1,1,2)`, `(1,1,3)`, `(2,1,0)`, `(2,1,1)`,
`(2,1,2)`, `(2,1,3)`, `(3,1,0)`, `(3,1,1)`, `(3,1,2)` et `(3,1,3)`, avec et
sans drift. Ils appartiennent à la grille automatique p,q de 0 à 3, pas à
une nouvelle liste de modèles manuels. Une tentative tracée n’est pas
nécessairement une estimation acceptée : R attribue `Inf` aux deux essais
`(3,1,3)`, et les essais Python `(1,1,0)` et `(0,1,1)` sans drift ne convergent
pas. La version sans drift de `(1,1,1)` figure également dans les recherches.

Sources : [ACF/PACF Python](../outputs/tables/phase3_acf_pacf_numeric.csv),
[ACF/PACF R](../outputs/tables/phase3_acf_pacf_numeric_r.csv),
[candidats manuels R](../outputs/tables/phase3_arima_manual_candidates_r.csv),
[candidats manuels Python](../outputs/tables/phase3_arima_manual_candidates_python.csv),
[recherche Python](../outputs/tables/phase3_auto_arima_python.csv)
et [trace R](../outputs/tables/phase3_auto_arima_trace_r.csv).

### Suggested student wording

L’ACF du log-prix révèle une forte persistance, alors que celle de sa
première différence est beaucoup plus faible. Au premier retard, ACF et
PACF valent environ -0,0815, avec quelques autres pics isolés. Ce motif
justifie de comparer des modèles simples, sans imposer automatiquement
un ordre unique. Nous avons testé deux marches aléatoires, puis ARIMA(1,1,0),
ARIMA(0,1,1) et ARIMA(1,1,1), ces trois derniers avec drift. Le drift
représente une variation moyenne du log-prix, sans garantir le signe des
variations quotidiennes. Les modèles plus complexes viennent de la
recherche automatique documentée.

## 3. Manual vs automatic selection

### Concept

L’identification manuelle construit des modèles compréhensibles à partir
des diagnostics. La recherche automatique élargit cette comparaison dans
une grille fixée. Elle reste dépendante du critère, des bornes, de
l’optimisation et des règles d’acceptation : son résultat est une proposition
à diagnostiquer, pas une preuve de qualité prédictive.

**AIC** compare ajustement et complexité à partir de la vraisemblance et du
nombre de paramètres. **AICc** corrige l’AIC selon l’effectif et la complexité.
**BIC** pénalise généralement davantage les paramètres, notamment avec notre
effectif. Plus faible est préférable à données et conventions comparables,
y compris lorsque les valeurs sont négatives. Un minimum AIC ne suffit pas :
il faut aussi examiner convergence, parcimonie et résidus. Ces critères ne
sont ni des p-values ni des erreurs de prévision.

### What our results show

Les scripts fixent `d=1`, désactivent la saisonnalité et la recherche stepwise,
limitent p et q à 3 et utilisent AICc. R désactive aussi l’approximation ;
Python compare explicitement les politiques avec et sans intercept/drift.
Les résultats vérifiés sont :

| Décision | Modèle | AIC | AICc | BIC |
| --- | --- | ---: | ---: | ---: |
| R automatique et provisoire | (2,1,2), avec drift | -7974,458 | -7974,415 | -7940,916 |
| Python automatique, pmdarima | (3,1,3), sans drift | -7965,755 | -7965,698051 | -7926,622 |
| Python provisoire, statsmodels | (1,1,1), avec drift | -7963,736 | -7963,715481 | -7941,374 |

La règle de sélection provisoire est explicite dans `select_candidate()`
en Python et le bloc `valid / adequate / near` en R :

1. Exclure les estimations non convergentes ou avec AICc/BIC non finis.
2. Privilégier celles dont les deux Ljung–Box, lags 10 et 20, donnent
   `p >= 0.05`. Si aucune ne passe, revenir aux estimations valides en
   conservant la limite diagnostique ; ce recours n’est pas nécessaire ici.
3. Conserver les modèles à au plus deux unités d’AICc du meilleur admissible.
4. Trier par nombre de paramètres k, puis BIC, AICc et identifiant du modèle.

Le pool Python contient **les cinq modèles manuels et le seul gagnant
automatique, réestimé avec statsmodels**. Il ne comprend pas les 32 essais
automatiques pour une nouvelle sélection par diagnostics. Les marches
aléatoires, AR(1) et MA(1) échouent au Ljung–Box à lag 10 ; seuls ces deux
modèles du pool passent les deux contrôles :

| Modèle du pool Python | Convergent | AICc | BIC | k | p LB10 | p LB20 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| (1,1,1), drift | Oui | -7963,715481 | -7941,374357 | 4 | 0,067465 | 0,118122 |
| (3,1,3), sans drift | Oui | -7965,698022 | -7926,622418 | 7 | 0,570307 | 0,611709 |

L’écart AICc documenté est d’environ **1,98254**, inférieur à deux. Le code
retient donc quatre paramètres plutôt que sept. BIC soutient également le
modèle simple, mais intervient après k : le départage décisif est la
parcimonie dans la fenêtre AICc. Le modèle automatique **converge et passe
les diagnostics** ; il n’est pas éliminé pour échec de convergence ou de
Ljung–Box. Une p-value Ljung–Box plus élevée ne mesure pas une meilleure
prévision. Aucun filtre supplémentaire de « stabilité » n’explique cette
décision dans `select_candidate()`.

La petite différence entre AICc pmdarima (-7965,698051) et celui du pool
statsmodels (-7965,698022) vient de l’effectif utilisé dans la correction :
1 980 contre 1 979. La décision du pool se lit avec sa propre valeur.
La proximité du seuil de deux reste un point à défendre : c’est une règle
conventionnelle, pas une preuve que les modèles prédisent aussi bien.

En R, `(1,1,1)` avec drift et `(2,1,2)` avec drift passent les deux tests,
mais leurs AICc sont -7963,715534 et -7974,415400. Le modèle simple est à
environ 10,70 unités et sort de la fenêtre : R conserve `(2,1,2)`. Son BIC
est légèrement moins favorable que celui du manuel `(1,1,1)`
(-7941,374409), ce qui rend le compromis de complexité utile à discuter.

La justification du choix Python est établie. Les raisons fines pour
lesquelles les recherches des deux langages atteignent des résultats
différents restent seulement partiellement identifiées, comme expliqué
en section 7 : **“This point should be defended as an implementation/selection
difference, not hidden as if R and Python agreed perfectly.”**

Sources : [pool Python](../outputs/tables/phase3_arima_selection_pool_python.csv),
[pool R](../outputs/tables/phase3_arima_selection_pool_r.csv),
[résultat automatique R](../outputs/tables/phase3_auto_arima_r.csv),
[résultats automatiques Python](../outputs/tables/phase3_auto_arima_python.csv)
et [comparaison globale](../outputs/tables/phase3_arima_selection_comparison.csv).

### Suggested student wording

L’identification manuelle fournit des modèles simples à expliquer, tandis
que la recherche automatique explore une grille plus large. R propose et
retient provisoirement ARIMA(2,1,2) avec drift. Python propose automatiquement
ARIMA(3,1,3) sans drift, mais retient provisoirement ARIMA(1,1,1) avec drift.
Les deux modèles Python convergent et passent Ljung–Box ; leur écart AICc
d’environ 1,98254 les place dans la même fenêtre de sélection. La règle du
projet préfère alors quatre paramètres à sept, avec un BIC également plus
favorable au modèle simple. Cette décision doit être défendue avec sa
proximité du seuil, sans prétendre qu’elle prouve une supériorité prédictive.

## 4. Residual independence

### Concept

Les résidus sont les innovations estimées, c’est-à-dire la partie des
observations que le modèle de moyenne n’explique pas avec le passé.
Ljung–Box teste H0 : **absence d’autocorrélation globale des résidus jusqu’au
retard considéré**. Un test à lag 20 porte sur l’ensemble des retards 1 à 20,
pas uniquement sur le vingtième.

Au seuil de 5 %, p>0,05 conduit à ne pas rejeter H0. Cela signifie que ce
diagnostic ne détecte pas assez de dépendance linéaire pour rejeter ; cela
ne prouve ni l’indépendance complète ni la perfection du modèle. Une p-value
n’est pas la probabilité que H0 soit vraie. Des résidus peuvent être peu
autocorrélés tout en conservant une dépendance de leurs carrés.

### What our results show

Les tests formels portent sur 1 979 innovations brutes après exclusion de
l’innovation initiale. Les degrés de liberté sont `lag − (p+q)` : 6 et 16
en R, 8 et 18 en Python.

| Modèle provisoire | p Ljung–Box lag 10 | p Ljung–Box lag 20 |
| --- | ---: | ---: |
| R (2,1,2), drift | 0,869791 | 0,784385 |
| Python (1,1,1), drift | 0,067465 | 0,118122 |

Toutes ces p-values dépassent 0,05. Les diagnostics sont donc compatibles
avec l’absence d’autocorrélation linéaire résiduelle significative aux
horizons testés. Python au lag 10 se situe assez près du seuil ; cela invite
à une formulation prudente. Les tests sont asymptotiques, réalisés après
sélection, et les effets ARCH limitent la portée des approximations usuelles.

Dans l’[ACF résiduelle R](../outputs/figures/phase3/nvda_arima_residual_acf.png),
les corrélations sont faibles, sans motif persistant évident ; les barres
restent visuellement dans les bandes. L’[ACF Python](../outputs/figures/phase3/nvda_arima_residual_acf_python.png)
présente aussi de faibles corrélations et quelques pics isolés, notamment
au voisinage du lag 7. L’axe Python va de -1 à 1, alors que l’axe R est
resserré : la hauteur apparente des barres ne suffit pas pour les comparer.
Un pic isolé et un test global ne répondent pas exactement à la même question.

**Précision par rapport au guide antérieur :** celui-ci décrit un dépassement
isolé R autour du lag 40. À l’examen de la figure actuelle, cette barre
paraît rester à l’intérieur de la bande ; ce brouillon ne reprend donc pas
cette affirmation. Cette correction de lecture graphique ne change pas
les p-values exportées à 10 et 20 et ne repose sur aucun nouveau calcul.

Le champ `white_noise_mean_supported=True` dans la synthèse désigne les
deux contrôles de corrélation de moyenne ; il ne certifie pas un bruit
gaussien indépendant et de variance constante. La
[figure checkresiduals R](../outputs/figures/phase3/nvda_arima_checkresiduals_r.png)
utilise la convention native incluant l’innovation initiale ; ses très
petits écarts avec les tables ne changent pas leur conclusion.

Sources : [diagnostics R](../outputs/tables/phase3_arima_residual_diagnostics_r.csv),
[diagnostics Python](../outputs/tables/phase3_arima_residual_diagnostics_python.csv)
et [synthèse](../outputs/tables/phase3_arima_diagnostic_summary.csv).

### Suggested student wording

Ljung–Box recherche une autocorrélation résiduelle globale jusqu’au retard
choisi. Les p-values sont environ 0,87 et 0,78 en R, puis 0,067 et 0,118
en Python aux lags 10 et 20. Elles dépassent 5 %, donc nous ne rejetons
pas l’hypothèse nulle aux horizons examinés. Les ACF résiduelles montrent
également une faible dépendance linéaire visible. Nous ne pouvons toutefois
pas affirmer que les résidus sont parfaitement indépendants, notamment
parce que leurs amplitudes restent dépendantes. Le résultat Python à lag
10, proche du seuil, renforce cette prudence.

## 5. Residual normality

### Concept

Jarque–Bera teste H0 : **résidus compatibles avec une distribution normale**,
à partir de leur asymétrie et de leur kurtosis. Une forte statistique
associée à une petite p-value conduit au rejet. Le QQ-plot complète le test
en comparant les quantiles observés à ceux d’une référence normale.

Un centre proche de la droite ne suffit pas si les queues s’en écartent.
Une queue gauche sous la droite et une queue droite au-dessus indiquent
des extrêmes plus prononcés que sous cette référence. Rejeter la normalité
n’invalide pas automatiquement l’usage d’un ARIMA pour décrire la moyenne ;
cela limite les hypothèses gaussiennes, l’inférence conventionnelle et la
confiance accordée à de futurs intervalles gaussiens. Cela ne valide aucune
prévision, puisqu’il n’y en a pas encore dans cette phase.

### What our results show

| Modèle provisoire | Statistique Jarque–Bera | p-value exportée |
| --- | ---: | ---: |
| R (2,1,2), drift | 1704,152267 | 0 numérique |
| Python (1,1,1), drift | 1776,106839 | 0 numérique |

La normalité est rejetée dans les deux langages. Le zéro affiché est une
limite de représentation numérique d’une p-value extrêmement faible, pas
une probabilité mathématiquement nulle.

Les [QQ-plots R](../outputs/figures/phase3/nvda_arima_residual_qqplot.png)
et [Python](../outputs/figures/phase3/nvda_arima_residual_qqplot_python.png)
montrent un centre relativement proche de la droite et des écarts
importants aux deux extrémités, avec des observations extrêmes. Cette lecture
est cohérente avec les queues épaisses déjà documentées pour les
log-rendements TRAIN en Phase 2, dont l’excès de kurtosis NVDA est 4,69802.
La dynamique de moyenne estimée n’a donc pas supprimé cette caractéristique.

Les figures ne choisissent pas à elles seules une autre loi d’innovations
et Jarque–Bera n’identifie pas la cause de la non-normalité. Les effets ARCH
peuvent contribuer à une distribution marginale à queues épaisses ; cela
ne démontre pas que toute la non-normalité vient de ce mécanisme.

Sources : [diagnostics R](../outputs/tables/phase3_arima_residual_diagnostics_r.csv),
[diagnostics Python](../outputs/tables/phase3_arima_residual_diagnostics_python.csv)
et [statistiques Phase 2](phase2_eda_stationarity.md#descriptive-statistics).

### Suggested student wording

Jarque–Bera teste la compatibilité des résidus avec une loi normale. Les
statistiques sont environ 1704,15 en R et 1776,11 en Python, avec des
p-values numériquement nulles. Nous rejetons donc la normalité dans les
deux implémentations. Les QQ-plots montrent surtout de forts écarts dans
les queues, comme les diagnostics de rendements en Phase 2. Cette limite
n’empêche pas automatiquement l’ARIMA de décrire la moyenne, mais elle
oblige à rester prudent sur l’inférence et les futurs intervalles fondés
sur une hypothèse gaussienne.

## 6. ARCH effects

### Concept

ARCH-LM teste H0 : **absence d’effet ARCH jusqu’à l’ordre considéré**.
Il examine si les carrés des résidus dépendent linéairement de leurs
valeurs passées. À l’ordre 10, les retards 1 à 10 entrent dans le diagnostic.
Une p-value extrêmement petite fournit un argument contre l’absence de
cette dépendance.

Intuitivement, les erreurs peuvent alterner de signe et être peu corrélées,
alors que leurs tailles se regroupent : une période agitée tend à être
suivie d’une période agitée. C’est le **volatility clustering**. La variance
conditionnelle, c’est-à-dire la dispersion des erreurs compte tenu du passé,
varie alors avec l’information disponible. Cela ne signifie pas que les
signes des prochains rendements sont prévisibles.

### What our results show

| Ordre ARCH-LM | p-value R | p-value Python |
| ---: | ---: | ---: |
| 5 | 1,50217e-12 | 1,09996e-13 |
| 10 | 9,44313e-12 | 1,02156e-13 |
| 20 | 1,06283e-10 | 2,02698e-12 |

H0 est fortement rejetée aux trois ordres, dans les deux langages. Les
conventions sont explicites : R utilise `FinTS::ArchTest(demean=FALSE)` et
Python `het_arch(ddof=0)` sur les innovations brutes après retrait de
l’innovation initiale.

La chaîne d’arguments repose sur plusieurs résultats concordants :

- Phase 2 décrit des regroupements d’amplitudes et fournit une
  [ACF des log-rendements au carré sur TRAIN](../outputs/figures/phase2/nvda_squared_returns_acf_train.png).
- Les [résidus R dans le temps](../outputs/figures/phase3/nvda_arima_residuals.png)
  et les [résidus Python](../outputs/figures/phase3/nvda_arima_residuals_python.png)
  restent globalement autour de zéro, mais leurs amplitudes changent et
  des valeurs extrêmes subsistent.
- Les ACF des résidus au carré,
  [R](../outputs/figures/phase3/nvda_arima_squared_residual_acf.png) et
  [Python](../outputs/figures/phase3/nvda_arima_squared_residual_acf_python.png),
  montrent plusieurs corrélations positives au-delà des bandes indicatives.
- ARCH-LM apporte le diagnostic formel Phase 3A de cette dépendance restante.
  La Phase 2 n’avait pas encore exécuté de test ARCH-LM.

Ces constats soutiennent une variance conditionnelle non constante après
modélisation de la moyenne. Ils donnent une justification scientifique à
une **future hypothèse GARCH**, qui porterait sur la variance, sans en
déterminer l’ordre, la loi d’innovations ou la performance. Aucun GARCH
n’est estimé ici et aucune amélioration future n’est acquise.

Sources : [diagnostics R](../outputs/tables/phase3_arima_residual_diagnostics_r.csv),
[diagnostics Python](../outputs/tables/phase3_arima_residual_diagnostics_python.csv)
et [ACF/variance Phase 2](phase2_eda_stationarity.md#acf-pacf).

### Suggested student wording

ARCH-LM teste l’absence de dépendance des carrés des résidus aux ordres
examinés. Les p-values aux lags 5, 10 et 20 sont extrêmement faibles en
R comme en Python, donc cette hypothèse est fortement rejetée. Les résidus
peuvent être peu autocorrélés tout en conservant une dépendance de leurs
amplitudes. Les graphiques temporels et les ACF des résidus au carré
confirment ce constat, cohérent avec le volatility clustering de Phase 2.
La moyenne paraît mieux décrite que la variance conditionnelle. Une future
phase GARCH devient donc une hypothèse justifiée à étudier, sans être
estimée ni considérée comme validée à ce stade.

## 7. R vs Python

### Concept

Deux implémentations peuvent partager la même logique scientifique tout en
atteignant des estimations différentes. L’optimiseur, le point de départ,
la représentation du modèle, le traitement des états initiaux et les
contrôles d’acceptation peuvent modifier le résultat numérique. Une
convergence indique que les conditions d’arrêt de l’algorithme sont
satisfaites ; elle ne garantit pas le maximum global de vraisemblance.

Comparer des noms de coefficients sans vérifier leur définition peut aussi
induire en erreur. Avec la paramétrisation employée ici, l’intercept dans
l’équation des différences est relié au drift par
`intercept = drift × (1 − somme des coefficients AR)`. La pente `x1` de
statsmodels ARIMA avec `trend="t"` est comparable au drift R ; un intercept
pmdarima/SARIMAX ne se compare pas directement à cette pente.

### What our results show

Les manifestes indiquent les mêmes 1 980 observations TRAIN, les mêmes
dates et la même empreinte MD5 dans les deux lecteurs. La divergence
documentée ne s’explique donc pas par deux échantillons différents selon
ces contrôles. Les décisions sont conservées honnêtement : automatique R
`(2,1,2)` avec drift, automatique Python `(3,1,3)` sans drift ; provisoire R
`(2,1,2)` avec drift, provisoire Python `(1,1,1)` avec drift.

| Point de comparaison | Ce qui est établi dans le projet |
| --- | --- |
| Estimation | R utilise `forecast::Arima(method="ML")` ; statsmodels ARIMA utilise une vraisemblance en espace d’états ; la recherche pmdarima précise L-BFGS. Il ne s’agit pas d’opposer ML à une estimation sans vraisemblance. |
| Initialisation et optimisation | La sensibilité déjà exportée au même ordre `(2,1,2)` montre des vraisemblances différentes selon le départ. |
| Drift/intercept | Même idée de variation moyenne, mais paramètres exprimés différemment selon la représentation. |
| Convergence et acceptation | Deux essais Python sans drift ne convergent pas ; les gagnants retenus convergent. R rejette ses deux essais `(3,1,3)` avec un critère `Inf`. |
| AICc | Le calcul manuel R/statsmodels utilise 1 979 observations effectives ; pmdarima utilise 1 980. Cette correction minuscule n’explique pas les grands écarts de vraisemblance. |
| Incertitude des coefficients | Les estimateurs de covariance et corrections de variance diffèrent ; les erreurs standards et `sigma2` ne doivent pas être assimilés sans vérifier les conventions. |

La comparaison de sensibilité **déjà calculée** donne, au même ordre
`(2,1,2)` avec drift :

| Ajustement | Log-vraisemblance | AICc |
| --- | ---: | ---: |
| R sélectionné | 3993,228998 | -7974,415400 |
| Python, départ indépendant par défaut | 3985,905488 | -7959,768380 |
| Python, départ avec coefficients R | 3993,229479 | -7974,416362 |

L’initialisation avec les coefficients R retrouve une vraisemblance très
proche de R, ainsi que des p-values Ljung–Box proches : 0,869850 et 0,784482.
Cette preuve soutient la sensibilité à l’initialisation et aux optima locaux
comme explication concrète d’une partie importante du désaccord. Elle ne
prouve pas un optimum global et n’établit pas la cause technique précise
des deux critères `Inf` R ; il ne faut pas inventer cette cause.

**Cette estimation Python dépend de R.** Elle est une analyse de sensibilité,
pas une réplication indépendante, et ne remplace ni le résultat automatique
Python ni sa sélection provisoire. Elle n’est pas ajoutée rétrospectivement
au pool de sélection indépendant.

Les deux modèles provisoires donnent néanmoins les mêmes conclusions
qualitatives : non-rejet de Ljung–Box à 10/20, normalité rejetée et effets
ARCH aux trois ordres. Le projet peut conserver cette cohérence scientifique
sans imposer une égalité artificielle des ordres. Les mécanismes précis de
chaque rejet automatique restent un point partiellement ouvert.

Sources : [manifestes TRAIN](../outputs/tables/phase3_train_manifest.csv),
[sensibilité Python](../outputs/tables/phase3_optimizer_sensitivity_python.csv),
[diagnostics de sensibilité](../outputs/tables/phase3_optimizer_sensitivity_diagnostics_python.csv)
et [documentation des conventions](phase3a_arima_identification.md#r-vs-python-comparison).

### Suggested student wording

R et Python utilisent le même TRAIN et la même logique de différenciation,
mais leurs recherches et leurs optimisations ne sélectionnent pas le même
modèle. Les différences d’initialisation, de paramétrisation et de critères
doivent être documentées. À l’ordre (2,1,2) avec drift, la sensibilité
existante montre qu’un départ Python fondé sur les coefficients R retrouve
une vraisemblance proche de celle de R. Cela soutient une explication par
l’initialisation, sans prouver un optimum global ni expliquer chaque rejet
de recherche. Ce résultat dépend de R et ne remplace pas la sélection
Python indépendante. Malgré la divergence des ordres, les conclusions
résiduelles générales concordent.

## 8. Is the ARIMA model statistically acceptable?

### Concept

L’acceptabilité doit préciser ce que le modèle cherche à décrire : ici,
la dynamique linéaire de **moyenne**, et non toute la distribution des
erreurs. Un modèle peut rendre cette moyenne raisonnablement satisfaisante
aux horizons examinés tout en décrivant mal la variance. Les diagnostics
sur TRAIN ne permettent pas d’affirmer qu’il sera le meilleur en prévision.

Il faut aussi distinguer une hypothèse saisonnière exploratoire et une
saisonnalité assez étayée pour estimer SARIMA. Refuser de forcer une
composante saisonnière insuffisamment justifiée fait partie de la logique
d’identification. Enfin, protéger le holdout conserve une évaluation future
indépendante du choix du modèle.

### What our results show

**La conclusion est une acceptabilité provisoire pour la moyenne, avec une
description incomplète de la variance conditionnelle.**

| Arguments favorables | Limites à conserver dans la rédaction |
| --- | --- |
| d=1 soutenu par Phase 2 et ndiffs | Les tests ne prouvent pas une stationnarité parfaite pour toute période future. |
| Ljung–Box non rejeté à 10/20 dans les deux langages | Cela ne prouve pas l’indépendance ; la p-value Python à lag 10 est proche de 0,05. |
| Résidus globalement centrés autour de zéro | Des extrêmes et des regroupements d’amplitudes persistent. |
| Saison non imposée sans preuve suffisante | `sarima_justified=FALSE` ne démontre pas l’absence de tout effet calendaire. |
| 14 contrôles holdout exportés PASS | Ces contrôles protègent la procédure ; ils ne constituent pas une performance prédictive. |
| Diagnostics qualitatifs cohérents en R/Python | Les ordres diffèrent et l’optimisation est sensible à l’initialisation. |

Les moyennes résiduelles exportées sont -0,0000223294 en R et 0,0000071808
en Python, dans l’unité des différences de log-prix. Les figures temporelles
corroborent ce centrage visuel, sans démontrer à elles seules un modèle
correct. La normalité est rejetée et ARCH-LM reste fortement significatif.

**Pourquoi aucun SARIMA ?** Le gate exporté donne `sarima_justified = FALSE` :

- `nsdiffs` vaut 0 avec `seas` et 0 avec OCSB en R.
- STL `period=5` était une exploration ; les recomputations Phase 3
  donnent une force saisonnière tronquée à 0 dans les deux langages.
- Les ACF des différences aux lags 5/10/15/20 valent respectivement
  0,014469 / -0,025300 / -0,026976 / 0,021551 : aucune ne dépasse la borne
  corrigée pour ces quatre retards, ±0,056146.
- Les moyennes par jour de semaine sont descriptives ; l’ANOVA auxiliaire
  donne p=0,431880 et possède des limites avec queues épaisses et variances
  inégales. Des moyennes observées différentes ne prouvent pas une
  saisonnalité stable. Cinq séances ne correspondent pas toujours aux
  mêmes cinq jours calendaires, notamment en présence de jours fériés.

La règle R exige conjointement une force saisonnière >0,64, au moins trois
des quatre ACF au-delà de la borne corrigée, une p-value weekday <0,05 et
un `nsdiffs` saisonnier positif. Python contrôle les trois premiers éléments
et s’arrêterait s’ils étaient convaincants ; la synthèse ajoute les
vérifications R, ici nulles. Les preuves conjointes sont insuffisantes,
donc aucun SARIMA n’a été estimé. `nsdiffs=0` seul n’exclurait pas toute
forme possible de saisonnalité.

Les **14 PASS** du holdout guard existant concernent l’estimation, la
sélection, les diagnostics, le gate, les listes de lecture autorisées et
la concordance de TRAIN. Ils combinent validations d’entrées et audit du
code. Ils sont rapportés depuis le fichier existant, sans nouvelle lecture
du holdout. Aucun score final, aucune comparaison prédictive finale et
aucune prévision finale ne sont disponibles pour départager ces modèles.

La formulation centrale à comprendre est : **“ARIMA captures the linear mean
dynamics reasonably well, but does not fully model the conditional variance.”**
Elle concerne les diagnostics présents et les choix provisoires. Elle ne
permet pas d’affirmer que l’ARIMA est le meilleur modèle ou qu’une future
extension améliorera nécessairement les prévisions.

Sources : [synthèse des diagnostics](../outputs/tables/phase3_arima_diagnostic_summary.csv),
[gate saisonnier commun](../outputs/tables/phase3_seasonality_gate.csv),
[gate R](../outputs/tables/phase3_seasonality_gate_r.csv)
et [holdout guard](../outputs/tables/phase3_holdout_guard.csv).

### Suggested student wording

Nous considérons les ARIMA retenus comme des modèles provisoires
raisonnablement acceptables pour la dynamique linéaire de moyenne sur
TRAIN. La différenciation est justifiée, les résidus sont globalement
centrés et Ljung–Box ne rejette pas aux horizons testés. Aucun SARIMA n’a
été forcé, car les diagnostics saisonniers ne donnent pas de preuve
conjointe suffisante. En revanche, la normalité est rejetée et les effets
ARCH montrent que la variance conditionnelle reste incomplètement décrite.
La divergence R/Python est documentée et le holdout est protégé. Nous ne
concluons donc ni à un modèle parfait ni à une supériorité prédictive,
puisqu’aucune validation prédictive finale n’a encore été réalisée.

## Oral Defense — What We Must Know

Ces réponses sont des repères à reformuler, pas une preuve de maîtrise
acquise par l’équipe.

1. **Qu’est-ce qu’un ARIMA(p,d,q) ?**
   C’est un modèle de la série après d différenciations, avec p valeurs
   passées et q chocs passés. La partie MA concerne les innovations,
   pas une moyenne glissante des prix.

2. **Pourquoi d=1 ?**
   ADF/KPSS Phase 2 soutiennent un log-prix non stationnaire et une première
   différence stationnaire. Les trois ndiffs R retournent 1 et confortent
   cette décision prise avant la recherche automatique.

3. **Différence entre ACF et PACF ?**
   L’ACF mesure la corrélation avec les valeurs retardées. La PACF retire
   l’association linéaire liée aux retards intermédiaires pour isoler
   celle d’un retard spécifique.

4. **Qu’est-ce qu’un drift ?**
   Il autorise une variation moyenne du log-prix par séance. Il ne garantit
   pas une hausse quotidienne, et sa paramétrisation doit être distinguée
   de l’intercept d’une équation autorégressive sur les différences.

5. **Pourquoi tester plusieurs candidats ?**
   L’ACF/PACF ne désigne pas un ordre unique certain dans notre échantillon.
   Comparer des modèles simples permet d’examiner le compromis entre
   dépendance de moyenne, complexité et diagnostics résiduels.

6. **Pourquoi auto.arima ne suffit pas ?**
   Il cherche un bon critère dans une grille avec un algorithme et des
   conventions donnés. Il faut encore contrôler convergence et résidus,
   puis appliquer une règle de sélection explicable.

7. **Que mesure AIC ?**
   AIC met en balance l’ajustement par vraisemblance et le nombre de
   paramètres. Plus faible est préférable à comparaison compatible,
   mais ce n’est pas une erreur de prévision.

8. **Que mesure BIC ?**
   BIC met également en balance vraisemblance et complexité, avec une
   pénalité dépendant de l’effectif. Ici, il pénalise davantage les
   paramètres supplémentaires et peut préférer un modèle plus simple
   que celui favorisé par AICc.

9. **H0 du Ljung–Box ?**
   H0 est l’absence d’autocorrélation globale jusqu’au retard considéré.
   Les p-values supérieures à 0,05 conduisent à une non-réjection, sans
   prouver l’indépendance complète des résidus.

10. **H0 du Jarque–Bera ?**
    H0 est la compatibilité des résidus avec une distribution normale.
    Nos p-values numériquement nulles et les QQ-plots conduisent au rejet,
    avec des queues plus épaisses que la référence normale.

11. **H0 de ARCH-LM ?**
    H0 est l’absence d’effet ARCH à l’ordre examiné. Les très petites
    p-values aux ordres 5, 10 et 20 soutiennent une dépendance de la
    variance conditionnelle à l’information passée.

12. **Pourquoi GARCH devient pertinent ?**
    ARCH-LM et les ACF des résidus au carré indiquent une dépendance des
    amplitudes que le modèle de moyenne laisse subsister. Cela justifie
    l’étude future d’un modèle de variance, sans estimation GARCH ici
    ni garantie d’amélioration.

13. **Pourquoi SARIMA n’a pas été retenu ?**
    nsdiffs=0, la faible ACF saisonnière, la force STL nulle et les
    diagnostics weekday n’apportent pas de preuve conjointe suffisante.
    Le gate reste FALSE ; cela n’exclut pas tout effet calendaire possible.

14. **Pourquoi R et Python peuvent différer ?**
    Optimisation, initialisation, paramétrisation et conventions de calcul
    peuvent différer sur un même TRAIN. La sensibilité déjà calculée
    montre qu’un départ Python fondé sur R rapproche les vraisemblances,
    mais ce résultat dépend de R et ne remplace pas la réplication indépendante.

15. **Pourquoi le holdout final reste interdit à ce stade ?**
    Il doit rester indépendant des décisions de modèle pour permettre
    une évaluation finale crédible. L’utiliser maintenant pour choisir
    un ordre ou ajuster l’interprétation contaminerait cette évaluation.

## Phase 3A Interpretation Checklist

Les statuts portent sur la préparation pédagogique de ce brouillon :
**READY** signifie que les explications et leurs preuves sont disponibles ;
**REVIEW NEEDED** identifie un point à défendre explicitement avant la
rédaction finale. Ils ne certifient pas la compréhension personnelle des
étudiants, qui doit être vérifiée par la reformulation orale.

| Item | Statut | Point de contrôle pour l’équipe |
| --- | --- | --- |
| d=1 understood | READY | Relier ADF/KPSS, première différence, facteur 100 et ndiffs ; distinguer soutien et preuve. |
| ARIMA(p,d,q) understood | READY | Expliquer valeurs passées, différenciation et chocs passés. |
| ACF/PACF understood | REVIEW NEEDED | Lire les bandes et les axes ; retenir la précision sur le lag 40 R au lieu du dépassement décrit dans le guide antérieur. |
| drift understood | READY | Expliquer la variation moyenne et la différence drift/intercept. |
| manual vs automatic understood | REVIEW NEEDED | Défendre la fenêtre AICc proche de deux, le tri par k puis BIC, et le périmètre exact du pool Python. |
| Ljung-Box interpreted correctly | READY | Dire non-rejet aux horizons testés, sans affirmer une indépendance parfaite. |
| Jarque-Bera interpreted correctly | READY | Expliquer rejet, zéro numérique, QQ-plots et limites des hypothèses gaussiennes. |
| ARCH-LM interpreted correctly | READY | Distinguer dépendance des amplitudes et dépendance linéaire de moyenne. |
| SARIMA rejection understood | READY | Expliquer l’insuffisance conjointe des preuves ; distinguer d et différence saisonnière. |
| R/Python divergence understood | REVIEW NEEDED | Distinguer preuve de sensibilité, causes techniques encore partielles et estimation dépendante de R. |
| holdout protection understood | READY | Expliquer les 14 PASS existants et pourquoi ils ne sont pas une validation prédictive. |

**Statut pédagogique global : REVIEW NEEDED.** Le brouillon est complet
pour préparer la discussion ; l’équipe doit défendre les trois points
signalés et reformuler les propositions avant de rédiger sa version humaine
finale. Aucune nouvelle phase, estimation, prévision, métrique test ou
opération commit/push/merge n’a été engagée pour produire ce document.
