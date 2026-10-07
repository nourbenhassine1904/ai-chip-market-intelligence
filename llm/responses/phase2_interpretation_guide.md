# Phase 2 — Guide pédagogique d'interprétation

Ce guide aide l'équipe à comprendre ses résultats et à formuler ensuite ses
propres explications. Il ne remplace pas l'interprétation humaine finale dans
`llm/human_analysis/phase2_interpretation.md`, qui reste inchangée. Les questions
à la fin de chaque section sont à traiter avec vos propres mots.

Toutes les valeurs ci-dessous proviennent des sorties Phase 2 existantes ;
elles sont arrondies pour faciliter la lecture. Aucun nouveau calcul statistique,
test ou modèle n'a été réalisé pour ce guide. Les observations visuelles sont
signalées comme telles et ne sont pas des coefficients nouvellement calculés.

Le [rapport Phase 2](phase2_eda_stationarity.md) fixe le cadre : **1 980 lignes
train**, du **2018-01-02 au 2025-11-14**, puis **220 lignes de test final**, du
**2025-11-17 au 2026-10-02**. Chaque série de rendements train possède
**1 979 valeurs**, car le rendement de la première observation est indéfini.
Les figures couvrant toute la période sont descriptives : la ligne verticale
et la zone grisée marquent le holdout. Seuls les résultats train peuvent guider
les futurs choix de modèle.

## 1. Price dynamics

### A. What the result shows

Le graphique des prix ajustés montre le **niveau du prix** à chaque date.
Une courbe qui monte signifie que ce niveau augmente ; une courbe qui descend
signifie qu'il diminue. Les trois trajectoires présentent une progression de
long terme, interrompue par des baisses. Visuellement, une baisse est notamment
visible en 2022, puis une reprise en 2023. Une progression générale ne signifie
donc pas une hausse régulière chaque jour.

Les panneaux des prix ont des échelles verticales différentes. Comparer la
hauteur apparente des courbes entre panneaux peut induire en erreur. Le prix
d'une action ou d'une part d'ETF n'est pas, à lui seul, une mesure de sa performance.

Le graphique **Base 100** donne le même point de départ à chaque actif :
`100 × P_t / P_0`, avec P égal à Adjusted Close. Il compare ainsi la progression
relative depuis la première observation, indépendamment des prix initiaux.
Dans cette formule, un indice supérieur à 100 signifie un prix ajusté supérieur
à celui du départ. La valeur de l'indice n'est pas directement un pourcentage
de gain : il faut la comparer à sa base 100.

### B. Evidence from our project

- [adjusted_close.png](../outputs/figures/phase2/adjusted_close.png) : niveaux de
  prix ajustés des trois actifs et alternance de hausses et de baisses.
- [normalized_prices_base100.png](../outputs/figures/phase2/normalized_prices_base100.png) :
  **à la fin du train, NVDA est visuellement en tête**, devant AMD puis SOXX.
  **À la fin de la période complète, AMD termine visuellement au-dessus de
  NVDA**, puis vient SOXX. Le classement dépend donc de la date retenue.
- [phase2_descriptive_stats.csv](../outputs/tables/phase2_descriptive_stats.csv),
  lignes `Adj_Close`, `scope=train` :

| Actif | Minimum train (USD ajustés) | Maximum train (USD ajustés) |
| --- | ---: | ---: |
| NVDA | 3.143212 | 206.545151 |
| AMD | 9.530000 | 264.329987 |
| SOXX | 45.085033 | 308.608276 |

Ces minima et maxima ne sont pas les prix de début et de fin : ils ne donnent
pas, à eux seuls, la performance entre ces deux dates. La figure complémentaire
[trading_volumes.png](../outputs/figures/phase2/trading_volumes.png) décrit les
volumes échangés, sans établir la cause des mouvements de prix.

### C. What we are allowed to conclude

On peut décrire les trajectoires observées, les épisodes de baisse et les
différences de progression relative. Pour comparer cette progression, Base 100
est plus informative que les niveaux de prix bruts. Il faut toujours préciser
la période : le classement à la fin du train et celui à la fin du graphique
complet ne sont pas identiques.

### D. What we must NOT conclude

