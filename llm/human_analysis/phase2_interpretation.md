# Human Interpretation — Phase 2

## 1. Price dynamics

Sur la période étudiée, nous observons que les trois actifs NVDA, AMD et SOXX
présentent globalement une progression de long terme, mais cette évolution
n'est pas régulière. Les trajectoires sont marquées par plusieurs périodes
de hausse et de baisse. Une phase de baisse importante est notamment visible
autour de 2022, suivie d'une reprise à partir de 2023.

Le graphique des prix ajustés permet d'observer les niveaux de prix, mais il
n'est pas suffisant pour comparer directement les performances des trois actifs,
car leurs prix initiaux et leurs échelles sont différents.

Le graphique en base 100 est donc plus adapté pour cette comparaison. Il place
les trois actifs au même niveau initial de 100 et permet d'observer leur
progression relative depuis le début de la période. À la fin de la période
d'entraînement, NVDA apparaît comme l'actif ayant enregistré la progression
relative la plus importante, devant AMD et SOXX.

Nous remarquons également que le classement peut changer selon la date
considérée. Par exemple, sur la période descriptive complète incluant le
holdout final, AMD termine visuellement au-dessus de NVDA. Cette information
reste descriptive et ne doit pas être utilisée pour choisir un modèle, puisque
le jeu de test doit rester réservé à l'évaluation finale.

Ces graphiques permettent donc de décrire les mouvements observés, mais ils ne
permettent pas d'identifier leurs causes économiques. Nous évitons ainsi
d'attribuer une hausse ou une baisse à un événement précis sans vérification
supplémentaire.

## 2. Returns

Les log-rendements représentent les variations quotidiennes des prix plutôt
que leur niveau. Contrairement aux prix, ils fluctuent autour de valeurs
relativement faibles et prennent des valeurs positives ou négatives.

Sur la période d'entraînement, le rendement logarithmique moyen quotidien est
d'environ 0.185 % pour NVDA, 0.157 % pour AMD et 0.085 % pour SOXX. Ces moyennes
sont faibles par rapport à leurs écarts-types respectifs, qui sont d'environ
3.24 %, 3.45 % et 2.22 %. Cela montre que les variations quotidiennes sont
beaucoup plus importantes que le niveau du rendement moyen.

AMD présente ici l'écart-type quotidien le plus élevé, suivi par NVDA, tandis
que SOXX présente la dispersion la plus faible parmi les trois actifs.

Les graphiques des rendements montrent aussi que leur variance ne semble pas
constante au cours du temps. Certaines périodes relativement calmes sont suivies
de périodes comportant de nombreuses variations de forte amplitude.

Ce phénomène ressemble à ce que nous avons étudié en cours sous le nom de
volatility clustering : les périodes de forte volatilité ont tendance à être
regroupées dans le temps.

Le graphique des rendements au carré renforce visuellement cette observation,
car il élimine le signe du rendement et met davantage en évidence les périodes
où l'amplitude des variations est importante.

À ce stade, nous pouvons seulement dire que les données suggèrent une dynamique
de volatilité intéressante. Nous ne pouvons pas encore conclure qu'un modèle
GARCH est nécessaire. Cette hypothèse devra être vérifiée plus tard avec un
test ARCH-LM appliqué aux résidus d'un modèle de moyenne approprié.

## 3. Distribution

L'étude des histogrammes, boxplots et QQ-plots montre que les distributions
des log-rendements ne semblent pas parfaitement compatibles avec une
distribution normale.

Sur le jeu d'entraînement, la skewness vaut environ :

- -0.192 pour NVDA ;
- 0.251 pour AMD ;
- -0.209 pour SOXX.

Ces valeurs restent relativement proches de zéro. L'asymétrie des distributions
est donc modérée : NVDA et SOXX présentent une légère asymétrie négative,
tandis qu'AMD présente une légère asymétrie positive.

En revanche, les kurtosis excédentaires sont nettement positives :

- NVDA : environ 4.70 ;
- AMD : environ 3.57 ;
- SOXX : environ 5.13.

Comme la kurtosis excédentaire d'une distribution normale est égale à zéro,
ces valeurs indiquent que les distributions empiriques présentent davantage
d'observations extrêmes dans les queues que ce que suggérerait une distribution
normale. On parle alors de distributions à queues épaisses ou leptokurtiques.

Les QQ-plots confirment visuellement cette observation : les points sont plus
proches de la droite théorique au centre de la distribution, mais s'en écartent
davantage dans les extrémités.

Nous ne pouvons cependant pas conclure qu'une distribution théorique précise
est correcte uniquement à partir de ces graphiques. De même, une kurtosis plus
élevée ne signifie pas automatiquement une volatilité globale plus élevée.
SOXX possède par exemple la kurtosis la plus élevée alors que son écart-type
des rendements est le plus faible des trois actifs.

