# Phase 9E — Audit du paquet final de remise universitaire

Construction validée le **10 octobre 2026 à 19h22, heure de Tunis**
(`2026-10-10T18:22:23.944461+00:00`). Échéance : 12 octobre 2026 à 23h55.
Branche : `feature/final-submission`, working tree initial propre.
Révision Git source : `4d91b7935039afafb1e6105dff435636926b001a`.
Révision scientifique : `v0.15.0-phase9d`
(`3bd3556570af50047c671c392e18abcddce20db2`).

L'archive capture les octets du checkout source et les nouveaux fichiers 9E
de packaging/documentation avant leur commit local ; leur contenu exact est
identifié par les SHA256 individuels du manifeste. Le hash source n'est pas
présenté comme un commit contenant à lui seul ces ajouts.

## Livrable et périmètre

Archive locale : `dist/AI_Chip_Market_Intelligence_Remise_2026.zip`.
**24 496 727 octets = 24,496727 Mo décimaux = 23,361899375915527 Mio**.
**443 fichiers**, manifeste interne inclus ; 40 741 723 octets non compressés.
`dist/` est déjà ignoré par Git ; aucun changement d'exclusion n'a été nécessaire.

Le ZIP a été construit depuis un staging temporaire isolé sous `dist/`, puis
ouvert avec `zipfile` et extrait dans un autre dossier temporaire. Les deux
dossiers ont été nettoyés après comparaison des fichiers et exécution FAST.
Seuls les fichiers suivis des dossiers autorisés, les trois nouveaux fichiers
de packaging/guide/tests et les sept snapshots locaux exacts sont sélectionnés.
Les chemins scientifiques relatifs sont conservés.

| Livrable | Vérification |
| --- | --- |
| Rapport final | `report_latex/rapport_final_latex.pdf`, header/trailer PDF valides, octets identiques à la source |
| Copie racine | `RAPPORT_FINAL.pdf`, identique octet par octet au PDF LaTeX |
| PDF SHA256 | `1673e982dd7ec980ba4bf9dcd0bcb7238c325bc6442273b50d424aac0893980b` |
| Sources éditables | Tout le contenu versionné utile de `report_latex/`, TeX/BibTeX/figures/tableaux/annexes/LLM |
| Rapports historiques | `report/` conservé intégralement, sans réédition de Word/PDF/Markdown |
| Python | 13 scripts : neuf scripts scientifiques, outils FAST/FULL et packaging |
| R | Cinq fichiers, dont quatre implémentations réelles ; `01_data_eda.R` reste un placeholder |
| Notebooks | FAST : 52 cellules de code ; FULL : cinq, défaut PREFLIGHT conservé ; JSON et syntaxe Python valides |
| Données | Exactement les sept CSV demandés ; tous les SHA historiques concordent |
| Sorties | `outputs/tables/` et `outputs/figures/`, fichiers scientifiques suivis et audits/provenances |
| LLM | Les quatre documents officiels complets, autres textes importants et avertissements préservés |
| Guides et configurations | `LIVRAISON.md`, README, protocoles, dictionnaire, décisions, guides, audits, requirements et projet RStudio |

Les placeholders `.gitkeep` et `.env.example` sont exclus. Aucun environnement,
cache, secret détecté par les signatures recherchées, fichier `.env`, archive
imbriquée, auxiliaire TeX, temporaire Word ou `report_latex/_build/` n'est inclus.
Le scan cherche notamment les en-têtes de clés privées et les formats usuels
de tokens AWS/GitHub/OpenAI ; sa portée est documentée, sans prétendre à une
détection universelle de secrets arbitraires.

## Manifestes et absence de cycle

[final_submission_manifest.json](final_submission_manifest.json) enregistre
les 443 chemins, tailles et SHA256, les statuts des snapshots/PDF/notebooks/FULL,
la révision source, la date UTC, les volumes et la taille finale du ZIP.
`MANIFESTE_LIVRAISON.json` à la racine du ZIP décrit les 442 autres fichiers et
exclut sa propre empreinte. Le manifeste externe contient aussi son SHA256.
Le hash du ZIP est enregistré séparément dans
`dist/AI_Chip_Market_Intelligence_Remise_2026.zip.sha256`.

Le manifeste externe et le présent audit sont des preuves post-construction
conservées hors du ZIP ; ils ne sont pas réinjectés dans l'archive qu'ils décrivent.
Une reconstruction actualise le manifeste et la somme séparée ; le présent audit
décrit précisément la construction datée ci-dessus.

## Intégrité et extraction

| Contrôle réellement exécuté | Résultat |
| --- | --- |
| `zipfile.ZipFile.testzip()` sur le vrai ZIP | PASS, CRC de toutes les entrées |
| Inventaire et SHA256 du contenu | PASS, tailles et hashes de chaque payload ; manifeste interne hashé dans le manifeste externe |
| Chemins | PASS, relatifs, sans `..`, drive, antislash, collision de casse ni lien symbolique |
| Présence des livrables obligatoires | PASS, vrais codes Python/R, deux notebooks, PDF, sept CSV, LLM et guides |
| Exclusions et signatures de secrets | PASS sur la sélection et le contenu du ZIP |
| Extraction distincte | PASS, les 443 fichiers extraits correspondent aux bytes du staging |
| Snapshots après extraction | PASS, sept SHA historiques exacts ; aucun téléchargement de remplacement |
| FAST sur l'extraction | PASS, 52 cellules exécutées en ordre par l'exécuteur protégé |
| Provenance FAST | PASS, 305 artefacts gelés et sept snapshots |
| Arithmétique des métriques gelées | PASS, dix lignes ; aucune nouvelle prévision, aucun DM ou scoring TEST relancé |
| Extraction après FAST | PASS, tous les fichiers livrés restent identiques |
| Intégrité source avant/après | PASS, les 444 fichiers protégés préexistants sont inchangés, dont les sept snapshots locaux |

