"""Écriture de journaux : une ligne = une seule écriture système (pas de lignes mélangées entre deux programmes)."""

from __future__ import annotations

import os


def ajouter_ligne(chemin: str, texte: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(chemin)), exist_ok=True)
    fd = os.open(chemin, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o666)
    try:
        donnees = texte.encode("utf-8")
        if os.write(fd, donnees) != len(donnees):
            raise OSError("Écriture incomplète du journal ; fragment conservé pour diagnostic.")
    finally:
        os.close(fd)
