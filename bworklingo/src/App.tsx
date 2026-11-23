import React, { useState, useEffect } from 'react';
import { BookOpen } from 'lucide-react';
import { OverlayWidget } from './components/OverlayWidget';
import { PipOverlay } from './components/PipOverlay';
import { DictionaryBrowser } from './components/DictionaryBrowser';
import { ResizableFrame } from './components/ResizableFrame';
import { DofusEntry, DofusLanguage } from './types/dofus';
import { loadDofusDictionary } from './data/dofusDictionary';
import { isTauri, getTauriWindow } from './utils/platform';

export default function App() {
  const isDesktopExe = isTauri();
  const searchParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const isOverlayOnly = Boolean(searchParams?.get('overlay_only') === 'true');
  const isEmbed = Boolean(searchParams?.get('embed'));
  const rawLang = searchParams?.get('lang');
  const initialUiLang: DofusLanguage =
    rawLang === 'en' || rawLang === 'es' || rawLang === 'pt' ? rawLang : 'fr';
  const pageLang: 'fr' | 'en' = initialUiLang === 'en' ? 'en' : 'fr';
  const isEn = pageLang === 'en';

  const [activeTab, setActiveTab] = useState<'overlay' | 'dictionary'>('overlay');
  const [entries, setEntries] = useState<DofusEntry[]>([]);
  const [uiLang, setUiLang] = useState<DofusLanguage>(initialUiLang);

  useEffect(() => {
    loadDofusDictionary().then((data) => {
      if (data && data.entries) {
        setEntries(data.entries);
      }
    });
  }, []);

  const handleMinimizeTauri = async () => {
    const tauriWin = getTauriWindow();
    if (tauriWin && typeof tauriWin.minimize === 'function') {
      try {
        await tauriWin.minimize();
      } catch {
        // ignore
      }
    }
  };

  const handleCloseTauri = async () => {
    const tauriWin = getTauriWindow();
    if (tauriWin && typeof tauriWin.close === 'function') {
      try {
        await tauriWin.close();
      } catch {
        // ignore
      }
    }
  };

  // 1. NATIVE WINDOWS .EXE MODE (Tauri) OR DETACHED POPUP OVERLAY (?overlay_only=true)
  if (isDesktopExe || isOverlayOnly) {
    const hudHeaderButtons = isDesktopExe ? (
      <>
        <button
          type="button"
          onClick={handleMinimizeTauri}
          className="px-1.5 py-0.5 rounded text-xs text-[#a9ab9c] hover:text-[#e9e7da] transition-colors cursor-pointer"
          title="Réduire (Alt+T)"
        >
          —
        </button>
        <button
          type="button"
          onClick={handleCloseTauri}
          className="px-1.5 py-0.5 rounded text-xs text-[#a9ab9c] hover:text-[#ff8a4c] transition-colors cursor-pointer"
          title="Fermer"
        >
          ✕
        </button>
      </>
    ) : null;

    return (
      <ResizableFrame mode="window" minWidth={300} minHeight={240} maxWidth={2400} maxHeight={1600} className="bg-[#1b1c18]">
        <div className={activeTab === 'overlay' ? 'h-full w-full' : 'hidden'}>
          <OverlayWidget
            entries={entries}
            dragRegion
            headerRight={hudHeaderButtons}
            onOpenDictionary={() => setActiveTab('dictionary')}
            onUiLangChange={setUiLang}
          />
        </div>

        {activeTab === 'dictionary' && (
          <div className="dofus-panel h-full w-full flex flex-col overflow-hidden">
            <div data-tauri-drag-region className="dofus-header relative h-8 shrink-0 flex items-center justify-center cursor-move">
              <button
                type="button"
                onClick={() => setActiveTab('overlay')}
                className="absolute left-1.5 h-6 px-2 rounded-[3px] bg-[#262822] border border-[#43463b] hover:border-[#7f9a2e] text-[#c8e04a] text-[11px] font-semibold flex items-center gap-1 transition-colors cursor-pointer"
              >
                ← {uiLang === 'en' ? 'Back' : uiLang === 'es' ? 'Volver' : uiLang === 'pt' ? 'Voltar' : 'Retour'}
              </button>
              <div className="flex items-center gap-1.5 pointer-events-none">
                <BookOpen className="w-3.5 h-3.5 text-[#b8d638]" />
                <span className="text-[12px] font-bold tracking-[0.12em] uppercase text-[#e9e7da]">
                  {uiLang === 'en' ? 'LEXICON' : uiLang === 'es' || uiLang === 'pt' ? 'LÉXICO' : 'LEXIQUE'} ({entries.length || 19030})
                </span>
              </div>
              <div className="absolute right-1 top-0 bottom-0 flex items-center gap-0.5">{hudHeaderButtons}</div>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto p-2.5">
              <DictionaryBrowser entries={entries} uiLang={uiLang} />
            </div>
          </div>
        )}
      </ResizableFrame>
    );
  }

  // Reusable interactive Web + Overlay block (used both in ?embed=bworkshop and on the standalone web view)
  const interactiveWorkspace = (
    <div className="space-y-5">
      {/* Detachable Always-On-Top Overlay Controller */}
      <PipOverlay entries={entries} lang={pageLang} />

      {/* Mode Switcher Bar: HUD Web vs Lexique */}
      <div className="flex items-center justify-between border-b border-[#343c31] pb-3">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm text-[#eee8da]">
            {isEn ? 'Interactive Web & Overlay Tool' : 'Outil Interactif Web & Overlay'}
          </span>
          <span className="text-xs text-[#aea99a]">
            · {isEn ? 'Drag to move, pull edges or corners to resize' : 'Glissez pour déplacer, étirez les bords ou coins pour redimensionner'}
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('overlay')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-colors cursor-pointer ${
              activeTab === 'overlay'
                ? 'bg-[#d7a449] text-[#101210]'
                : 'bg-[#1b201a] border border-[#343c31] text-[#aea99a] hover:text-[#eee8da]'
            }`}
          >
            Bworklingo
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('dictionary')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-colors cursor-pointer ${
              activeTab === 'dictionary'
                ? 'bg-[#d7a449] text-[#101210]'
                : 'bg-[#1b201a] border border-[#343c31] text-[#aea99a] hover:text-[#eee8da]'
            }`}
          >
            {isEn ? `Lexicon (${entries.length || 19030})` : `Lexique (${entries.length || 19030})`}
          </button>
        </div>
      </div>

      {activeTab === 'overlay' ? (
        <div className="py-2">
          <ResizableFrame
            mode="inline"
            initialWidth={440}
            initialHeight={380}
            minWidth={300}
            minHeight={250}
            maxWidth={1100}
            maxHeight={900}
          >
            <OverlayWidget
              entries={entries}
              onOpenDictionary={() => setActiveTab('dictionary')}
              onUiLangChange={setUiLang}
            />
          </ResizableFrame>
        </div>
      ) : (
        <div className="py-2">
          <div className="dofus-panel w-full flex flex-col overflow-hidden">
            <div className="dofus-header relative h-8 shrink-0 flex items-center justify-center px-2">
              <button
                type="button"
                onClick={() => setActiveTab('overlay')}
                className="absolute left-1.5 h-6 px-2 rounded-[3px] bg-[#262822] border border-[#43463b] hover:border-[#7f9a2e] text-[#c8e04a] text-[11px] font-semibold flex items-center gap-1 transition-colors cursor-pointer"
              >
                ← {isEn ? 'Back' : 'Retour'}
              </button>
              <div className="flex items-center gap-1.5 pointer-events-none">
                <BookOpen className="w-3.5 h-3.5 text-[#b8d638]" />
                <span className="text-[12px] font-bold tracking-[0.12em] uppercase text-[#e9e7da]">
                  {isEn ? 'LEXICON' : 'LEXIQUE'} ({entries.length || 19030})
                </span>
              </div>
            </div>
            <div className="p-3">
              <DictionaryBrowser entries={entries} uiLang={uiLang} />
            </div>
          </div>
        </div>
      )}
    </div>
  );

  // 2. EMBED MODE FOR BWORKSHOP ASTRO PAGE (?embed=bworkshop)
  if (isEmbed) {
    return (
      <div className="min-h-screen bg-[#101210] text-[#eee8da] p-4 sm:p-6 font-sans">
        <div className="max-w-5xl mx-auto">{interactiveWorkspace}</div>
      </div>
    );
  }

  // 3. STANDALONE WEB VIEW (Bworkshop visual identity)
  return (
    <div className="min-h-screen bg-[#101210] text-[#eee8da] flex flex-col font-sans">
      <header className="sticky top-0 z-40 bg-[#101210]/95 backdrop-blur-md border-b border-[#343c31] px-6 py-3.5">
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded bg-[#d7a449] flex items-center justify-center font-bold text-[#101210] text-sm">
              B
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-bold text-base tracking-wide text-[#eee8da]" style={{ fontFamily: 'Georgia, serif' }}>
                Bworklingo
              </span>
              <span className="text-xs text-[#aea99a]">par Bworkshop</span>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <button
              type="button"
              onClick={() => setActiveTab('overlay')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-colors cursor-pointer ${
                activeTab === 'overlay'
                  ? 'bg-[#d7a449] text-[#101210]'
                  : 'text-[#aea99a] hover:text-[#eee8da]'
              }`}
            >
              Outil Web & Overlay
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('dictionary')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-colors cursor-pointer ${
                activeTab === 'dictionary'
                  ? 'bg-[#d7a449] text-[#101210]'
                  : 'text-[#aea99a] hover:text-[#eee8da]'
              }`}
            >
              Lexique ({entries.length || 19030})
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 md:px-6 py-6 md:py-8 space-y-6">
        <section className="space-y-2">
          <h1 className="text-2xl md:text-3xl font-bold text-[#eee8da]" style={{ fontFamily: 'Georgia, serif' }}>
            Bworklingo — Traducteur instantané FR · EN · ES · PT
          </h1>
          <p className="text-sm text-[#aea99a] leading-relaxed max-w-3xl">
            Utilisable directement dans votre navigateur ou détachable en <strong>fenêtre Overlay au premier plan</strong>. Traduction instantanée avec protection des termes du jeu et copie automatique dans le presse-papier.
          </p>
        </section>

        {interactiveWorkspace}
      </main>

      <footer className="border-t border-[#343c31] bg-[#101210] py-5 px-6 text-xs text-[#aea99a] mt-auto">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Bworklingo · Outil communautaire indépendant par Bworkshop</span>
          <span>Site non officiel, sans lien avec Ankama Games.</span>
        </div>
      </footer>
    </div>
  );
}
