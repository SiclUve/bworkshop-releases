# Audit de Harebourg Overlay 0.3.0

## Verdict

Prêt à être essayé en jeu. La logique, le calage, la robustesse et l'installateur sont vérifiés par des tests et par des
essais sur la vraie machine. **Une seule chose n'a pas pu être vérifiée : la reconnaissance de la salle sur un combat réel
en direct** (le jeu n'affichait pas la salle pendant l'audit). Pour cela, `--diagnose` donne la réponse en 5 secondes.

## Méthode

- Tests automatiques (Qt hors écran, faux raccourcis clavier, événements simulés : jamais la vraie souris ni le vrai clavier).
- Essais sur la vraie machine : Windows 11, Dofus non lancé en administrateur, plein écran sans bordure 1920x1080, 100 % d'échelle.
- Exe construit puis lancé : `--selftest`, démarrage avec un `config.json` volontairement abîmé, mesure de charge au repos.

## Ce qui est vérifié

| Sujet | Résultat |
|---|---|
| Calculs (rotation, carte, ligne de vue) | 480 / 480 cas identiques au simulateur |
| Calage automatique | environ 2 px d'écart (≤ 1,2 px sur fausses captures) ; aucun faux positif sur le vrai bureau |
| Mode Songes | grille libre, jamais recalée seule, placement et calage à la main |
| Case « Calage automatique » | décochée : la grille ne bouge plus, bouton manuel gardé, réglage retenu |
| Français / English | aucun texte oublié, mêmes champs dans les deux langues, installateur bilingue |
| Réglages abîmés | 3000 fichiers absurdes sans erreur ; démarrage OK avec un `config.json` coupé |
| Écriture des réglages | atomique avec copie `.bak` ; dossier protégé : repli sur `%LOCALAPPDATA%` |
| Fermeture immédiate | rien n'est perdu (taille, position, calage) |
| Overlay | ne prend jamais le focus, laisse passer les clics, reste au premier plan |
| Raccourcis globaux | s'installent ; fonctionnent car le jeu n'est pas en administrateur |
| Exe | `--selftest` OK, version 0.3.0.0 identique dans le programme, l'installateur et l'exe |
| Charge au repos | 0 s de processeur sur 10 s (mesure sur le processus lanceur de l'exe) |
| Antivirus | analyse Windows Defender de l'installateur : aucune détection |

## Défauts trouvés et corrigés

- Réglages écrits non atomiquement : un arrêt en plein milieu pouvait les détruire.
- Un `config.json` abîmé ou modifié à la main pouvait empêcher le démarrage.
- Journal d'erreurs illimité (une erreur à 30 images par seconde remplissait le disque).
- Échec au démarrage silencieux : maintenant une fenêtre l'explique.
- Plusieurs instances possibles en même temps : une seule désormais.
- Les 0,5 dernières secondes de réglages étaient perdues à la fermeture.
- Un outil plein écran qui plante à l'ouverture laissait l'overlay caché.
- Fenêtre pouvant voler le focus du jeu ; presse-papiers énorme lu en entier.
- Un `lang` invalide dans les réglages faisait planter le nettoyage (trouvé par test aléatoire).

## À surveiller (non vérifié ou limité)

- **Écrans en échelle supérieure à 100 %** : testé en simulation seulement.
- **Client Dofus en anglais** : les formats de la ligne de confusion sont supposés ; « Songes » est traduit « Dreams » sans confirmation.
- **Antivirus / SmartScreen** : l'exe n'est pas signé, un avertissement à la première exécution est normal.
- **Jeu lancé en administrateur** : les raccourcis ne marcheraient plus (le diagnostic le signale).
- **Copies `github-harebourg-overlay/` et `envoi-harebourg-overlay/`** : anciennes, volontairement non touchées.
- **Confidentialité** : le programme lit le presse-papiers (lignes « Confusion… ») et capture l'écran pour le calage ; rien n'est enregistré ni envoyé.
- Tests : les vrais écouteurs pynput enchaînés plantent le banc d'essai (pile saturée) ; les tests utilisent un faux écouteur. Non reproductible dans l'application.

## Check-list au premier combat

1. Lance `HarebourgOverlay.exe --diagnose` pendant un combat : le résultat doit finir par « tout est bon pour jouer ».
2. Place-toi (F6 sur ton personnage) : le contour cyan doit longer le carrelage.
3. Copie une ligne de confusion du chat : la case jaune doit correspondre à l'atterrissage réel.
4. Si le décalage gêne : décoche « Calage automatique ».

## Audit du mode Songes (`python audit_songes.py`)

- Lancé directement en Songes : au bout de 2,6 s (la minuterie de 1,5 s est passée), aucune capture d'écran n'a été prise et la grille n'a pas bougé d'un pixel.
- 960 cas de rotation (4 tailles de case, cases négatives ou très éloignées) : la case d'atterrissage est l'inverse exact du calcul du simulateur, sans avertissement parasite.
- Survol de cases quelconques, loin de la salle du Comte : reconnues. Contrôle fin sur un cas : le losange bleu (visée) et le losange jaune « ATTERRIT ICI » sont dessinés aux pixels attendus.
- Grille complète de 720p à 4K, sans mur ni trou.
- Retour Comte <-> Songes, et Songes retenu après redémarrage.
- Non vérifié : l'aspect réel par-dessus le jeu (le test s'arrête au dessin calculé), et l'anglais « Dreams ».