Une hausse visuelle ne garantit aucune hausse future. Elle n'établit ni la
stationnarité ni la cause économique du mouvement. Aucun événement, aucune
actualité et aucune crise ne doivent être attribués à une date sur la seule
base de cette courbe. Le classement observé dans le holdout ne doit pas servir
à choisir un modèle ou une transformation.

### Questions for the team

- Pourquoi Base 100 facilite-t-elle la comparaison des trois actifs ?
- Quel actif est en tête à la fin du train, et à la fin du graphique complet ?
- Quelle période de baisse pouvez-vous décrire sans lui attribuer une cause ?

## 2. Returns

### A. What the result shows

Le prix mesure un niveau ; le **rendement mesure un changement entre deux
séances**. Ici, le log-rendement vaut `100 × [ln(P_t) − ln(P_{t−1})]`.
Un rendement positif correspond à une hausse, un rendement négatif à une
baisse. Il se rapproche du rendement simple en pourcentage pour de petits
mouvements, mais les deux ne sont pas identiques pour de grandes variations.

Les rendements fluctuent autour de valeurs faibles parce que les variations
quotidiennes sont généralement modestes par rapport au niveau du prix, avec
une alternance de signes. Leur moyenne est petite devant leur dispersion.
Cela n'impose pas une moyenne exactement nulle.

La largeur du « nuage » de rendements change visuellement au fil du temps.
Des séquences agitées voisinent avec des séquences plus calmes : c'est l'idée
du **volatility clustering**, ou regroupement des grandes variations dans
le temps. Le signe est secondaire pour cette question : une forte baisse et
une forte hausse sont toutes deux de grandes variations.

Les rendements au carré retirent le signe et accentuent les grandes amplitudes.
Ils servent d'indicateur de l'intensité des variations ; un carré isolé n'est
pas, à lui seul, une estimation complète de la variance conditionnelle.
La volatilité glissante résume la dispersion des 20 derniers rendements et
la convertit en mesure annualisée. Elle décrit le passé récent, sans prédire
automatiquement la prochaine séance.

### B. Evidence from our project

Dans [phase2_descriptive_stats.csv](../outputs/tables/phase2_descriptive_stats.csv),
les lignes `Log_Return`, `scope=train`, donnent :

| Actif | Moyenne quotidienne (%) | Écart-type quotidien (%) | Nombre de rendements |
| --- | ---: | ---: | ---: |
| NVDA | 0.184579 | 3.243598 | 1 979 |
| AMD | 0.157279 | 3.450861 | 1 979 |
| SOXX | 0.084901 | 2.219148 | 1 979 |

- [log_returns.png](../outputs/figures/phase2/log_returns.png) montre des
  amplitudes irrégulières, avec une agitation particulièrement visible autour
  du début de 2020 dans la partie train.
- [squared_log_returns.png](../outputs/figures/phase2/squared_log_returns.png)
  rend les fortes variations positives et négatives comparables en amplitude.
- [rolling_volatility_20d.png](../outputs/figures/phase2/rolling_volatility_20d.png)
  montre des bosses et des phases plus basses, plutôt qu'une dispersion
  historique uniforme.

Ces trois figures couvrent la période complète ; pour préparer les diagnostics
futurs, on se limite à leur partie train et à l'ACF des carrés train, section 6.

### C. What we are allowed to conclude

AMD a le plus grand écart-type quotidien sur train parmi les trois actifs,
puis NVDA et SOXX. Les figures train suggèrent une concentration temporelle
des grandes variations. Avec l'ACF des carrés déjà disponible, cela rend utile
un futur diagnostic ARCH, sans préjuger de son résultat.

### D. What we must NOT conclude

Une moyenne positive ne garantit pas un gain quotidien ni une rentabilité
future. Les pics de volatilité ne permettent pas d'en identifier la cause.
On ne peut pas affirmer que GARCH est nécessaire. La volatilité annualisée
n'est ni le rendement annuel ni une perte annuelle prévue. Enfin, des
rendements jugés stationnaires peuvent avoir une variance **conditionnelle**
qui évolue : stationnarité et regroupement de volatilité ne s'excluent pas.

### Questions for the team

- Quelle différence faites-vous entre le prix et le rendement ?
- Pourquoi regarder les carrés des rendements plutôt que leurs seuls signes ?
- Quel actif a le plus grand écart-type train ?

