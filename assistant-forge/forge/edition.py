"""Configuration de l'édition publique d'Assistant Forge.

Les données de l'utilisateur (journaux, prix, objectif...) sont rangées dans %LOCALAPPDATA%\\AssistantForge,
jamais à côté du programme (dossier d'installation en lecture seule).
"""

from __future__ import annotations

import os
import sys

NOM_FICHIER = os.path.join("edition", "publique.txt")


def publique() -> bool:
    return True


def dossier_donnees_publique() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "AssistantForge")