Ces résultats seront importants plus tard pour les diagnostics des modèles,
notamment lorsque nous étudierons les résidus et les modèles de volatilité.

## 4. Correlations

Les corrélations contemporaines des log-rendements calculées uniquement sur
la période d'entraînement sont toutes positives :

- NVDA / AMD : environ 0.685 ;
- NVDA / SOXX : environ 0.819 ;
- AMD / SOXX : environ 0.745.

La relation la plus forte est donc observée entre NVDA et SOXX. La relation
NVDA/AMD reste également élevée mais constitue la plus faible des trois paires.

Ces résultats montrent que les rendements des trois actifs ont tendance à
évoluer dans le même sens au cours d'une même séance. Cela est cohérent avec
l'idée que les trois séries appartiennent à un environnement financier proche,
mais cette observation ne permet pas d'en identifier la cause.

L'analyse des corrélations glissantes sur 60 séances montre également que ces
relations ne sont pas constantes dans le temps. Par exemple, la corrélation
NVDA/AMD varie approximativement entre 0.15 et 0.94, tandis que NVDA/SOXX varie
entre environ 0.51 et 0.96.

La corrélation statique calculée sur toute la période d'entraînement résume
donc une relation qui évolue dans le temps.

Cette analyse justifie l'intérêt d'une modélisation multivariée ultérieure,
mais elle ne prouve pas qu'un actif provoque les mouvements d'un autre.
Une corrélation élevée ne signifie pas causalité. La causalité au sens de
Granger sera étudiée ultérieurement dans le cadre du VAR et devra elle-même
être interprétée comme une relation de prévisibilité temporelle, et non comme
une causalité économique réelle.

## 5. Outliers

La méthode IQR appliquée aux log-rendements du jeu d'entraînement identifie :

- 74 observations atypiques pour NVDA ;
- 89 pour AMD ;
- 74 pour SOXX.

Cela représente environ 3.74 % des rendements de NVDA, 4.50 % de ceux d'AMD
et 3.74 % de ceux de SOXX.

Les variations extrêmes sont importantes. Par exemple, certains log-rendements
journaliers dépassent 20 % en valeur absolue pour NVDA ou AMD.

Cependant, une observation classée comme outlier par la méthode IQR n'est pas
nécessairement une erreur de données. Sur un marché financier, une variation
journalière très importante peut être une observation réelle et contenir une
information essentielle sur le risque.

Pour cette raison, nous avons choisi de conserver toutes les observations.
Nous n'avons effectué ni suppression, ni winsorisation, ni correction
automatique des rendements extrêmes.

Cette décision est également importante pour la future analyse de volatilité :
supprimer artificiellement les plus grands mouvements pourrait réduire les
effets que les modèles ARCH/GARCH sont justement destinés à étudier.

Nous restons toutefois prudents dans l'interprétation des dates extrêmes.
Une date présentant un rendement important ne peut pas être associée
automatiquement à une crise ou à une actualité sans vérification externe.

## 6. ACF/PACF

Les graphiques ACF et PACF présentent des comportements très différents selon
que nous observons les prix ou les log-rendements.

Pour les prix ajustés, l'ACF reste fortement positive sur de nombreux retards
et décroît lentement. Cela montre une forte persistance temporelle : deux prix
proches dans le temps ont tendance à être eux-mêmes très proches.

Ce comportement est cohérent avec une série non stationnaire. Il serait donc
dangereux d'interpréter directement cette forte autocorrélation comme une
structure AR exploitable sans traiter d'abord la stationnarité.

Pour les log-rendements, l'ACF et la PACF sont beaucoup plus proches de zéro.
La dépendance linéaire temporelle semble donc nettement plus faible que pour
les prix. Certains retards peuvent néanmoins dépasser les bandes de confiance,
ce qui signifie que nous ne pouvons pas affirmer que toute autocorrélation
est absente.

Nous avons également étudié l'ACF des rendements au carré. Celle-ci présente
des autocorrélations positives plus visibles à plusieurs retards, notamment
pour certaines séries. Cela signifie que l'amplitude des variations peut
rester dépendante dans le temps même lorsque les rendements eux-mêmes sont
faiblement autocorrélés.

Ce résultat est cohérent avec l'observation précédente du volatility clustering
et motive la réalisation future d'un test ARCH-LM.

À ce stade, nous ne choisissons aucun ordre ARIMA à partir de ces graphiques.
Ils serviront de point de départ en Phase 3 pour proposer des ordres p et q,
qui devront ensuite être comparés avec les critères AIC/BIC et surtout validés
par les diagnostics des résidus.

De même, l'ACF des rendements au carré ne suffit pas à décider qu'un modèle
GARCH doit être estimé.

## 7. Stationarity

Nous avons utilisé les tests ADF et KPSS car ils possèdent des hypothèses
nulles complémentaires.

Pour le test ADF :

H0 : la série possède une racine unitaire, donc elle est non stationnaire.