## 3. Distribution

### A. What the result shows

L'histogramme compte les rendements dans différents intervalles. Il montre
beaucoup de petites variations près du centre et quelques variations éloignées.
Le boxplot résume la médiane et les quartiles ; les points au-delà des moustaches
signalent des observations éloignées selon la règle IQR, pas des erreurs avérées.

La **skewness** mesure l'asymétrie. Une valeur négative indique davantage
d'asymétrie du côté des rendements négatifs ; une valeur positive, du côté
positif. Les valeurs observées sont relativement proches de zéro : l'asymétrie
est modérée dans cet échantillon, sans être nécessairement absente.

La **kurtosis excédentaire** compare le quatrième moment standardisé à celui
de la normale, dont la référence est zéro. Elle est sensible aux observations
très éloignées du centre. Une valeur positive suggère un profil plus
**leptokurtique** que la normale, compatible avec des queues plus épaisses :
les variations extrêmes pèsent davantage relativement à la dispersion globale.
Ce constat ne détermine pas une loi théorique précise des queues.

Le **QQ-plot normal** compare les quantiles observés à ceux d'une normale.
Un alignement approximatif sur la droite serait compatible avec cette référence.
Dans nos figures, le centre s'en approche davantage que les extrémités, qui
s'écartent de la droite. Cet écart aide à repérer des queues mal décrites par
une normale ; il ne constitue pas un nouveau test de normalité.

### B. Evidence from our project

Source numérique : [phase2_descriptive_stats.csv](../outputs/tables/phase2_descriptive_stats.csv),
`Log_Return`, `scope=train`.

| Actif | Skewness | Kurtosis excédentaire |
| --- | ---: | ---: |
| NVDA | −0.192489 | 4.698018 |
| AMD | 0.250518 | 3.571357 |
| SOXX | −0.208953 | 5.126085 |

Les trois figures train permettent de lire ces résultats de façon complémentaire :
[histogrammes](../outputs/figures/phase2/return_histograms_train.png),
[boxplots](../outputs/figures/phase2/return_boxplots_train.png) et
[QQ-plots](../outputs/figures/phase2/return_qqplots_train.png).
Les boxplots présentent des points éloignés des deux côtés ; les QQ-plots
présentent des écarts visibles dans les deux queues.

### C. What we are allowed to conclude

Les trois distributions empiriques ont une kurtosis excédentaire positive,
avec des observations extrêmes qui pèsent sensiblement. Une approximation
normale doit donc être discutée, notamment dans les queues. SOXX possède la
plus grande kurtosis excédentaire de cet échantillon, mais le plus faible
écart-type : **l'épaisseur relative des queues et l'amplitude globale des
variations sont deux notions différentes**.

### D. What we must NOT conclude

Une skewness faible ne prouve pas la normalité. La kurtosis n'est pas la
probabilité d'une crise ni un pourcentage de risque. On ne peut pas conclure
que SOXX est le plus volatil simplement parce que sa kurtosis est la plus haute.
Ces figures et moments empiriques ne démontrent pas une distribution exacte,
ni une fréquence future précise d'événements extrêmes. Aucun nouveau test
de normalité n'est effectué ici.

### Questions for the team

- Que signifie le signe de la skewness de NVDA ?
- Pourquoi une kurtosis proche de zéro et une skewness proche de zéro ne suffiraient-elles pas à prouver la normalité ?
- Comment SOXX peut-il avoir une kurtosis plus forte mais un écart-type plus faible ?

## 4. Correlations

### A. What the result shows

La corrélation de Pearson mesure à quel point deux séries de rendements
évoluent ensemble de façon **linéaire et à la même date**. Une valeur positive
signifie une tendance à varier dans le même sens. Une valeur proche de 1
indique une association positive forte ; elle ne signifie pas des rendements
identiques chaque jour.

Les corrélations globales train sont toutes positives et assez élevées.
Le contexte sectoriel commun des actifs étudiés rend des mouvements communs
plausibles, mais ces sorties ne permettent pas d'identifier les facteurs
responsables ni leur contribution. Une corrélation élevée décrit une
association ; elle n'en explique pas le mécanisme.

