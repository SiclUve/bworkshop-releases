# Bworklingo : code source

Traducteur instantané **FR / EN / ES / PT** en overlay pour **Dofus** (Unity & Rétro), publié sur [bworkshop.app/apps/bworklingo/](https://bworkshop.app/apps/bworklingo/).

Il traduit les messages du jeu tout en protégeant les noms officiels (donjons, monstres, quêtes, items), les commandes de chat (`/b`, `/r`, `/g`, `/w`), les liens entre crochets `[...]` et l'argot communautaire.

> **Tu préfères ne rien installer ?**  
> Si tu n'as pas confiance dans le téléchargement ou l'exécution du programme Windows (`.exe`), nous te recommandons simplement d'utiliser la **version Web / Overlay directement dans ton navigateur** sur [bworkshop.app/apps/bworklingo/](https://bworkshop.app/apps/bworklingo/) (aucune installation sur ton PC).

## Ce qu'il ne fait pas

- Il ne lit pas la mémoire du jeu, n'injecte rien et ne modifie aucun fichier Dofus.
- Il n'envoie aucun clic ni aucune frappe clavier automatique dans le jeu (tu copies/colles toi-même via le presse-papiers).
- L'application Windows (`src-tauri/`) enregistre uniquement le raccourci global `Alt+T` pour afficher ou masquer la fenêtre par-dessus le jeu.
- Aucune clé API ni secret privé n'est inclus dans ce dépôt (`.env` exclu ; la traduction fonctionne sans clé via le lexique local + endpoint public GTX, et la variable `GEMINI_API_KEY` dans `.env.example` est facultative pour un serveur local).

## Les fichiers

- `src/` : interface React / TypeScript, dictionnaires et moteur linguistique Dofus (`src/utils/translator/`).
- `public/assets/` : lexique communautaire et encyclopédie multilingue JSON.
- `src-tauri/` : enveloppe bureau Windows Tauri v2 (fenêtre overlay + raccourci `Alt+T`).
- `server.ts` : serveur local optionnel (dev + fallback API).
- `tests/` : tests unitaires du traducteur.

## Lancer ou compiler en local

```bash
npm install
npm run dev
```

Pour générer l'exécutable Windows (`.exe`, nécessite Node.js + Rust / Tauri CLI) :

```bash
npm run tauri:build
```