Pour le test KPSS :

H0 : la série est stationnaire autour de la composante déterministe spécifiée.

Pour les trois actifs, les résultats sur les prix ajustés et les log-prix
sont cohérents :

- ADF ne rejette pas l'hypothèse de racine unitaire ;
- KPSS rejette l'hypothèse de stationnarité.

Nous avons donc deux diagnostics allant dans le sens d'une non-stationnarité
des prix et des log-prix.

Pour les log-rendements, le résultat est inverse :

- ADF rejette très fortement l'hypothèse de racine unitaire ;
- KPSS ne rejette pas l'hypothèse de stationnarité.

La stationnarité des log-rendements est donc soutenue pour NVDA, AMD et SOXX.

Comme le log-rendement correspond à la première différence du log-prix,
multipliée par 100, ces résultats sont compatibles avec l'idée que les
log-prix se comportent approximativement comme des séries intégrées d'ordre 1,
I(1), tandis que leur première différence est I(0).

Cela suggère qu'une différenciation d'ordre d = 1 constitue un point de départ
naturel lorsqu'un futur modèle ARIMA est appliqué au log-prix. Ce choix devra
néanmoins être confirmé dans la phase de modélisation.

Il faut également rester prudent : ne pas rejeter une hypothèse n'est pas la
même chose que prouver qu'elle est vraie. Les tests dépendent de la période,
du nombre de retards et de la spécification déterministe choisie.

## 8. Consequences for modeling

Les résultats de la Phase 2 donnent maintenant une direction claire pour les
phases suivantes, sans imposer encore un modèle définitif.

Premièrement, pour la prévision univariée de NVDA, les prix et log-prix étant
non stationnaires, un modèle ARIMA sur le log-prix devra probablement utiliser
une différenciation d'ordre 1. Les graphiques ACF/PACF des séries stationnaires
serviront ensuite à proposer quelques valeurs raisonnables de p et q. Ces
ordres devront être confirmés par les critères d'information et surtout par
les diagnostics des résidus. Une baseline naïve ou random walk devra également
être construite afin de vérifier que le modèle ARIMA apporte réellement une
amélioration.

Deuxièmement, les log-rendements de NVDA, AMD et SOXX sont stationnaires selon
les diagnostics ADF/KPSS. Ils constituent donc des candidats naturels pour
un futur VAR standard destiné à analyser les interactions dynamiques de court
terme entre les trois actifs. Le nombre de retards devra être choisi avec les
critères AIC/BIC puis validé par les diagnostics du modèle.

Troisièmement, les log-prix restent importants malgré leur non-stationnarité.
Comme ils semblent compatibles avec des séries I(1), ils pourront être utilisés
pour tester la cointégration. Une éventuelle relation de long terme devra être
démontrée par un test de Johansen ou une approche équivalente avant d'envisager
un VECM. Le VECM ne devra donc être estimé que si une cointégration réelle est
mise en évidence.

Quatrièmement, les rendements présentent des queues épaisses, des observations
extrêmes, un regroupement visuel de volatilité et une autocorrélation des
rendements au carré. Ces éléments rendent pertinente une future analyse de
l'hétéroscédasticité conditionnelle. Cependant, conformément à la démarche du
cours, nous devrons d'abord estimer correctement le modèle de moyenne, récupérer
ses résidus, puis appliquer le test ARCH-LM. Un modèle GARCH ne sera retenu
que si les diagnostics justifient une variance conditionnelle dynamique.

Cinquièmement, la décomposition STL avec une période de cinq séances et les
statistiques par jour de semaine constituent uniquement une exploration. Elles
ne suffisent pas à démontrer une saisonnalité stable. Nous ne retenons donc pas
automatiquement un SARIMA. Une composante saisonnière devra être réellement
justifiée avant d'introduire des ordres saisonniers.

Enfin, la période de test finale reste séparée de toutes ces décisions. Les
choix de transformations, d'ordres et d'hyperparamètres devront être réalisés
à partir de la période d'entraînement, avec validation temporelle lorsque cela
est nécessaire. Le test final ne sera utilisé qu'ultérieurement pour comparer
les performances hors échantillon des modèles retenus.

En résumé, la Phase 2 nous conduit aux hypothèses de travail suivantes :

- ARIMA : probablement sur le log-prix NVDA avec une différenciation d'ordre 1,
  à confirmer par l'analyse de Phase 3 ;
- VAR : log-rendements stationnaires de NVDA, AMD et SOXX ;
- cointégration : tests à réaliser sur les log-prix avant toute décision VECM ;
- GARCH : seulement après estimation du modèle de moyenne et confirmation par
  ARCH-LM ;
- SARIMA : uniquement si une saisonnalité suffisamment convaincante est mise
  en évidence.

Ces choix restent donc des orientations statistiques fondées sur l'EDA et les
tests de stationnarité, et non encore des conclusions définitives sur les
meilleurs modèles.