La corrélation glissante répète cette description sur les 60 dernières séances.
Ses variations montrent que l'intensité de l'association observée dépend de
la fenêtre. Certaines valeurs locales sont nettement plus faibles que la
corrélation globale : « élevée sur train » ne signifie pas « élevée à chaque date ».

### B. Evidence from our project

Sources : [phase2_return_correlation_train.csv](../outputs/tables/phase2_return_correlation_train.csv),
[matrice graphique](../outputs/figures/phase2/return_correlation_train.png),
[phase2_rolling_correlation_summary.csv](../outputs/tables/phase2_rolling_correlation_summary.csv)
et [rolling_correlations_60d.png](../outputs/figures/phase2/rolling_correlations_60d.png).
Tous ces résultats utilisent train.

| Paire | Corrélation globale | Moyenne glissante | Médiane glissante | Minimum glissant | Maximum glissant | Écart-type glissant |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| NVDA/AMD | 0.684939 | 0.669317 | 0.659535 | 0.153628 | 0.936150 | 0.158178 |
| NVDA/SOXX | 0.819116 | 0.795832 | 0.800200 | 0.505620 | 0.956457 | 0.100340 |
| AMD/SOXX | 0.744839 | 0.738390 | 0.733277 | 0.348225 | 0.943442 | 0.126886 |

La paire la plus corrélée globalement est **NVDA/SOXX** ; la moins corrélée
est **NVDA/AMD**. Dans ce résumé, NVDA/AMD présente aussi le plus grand
écart-type des corrélations glissantes. Les fenêtres glissantes se chevauchent :
leurs valeurs ne sont pas des observations indépendantes. Leur moyenne n'est
pas nécessairement égale à la corrélation calculée sur toute la période train.

### C. What we are allowed to conclude

Il existe une association linéaire contemporaine positive entre les trois
actifs sur train. Cette association est la plus forte pour NVDA/SOXX et varie
dans les fenêtres de 60 séances. Cela justifie de s'intéresser plus tard à
leurs relations multivariées, tout en gardant distinctes association,
prévisibilité et causalité.

### D. What we must NOT conclude

**Corrélation ≠ causalité.** Ces coefficients ne disent pas qu'un actif
provoque les variations d'un autre. Ils ne donnent pas le sens d'une influence,
ne démontrent aucune relation décalée dans le temps et ne prouvent pas la
cointégration des log-prix. Une corrélation élevée n'assure pas non plus
qu'un modèle multivarié améliorera les prévisions.

### Questions for the team

- Quelle paire possède la plus forte corrélation globale train ?
- Pourquoi une corrélation de 0.684939 ne signifie-t-elle pas des variations identiques ?
- Que nous apprend le minimum glissant de NVDA/AMD par rapport à sa corrélation globale ?

## 5. Outliers

### A. What the result shows

Un **outlier IQR** est un rendement situé hors d'un intervalle construit à
partir des quartiles train. Q1 et Q3 délimitent la moitié centrale des
observations ; leur différence est l'IQR. Les bornes sont
`Q1 − 1.5 × IQR` et `Q3 + 1.5 × IQR`. Un point au-delà de ces bornes est
éloigné de cette zone centrale selon une convention explicable.

Cette définition est relative à la distribution de chaque actif. Les bornes
ne sont donc pas identiques pour NVDA, AMD et SOXX. Être signalé par cette
règle ne signifie ni donnée impossible ni faute de saisie. Une grande variation
financière peut être réelle et importante pour comprendre les risques.

### B. Evidence from our project

[phase2_outlier_summary.csv](../outputs/tables/phase2_outlier_summary.csv)
contient les seuils appris sur train. Les proportions sont calculées sur
les **1 979 rendements valides** de chaque actif.

| Actif | Borne basse (%) | Borne haute (%) | Nombre d'outliers | Proportion (%) |
| --- | ---: | ---: | ---: | ---: |
| NVDA | −6.758199 | 7.207811 | 74 | 3.739262 |
| AMD | −7.262539 | 7.614065 | 89 | 4.497221 |
| SOXX | −4.653354 | 4.937422 | 74 | 3.739262 |

[phase2_extreme_returns.csv](../outputs/tables/phase2_extreme_returns.csv)
liste les dix plus grandes variations absolues train par actif. Parmi elles :

