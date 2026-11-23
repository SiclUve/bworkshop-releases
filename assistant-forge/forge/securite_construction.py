"""Verrou partagé des sessions, exclusif pendant toute la construction (Windows)."""
import atexit
import ctypes
import json
import os
from pathlib import Path
import subprocess


def racine_projet():
    from forge.chemins import dossier_logiciel
    p = Path(dossier_logiciel()).resolve()
    return p.parent.parent if p.name.lower() == 'assistantforge' and p.parent.name.lower() == 'dist' else p


class VerrouUsage:
    def __init__(self, racine=None, construction=False, executable=None):
        if os.name != 'nt':
            raise RuntimeError('Protection de construction disponible sous Windows uniquement.')
        from ctypes import wintypes
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self.api.CreateFileW.restype = wintypes.HANDLE
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.CloseHandle.restype = wintypes.BOOL
        chemin = Path(executable) if executable else Path(racine or racine_projet()) / '.assistantforge_usage.lock'
        # Les sessions partagent lecture/écriture ; le constructeur refuse tout partage.
        # L'ancien exe ne participe pas au protocole : en interdire l'ouverture en lecture/exécution,
        # tout en permettant son remplacement par le constructeur (FILE_SHARE_DELETE).
        partage = 4 if executable else (0 if construction else 3)
        self.handle = self.api.CreateFileW(str(chemin), 0xC0000000, partage,
                                          None, 3 if executable else 4, 0x80, None)
        if self.handle == ctypes.c_void_p(-1).value:
            self.handle = None
            raise RuntimeError('AssistantForge ou une construction utilise déjà les fichiers, ou le verrou est inaccessible. '
                               'Ferme les sessions avant de construire ; attends la fin de la construction pour lancer.')

    def fermer(self):
        if self.handle is not None:
            self.api.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.fermer()


_SESSION = None

def proteger_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = VerrouUsage()
        atexit.register(_SESSION.fermer)


def verifier_anciennes_sessions():
    """Les anciens exécutables n'ont pas de verrou : refuser aussi leurs processus déjà actifs."""
    commande = "$ErrorActionPreference='Stop'; Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', commande],
                       capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    if r.returncode:
        raise RuntimeError('Impossible de vérifier les sessions ouvertes : construction annulée.')
    rows = json.loads(r.stdout or '[]')
    if isinstance(rows, dict):
        rows = [rows]
    for row in rows:
        if row['ProcessId'] == os.getpid():
            continue
        nom = (row.get('Name') or '').lower()
        ligne = (row.get('CommandLine') or '').lower()
        python = nom.startswith(('python', 'py.exe'))
        if nom == 'assistantforge.exe' or (python and (not ligne or any(
                x in ligne for x in ('fenetre_forge.py', 'suivi_direct.py')))):
            raise RuntimeError(f"Session potentielle encore ouverte (processus {row['ProcessId']}, {nom}). Ferme-la avant de construire.")