Le contrôle d'intégrité préalable portait sur 446 fichiers suivis/locaux. Les
deux seules modifications de fichiers préexistants sont `README.md` et
`docs/final_requirements_checklist.md`, explicitement autorisées. Aucune source
scientifique, sortie, réponse LLM, protocole, empreinte historique ou ancien
rapport n'a changé. Aucun modèle historique n'a été réentraîné, aucune nouvelle
donnée Yahoo téléchargée, aucune prévision Phase 7 recalculée.

Le packaging appelle directement la fonction d'exécution FAST protégée, avec
les sorties techniques hors de l'extraction : l'audit historique
`outputs/tables/phase9a_notebook_execution_audit.csv` n'est pas remplacé.
Les tests unitaires utilisent des fixtures et des copies temporaires ; ils
ne lancent pas le pipeline scientifique réel.

## Statut scientifique et limites de reproduction

La recommandation finale reste **Naive**. Les résultats défavorables LSTM/GRU,
les nuances ARIMA/DM, le rang Johansen nul, les limites Granger et la portée
variance de GARCH sont conservés.

Le runner FULL a terminé dans un **sandbox préparé**, preuve historique 9C3.
La machine entièrement vierge, l'installation autonome de toutes les dépendances
et le notebook FULL intégral demeurent **PARTIAL**. L'extraction et le FAST
réussis ici utilisent l'environnement Python déjà installé ; ils ne constituent
pas une démonstration du §8.3. Aucun FULL n'est lancé pendant 9E et aucune
identité bit-for-bit n'est promise.

Le runner FULL nécessite un checkout Git complet et le protocole pré-déclaré
dans son historique ; `.git/` est exclu du ZIP. `LIVRAISON.md` explique comment
obtenir ce checkout, restaurer les sept CSV, préparer un nouveau sandbox et
aligner la révision de la copie du notebook sur son `state.json`. Le défaut
historique `v0.13.0-phase9b` et l'absence d'injection automatique de cette révision
par `--execute-notebook` sont exposés, sans modifier le notebook livré.

La couverture personnalisée est présente. Son contrôle consiste ici à préserver
le PDF source et à vérifier sa copie, sans nouvelle compilation/rendu/pagination.
**Aucune vérification de cette couverture dans Prism n'est attestée.** Les audits
9B/9D gardent leurs paginations et SHA historiques, identifiés comme états antérieurs.
La checklist actualisée compte 30 PASS, trois PARTIAL et zéro MISSING sur 33
contrôles ; ce ne sont pas 33 clauses du PDF officiel certifiées indépendamment.

## Taille et préparation d'un partage ultérieur

Principaux volumes **non compressés** :

| Ensemble | Octets | Mo décimaux |
| --- | ---: | ---: |
| `outputs/` | 21 363 992 | 21,363992 |
| `report_latex/` | 5 436 516 | 5,436516 |
| `report/` | 5 316 940 | 5,316940 |
| `data/` | 3 995 343 | 3,995343 |
| Racine, dont la copie du PDF | 2 739 789 | 2,739789 |

Le ZIP représente environ **32 662 304 octets après base64**, hors en-têtes et
retours de ligne MIME. Pour un budget indicatif de message de 25 000 000 octets,
une pièce jointe unique risque donc d'être refusée. Le plafond réel dépend du
service utilisé ; aucun destinataire ni service mail n'a été choisi ou contacté.
Aucun livrable obligatoire n'a été supprimé pour réduire ce volume.

Solution de partage préparée, à exécuter seulement après autorisation : déposer
le ZIP complet et son fichier `.sha256` dans l'espace de partage universitaire
ou un stockage approuvé ; limiter l'accès au destinataire prévu, vérifier que
le fichier téléchargé conserve la somme, puis préparer un lien de remise et
indiquer la présence du code, du rapport et des deux notebooks. Confirmer que
ce mode répond à l'envoi prévu en section 10. Aucun espace distant, lien ou
partage n'est créé pendant cette mission ; aucun email n'est envoyé.

## Vérifications de développement et Git

- `python -m ruff check .` : **PASS**.
- `python -m pytest` : **439 passed**, quatre FutureWarning statsmodels, 35,58 s.
- `git diff --check` : **PASS** ; contrôle indexé également effectué avant commit.
- Commandes exécutées avec le Python 3.12.3 de `.venv/Scripts/python.exe`.

Le commit local demandé contient uniquement le script de packaging, ses tests,
ce guide/audit, le manifeste documentaire et les deux corrections documentaires.
Message : `feat: prepare final university submission package`.
Le ZIP, sa somme séparée, les sept CSV et les caches restent ignorés et non
committés. Aucun push, PR, merge, tag, email ou publication d'archive n'est effectué.

Pour reconstruire, depuis le checkout contenant les sept CSV locaux, ou une
extraction intacte avec manifeste interne :

```powershell
python -B python/09e_build_submission.py --run-fast
python -B python/09e_build_submission.py --verify dist/AI_Chip_Market_Intelligence_Remise_2026.zip
```

Sans packages de vérification, omettre `--run-fast` : le build standard emploie
la bibliothèque Python standard et vérifie CRC, SHA, snapshots et extraction.
Cette omission est enregistrée comme `NOT_RUN`, jamais comme un PASS FAST.