| Actif | Date | Log-rendement quotidien (%) |
| --- | --- | ---: |
| NVDA | 2023-05-25 | 21.808791 |
| NVDA | 2018-11-16 | −20.771106 |
| AMD | 2025-04-09 | 21.366259 |
| AMD | 2018-10-25 | −16.777238 |
| SOXX | 2025-04-09 | 17.034684 |
| SOXX | 2020-03-16 | −16.520227 |

Les valeurs sont bien des **log-rendements**, pas des rendements simples
interchangeables à ces amplitudes. La table des extrêmes est une sélection
de dix dates par actif, pas la liste complète de tous les outliers IQR.

### C. What we are allowed to conclude

AMD compte davantage d'outliers IQR sur train que les deux autres actifs,
selon les seuils propres à chacun. Les grandes variations des deux signes
doivent être conservées et examinées. Elles pourront peser dans les futurs
diagnostics de volatilité et de queues de distribution. La Phase 2 les
signale sans les supprimer, les corriger automatiquement ou les winsoriser.

### D. What we must NOT conclude

Le nombre d'outliers ne mesure pas, à lui seul, tous les aspects du risque.
Il ne prouve pas une mauvaise qualité des données. Les 74 observations de
NVDA et de SOXX ne correspondent pas nécessairement aux mêmes dates.
Une date extrême ne doit pas être reliée automatiquement à une actualité
ou à une crise. Supprimer ces journées pour obtenir une distribution plus
« propre » ferait perdre de l'information financière importante.

### Questions for the team

- Que signifie concrètement un rendement situé au-dessus de la borne IQR ?
- Pourquoi les seuils diffèrent-ils selon l'actif ?
- Pourquoi ne faut-il pas supprimer automatiquement une grande variation ?

## 6. ACF/PACF

### A. What the result shows

L'**ACF** compare une série à ses propres valeurs passées. Le lag 1 représente
une séance de retard ; le lag 5, cinq séances. La **PACF** cherche l'association
avec un retard donné après prise en compte des retards intermédiaires.
Les bandes colorées sont des intervalles de référence ponctuels à 95 %.

**Prix / Adjusted Close.** Pour les trois actifs, l'ACF reste fortement positive
et décroît lentement jusqu'au dernier retard affiché. Les prix proches dans le
temps se ressemblent beaucoup. La PACF présente un premier retard dominant.
Cette forte persistance est compatible avec les résultats de non-stationnarité,
mais le graphique ne constitue pas, à lui seul, un test de racine unitaire.

**Log-rendements.** Les ACF et PACF sont beaucoup plus proches de zéro que
celles des niveaux. Quelques points sortent des bandes ; il serait donc
incorrect de déclarer que toute autocorrélation est absente. La dépendance
linéaire apparaît néanmoins bien plus faible que dans les prix.

**Rendements au carré.** Les premiers retards de l'ACF présentent une
dépendance positive plus visible et plus suivie, particulièrement pour SOXX.
Cela concerne l'amplitude des variations, sans indiquer leur signe futur.
Cette lecture complète l'observation du regroupement de volatilité.

### B. Evidence from our project

Chaque figure ci-dessous est calculée sur **TRAIN**, avec **40 retards**.
Les lectures précédentes sont visuelles : aucun coefficient supplémentaire
n'a été recalculé pour ce guide.

| Actif | Prix : ACF/PACF | Log-rendements : ACF/PACF | Carrés : ACF |
| --- | --- | --- | --- |
| NVDA | [Prix](../outputs/figures/phase2/nvda_adj_close_acf_pacf_train.png) | [Rendements](../outputs/figures/phase2/nvda_log_return_acf_pacf_train.png) | [Carrés](../outputs/figures/phase2/nvda_squared_returns_acf_train.png) |
| AMD | [Prix](../outputs/figures/phase2/amd_adj_close_acf_pacf_train.png) | [Rendements](../outputs/figures/phase2/amd_log_return_acf_pacf_train.png) | [Carrés](../outputs/figures/phase2/amd_squared_returns_acf_train.png) |
| SOXX | [Prix](../outputs/figures/phase2/soxx_adj_close_acf_pacf_train.png) | [Rendements](../outputs/figures/phase2/soxx_log_return_acf_pacf_train.png) | [Carrés](../outputs/figures/phase2/soxx_squared_returns_acf_train.png) |

