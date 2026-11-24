# Harebourg Overlay : code source

Overlay gratuit pour le combat contre le Comte Harebourg (Frigost III, Dofus 3), publié sur [bworkshop.app](https://bworkshop.app).

Tu lui donnes ta confusion (ou la ligne du chat copiée) ou ta tranche de PV. Il dessine par-dessus le jeu la case que tu vises et la case où le sort atterrit vraiment, avec un avertissement si c'est un mur, un trou ou sans ligne de vue.

## Ce qu'il ne fait pas

- Il ne clique jamais et n'envoie aucune touche au jeu.
- Il ne lit pas la mémoire du jeu, n'injecte rien et ne touche pas au réseau.
- Il lit seulement la position de la souris, le presse-papiers quand tu copies une ligne de confusion, et une capture d'écran pour caler la grille.
- La capture n'est pas prise en continu : seulement au lancement si un combat est ouvert, quand tu te places (F6) ou quand tu cliques sur « Calibrer ». Elle est analysée sur ton ordinateur et jamais enregistrée ni envoyée.

## Les fichiers

- `overlay.py` : l'application (PyQt6).
- `core.py` : la carte de la salle et les règles de la confusion.
- `autocal.py` : calage automatique de la grille sur la capture.
- `view.py`, `dial.py`, `theme.py` : l'affichage.
- `i18n.py` : français et anglais. `safety.py` : réglages à l'épreuve des fichiers abîmés. `diagnostic.py` : `--diagnose`.
- `installer.iss`, `build_exe.bat`, `build_installer.bat`, `version_info.txt` : construire l'exe et l'installateur (français / anglais).
- `test_*.py`, `audit_songes.py` : les tests. `AUDIT.md` : l'audit. `README.en.md` : the English guide.

## Nouveautés de la 0.3.0

- Mode Songes (grille libre qui ne change jamais de taille) et case « Calage automatique » à décocher.
- Programme et installateur en français et en anglais.
- Réglages plus robustes, une seule instance, journal limité, `--diagnose` et `--selftest`.

## Lancer depuis le code

- Windows : `lancer.bat` (il faut Python 3).
- Mac / Linux : `sh lancer.sh`.

Le jeu doit être en fenêtre ou en fenêtre sans bordure.

## Licence

Le code est sous licence MIT (voir `LICENSE`). Dofus et le Comte Harebourg appartiennent à Ankama.
