# Assistant Forge : code source

Assistant de forgemagie gratuit pour Dofus 3, publié sur [bworkshop.app](https://bworkshop.app/apps/assistant-forge/).

Il lit la fenêtre de forge (stats de l'objet, reliquat, runes, historique) et te dit quelle rune passer : chances de succès critique, de succès neutre et d'échec, reliquat, coût en kamas. **C'est toi qui poses les runes.**

## Ce qu'il ne fait pas

- Il ne clique jamais et n'envoie aucune touche au jeu.
- Il ne lit pas la mémoire du jeu, n'injecte rien et ne touche pas au réseau du jeu.
- Les captures d'écran sont analysées sur ton ordinateur et ne sont jamais envoyées.
- Seule connexion internet : la liste des objets, prise sur l'API publique de DofusDB (`forge/objets_dofusdb.py`).
- Rien n'est dessiné par-dessus le jeu, et la fenêtre reste normalement visible des captures d'écran et des streams.

## Les fichiers

- `fenetre_forge.py` : l'application.
- `suivi_direct.py` : le suivi de l'écran (utilisé par l'application).
- `forge/` : le moteur : capture, lecture OCR, calcul des chances, conseil, coûts.
- `data/` : poids des runes, libellés, icônes, modèles OCR, liste des objets.

## Lancer depuis le code (Windows, Python 3.13)

1. `Installer_une_fois.bat` : installe les composants de `requirements.txt`.
2. `Lancer_assistant.bat`.

## Licences

- Le code est sous licence MIT (voir `LICENSE`).
- Les icônes et images de runes dans `data/` viennent de Dofus et restent la propriété d'Ankama.
- Modèles OCR (`data/modeles_ocr/`) : PP-OCRv5 de PaddleOCR, utilisés avec RapidOCR, sous licence Apache-2.0.
- Police Roboto Condensed (`data/fonts/`) : licence SIL OFL (voir `OFL-RobotoCondensed.txt`).