La PACF des log-rendements utilise la méthode `ywm`, d'après le
[rapport Phase 2](phase2_eda_stationarity.md). Les log-rendements sont la
première différence des **log-prix**, multipliée par 100 ; ils ne sont pas
la différence en dollars des prix bruts.

### C. What we are allowed to conclude

On peut distinguer la forte persistance des niveaux, la dépendance linéaire
plus faible des rendements et la dépendance de leurs amplitudes. **Ces
observations pourront guider les diagnostics des phases suivantes.**
L'ACF des carrés donne notamment une motivation pour examiner ultérieurement
la variance conditionnelle avec un diagnostic ARCH adapté.

### D. What we must NOT conclude

On ne choisit ici **aucun ordre ARIMA ou GARCH**. Une forte ACF des prix peut
refléter leur non-stationnarité ; elle ne suffit pas à justifier un modèle
sur leurs niveaux. Des rendements peu autocorrélés ne sont pas nécessairement
indépendants : une dépendance de l'amplitude peut subsister.

Un point hors d'une bande ponctuelle n'est pas une preuve isolée définitive :
on regarde de nombreux retards, et les bandes ne corrigent pas l'ensemble
de ces comparaisons. Une ACF des carrés positive ne remplace pas ARCH-LM
et ne garantit pas une amélioration des prévisions par GARCH.

### Questions for the team

- Quelle différence voyez-vous entre l'ACF des prix et celle des rendements ?
- Que compare l'ACF des rendements au carré ?
- Pourquoi des rendements peu autocorrélés peuvent-ils encore être dépendants ?

## 7. Stationarity

### A. What the result shows

Intuitivement, une série stationnaire garde un fonctionnement statistique
stable lorsqu'on décale l'origine du temps. Pour la stationnarité faible,
cela concerne la moyenne, la variance et les covariances, qui dépendent des
retards plutôt que de la date. Cela n'impose ni valeurs constantes ni loi
normale. ADF et KPSS explorent des aspects de cette question ; ils ne vérifient
pas toutes les formes possibles de stabilité.

Les tests partent d'hypothèses nulles **opposées** :

| Test | Hypothèse nulle H0 | Si p < 0.05 | Si p ≥ 0.05 |
| --- | --- | --- | --- |
| ADF | Présence d'une racine unitaire | Rejeter la racine unitaire | Ne pas rejeter la racine unitaire |
| KPSS | Stationnarité autour du niveau ou de la tendance spécifiée | Rejeter cette stationnarité | Ne pas rejeter cette stationnarité |

Une racine unitaire décrit notamment une situation où les effets des chocs
ne se dissipent pas comme dans une série stationnaire revenant autour d'un
fonctionnement stable. Mais ADF ne couvre pas toutes les causes de
non-stationnarité.

Pour les prix et log-prix, les deux tests incluent une **constante et une
tendance linéaire** (`ct`). Pour les log-rendements, ils incluent une
**constante** (`c`). Les résultats doivent être lus avec ces spécifications :
le rejet KPSS sur les niveaux porte ici sur la stationnarité autour d'une
tendance linéaire, pas seulement autour d'une moyenne constante.

### B. Evidence from our project

Sources : [phase2_stationarity_tests.csv](../outputs/tables/phase2_stationarity_tests.csv)
et [phase2_stationarity_summary.csv](../outputs/tables/phase2_stationarity_summary.csv).
Tous les tests utilisent train. ADF sélectionne ses retards avec
`autolag="AIC"` ; KPSS utilise `nlags="auto"`.

| Actif | Série | p-value ADF | p-value KPSS interprétable | Synthèse mécanique |
| --- | --- | ---: | ---: | --- |
| NVDA | Adjusted Close | 0.988692 | <0.01 | nonstationary_supported |
| NVDA | Log Price | 0.461103 | <0.01 | nonstationary_supported |
| NVDA | Log Return | 7.911432e-27 | >0.10 | stationary_supported |
| AMD | Adjusted Close | 0.487496 | 0.015277 | nonstationary_supported |
| AMD | Log Price | 0.416796 | <0.01 | nonstationary_supported |
| AMD | Log Return | 0.0 numérique | >0.10 | stationary_supported |
| SOXX | Adjusted Close | 0.459873 | <0.01 | nonstationary_supported |
| SOXX | Log Price | 0.277134 | <0.01 | nonstationary_supported |
| SOXX | Log Return | 7.599931e-28 | >0.10 | stationary_supported |

**Comment lire une ligne :** pour le log-prix NVDA, ADF donne 0.461103,
au-dessus de 0.05 : il ne rejette pas la racine unitaire. KPSS donne une
p-value réellement inférieure à 0.01 : il rejette la stationnarité spécifiée.
Les deux résultats vont donc dans le sens de la non-stationnarité. Pour le
log-rendement NVDA, les décisions s'inversent : ADF rejette fortement sa H0
et KPSS ne rejette pas la sienne. La stationnarité est alors soutenue.

Les CSV enregistrent **0.01** ou **0.10** pour les p-values KPSS qui atteignent
les limites de la table de référence. Les warnings et `p_value_bound` indiquent
respectivement une vraie p-value **plus petite** ou **plus grande** ; ce ne
sont pas des p-values exactes. Le zéro numérique ADF d'AMD ne doit pas être
présenté comme une probabilité mathématiquement exactement nulle. Les warnings
d'évolution d'API statsmodels sont aussi enregistrés ; ils concernent le format
futur des résultats, sans changer la lecture des valeurs présentes.

### C. What we are allowed to conclude

Pour les trois actifs, les décisions ADF et KPSS concordent :

- prix et log-prix : **non-stationnarité soutenue** ;
- log-rendements : **stationnarité soutenue**.

Les deux tests sont plus informatifs qu'ADF seul : ils examinent la série
en partant d'hypothèses opposées. Leur concordance renforce le diagnostic,
sans être deux preuves indépendantes ou une certitude absolue. En cas de
désaccord, le résumé prévu serait `mixed_evidence` ; aucune des neuf lignes
du résumé actuel ne porte cette étiquette.

### D. What we must NOT conclude

**Ne pas rejeter H0 n'est pas prouver H0.** Une p-value n'est pas la probabilité
que H0 soit vraie. Les décisions dépendent de la période, des retards, des
termes déterministes, de la puissance du test et d'éventuelles ruptures.
Prendre le logarithme ne suffit manifestement pas ici à rendre les niveaux
stationnaires. La stationnarité soutenue des rendements ne prouve ni leur
normalité, ni leur indépendance, ni une variance conditionnelle constante,
ni leur stabilité garantie dans le holdout ou dans le futur.

### Questions for the team

- Quelles sont les deux hypothèses nulles, pour ADF et pour KPSS ?
- Pourquoi les deux tests soutiennent-ils la non-stationnarité des log-prix ?
- Pourquoi « KPSS ne rejette pas » est-il différent de « la stationnarité est prouvée » ?

## 8. Consequences for modeling

### A. What the result shows

Les résultats donnent des **pistes provisoires**, pas une liste de modèles
à appliquer automatiquement. Les prix et log-prix conservent de la persistance
et un diagnostic de non-stationnarité ; les log-rendements sont des variables
stationnaires plausibles pour les étapes suivantes.

Un futur VAR standard devra probablement utiliser des variables stationnaires,
avec ses propres validations. Les log-prix pourront rester utiles pour de
futurs tests de cointégration : ces tests examinent si une combinaison de
séries non stationnaires peut être stationnaire. Les diagnostics actuels
sont compatibles avec des log-prix intégrés d'ordre un, mais ne constituent
pas à eux seuls une vérification exhaustive de cette condition. Ni une
cointégration ni un VECM ne sont établis aujourd'hui.

Les ACF des carrés peuvent motiver un futur ARCH-LM, sans imposer GARCH.
La faible autocorrélation linéaire des rendements ne suffit pas à affirmer
qu'aucune prévision utile n'est possible, ou qu'un modèle complexe sera utile.

Une décomposition STL sépare le log-prix en tendance, composante saisonnière
et résidu, **pour la période imposée**. Ici, `period=5` est une hypothèse de
cycle de cinq séances, avec `robust=True` pour limiter l'influence des extrêmes
sur l'ajustement. L'apparition d'une composante appelée « Seasonal » ne
démontre donc pas une saisonnalité exploitable. Cinq séances observées ne
correspondent pas toujours à une semaine calendaire, à cause des jours sans
cotation. SARIMA ne peut pas être décidé automatiquement.

### B. Evidence from our project

- [phase2_stationarity_summary.csv](../outputs/tables/phase2_stationarity_summary.csv) :
  les six lignes prix/log-prix sont `nonstationary_supported` ; les trois lignes
  log-rendements sont `stationary_supported`.
- Les ACF des carrés train de [NVDA](../outputs/figures/phase2/nvda_squared_returns_acf_train.png),
  [AMD](../outputs/figures/phase2/amd_squared_returns_acf_train.png) et
  [SOXX](../outputs/figures/phase2/soxx_squared_returns_acf_train.png)
  montrent la dépendance des amplitudes décrite en section 6.
- Les STL de [NVDA](../outputs/figures/phase2/nvda_log_price_stl_train.png),
  [AMD](../outputs/figures/phase2/amd_log_price_stl_train.png) et
  [SOXX](../outputs/figures/phase2/soxx_log_price_stl_train.png)
  annoncent explicitement `TRAIN`, `period=5`, `robust=True` et le caractère
  exploratoire de l'hypothèse hebdomadaire.
- [phase2_weekday_returns.csv](../outputs/tables/phase2_weekday_returns.csv)
  et [weekday_returns_train.png](../outputs/figures/phase2/weekday_returns_train.png)
  décrivent des différences de moyennes selon le jour. Par exemple, AMD affiche
  **0.495498 % le lundi** contre **−0.027712 % le vendredi**, avec respectivement
  **370** et **398** observations, et des écarts-types de **3.419089 %** et
  **3.130801 %**. La moyenne du vendredi est négative alors que sa médiane
  est **0.037836 %** : moyenne et journée « typique » ne sont pas identiques.
  Ces descriptions ne constituent pas un test d'effet hebdomadaire.
- [phase2_leakage_check.csv](../outputs/tables/phase2_leakage_check.csv)
  comporte **12 statuts PASS**. Il combine des assertions mesurées avec des
  contrôles explicitement nommés « Code audit » sur le périmètre des diagnostics.
  Le [rapport Phase 2](phase2_eda_stationarity.md) précise que les fenêtres sont
  rétrospectives et qu'aucun scaler n'est ajusté sur toute la période.

### C. What we are allowed to conclude

Les prochains travaux devront vérifier les hypothèses propres à chaque
méthode avant toute conclusion définitive : stationnarité des variables du
VAR, conditions des tests de cointégration, éventuelle dépendance conditionnelle
de variance et réalité d'une structure saisonnière exploitable. Les résultats
actuels organisent ces questions ; ils ne donnent pas encore leurs réponses.

Les choix et validations intermédiaires doivent rester dans train. Le holdout
final doit conserver son rôle d'évaluation hors échantillon. Une future feature
utilisable à une date doit être connue à cette date : la volatilité glissante
est rétrospective, mais son usage dépendra de l'instant de prévision. Les
composantes STL, lissées avec des observations de part et d'autre au sein du
train, ne sont pas directement des features causales disponibles en temps réel.

### D. What we must NOT conclude

On ne choisit automatiquement ni SARIMA, ni GARCH, ni un ordre de modèle.
On n'affirme ni cointégration ni nécessité d'un VECM. Les différences par
jour de semaine ne prouvent pas un effet stable et exploitable ; un panneau
STL « Seasonal » ne le prouve pas davantage. Le caractère multivarié des données
ne garantit pas la supériorité d'un VAR ou d'un réseau neuronal.

Les statuts anti-leakage de Phase 2 ne dispensent pas de nouveaux contrôles
lors de la construction des futurs modèles. Aucun ARCH-LM, test de
cointégration, modèle ou nouveau test statistique n'est exécuté dans ce guide.

### Questions for the team

- Pourquoi les log-rendements sont-ils des candidats plausibles pour un futur VAR standard ?
- Quelle différence faites-vous entre corrélation des rendements et cointégration des log-prix ?
- Pourquoi une composante saisonnière STL ne suffit-elle pas à choisir SARIMA ?
- Pourquoi devons-nous garder le test final à l'écart des choix de modèle ?
