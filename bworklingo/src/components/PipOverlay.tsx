import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { BookOpen } from 'lucide-react';
import { OverlayWidget } from './OverlayWidget';
import { DictionaryBrowser } from './DictionaryBrowser';
import { DofusEntry, TranslationRecord } from '../types/dofus';

interface PipOverlayProps {
  entries: DofusEntry[];
  lang?: 'fr' | 'en';
  onNewTranslation?: (record: TranslationRecord) => void;
}

declare global {
  interface Window {
    documentPictureInPicture?: {
      requestWindow: (options?: { width?: number; height?: number }) => Promise<Window>;
      window?: Window | null;
    };
  }
}

export const PipOverlay: React.FC<PipOverlayProps> = ({
  entries,
  lang = 'fr',
  onNewTranslation
}) => {
  const [pipWindow, setPipWindow] = useState<Window | null>(null);
  const [pipTab, setPipTab] = useState<'overlay' | 'dictionary'>('overlay');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const isEn = lang === 'en';

  const getPipController = () => {
    try {
      if (window.top && window.top.documentPictureInPicture) {
        return window.top.documentPictureInPicture;
      }
    } catch {
      // Cross-origin top frame fallback
    }
    return window.documentPictureInPicture;
  };

  const openAlwaysOnTopPip = async () => {
    const pipController = getPipController();
    if (!pipController) {
      openStandaloneWindow();
      return;
    }

    try {
      if (pipWindow && !pipWindow.closed) {
        pipWindow.close();
        setPipWindow(null);
        return;
      }

      const pip = await pipController.requestWindow({
        width: 440,
        height: 390
      });

      // 1. Copy all inline <style> tags and fetch all <link rel="stylesheet"> contents directly as raw <style>
      const styleNodes = Array.from(document.querySelectorAll('style, link[rel="stylesheet"]'));
      for (const styleNode of styleNodes) {
        if (styleNode.tagName.toLowerCase() === 'link') {
          const linkEl = styleNode as HTMLLinkElement;
          const absHref = linkEl.href;
          // Add <link> with absolute URL
          const newLink = pip.document.createElement('link');
          newLink.rel = 'stylesheet';
          newLink.href = absHref;
          pip.document.head.appendChild(newLink);

          // Also fetch raw CSS text and inject as <style> so it never fails in top-level PiP
          if (absHref && !absHref.includes('fonts.googleapis.com')) {
            try {
              const res = await fetch(absHref);
              if (res.ok) {
                const cssText = await res.text();
                const rawStyle = pip.document.createElement('style');
                rawStyle.textContent = cssText;
                pip.document.head.appendChild(rawStyle);
              }
            } catch {
              // Ignore fetch error
            }
          }
        } else {
          pip.document.head.appendChild(styleNode.cloneNode(true));
        }
      }

      // 2. Also copy any runtime CSSOM rules
      try {
        const inlineCss: string[] = [];
        Array.from(document.styleSheets).forEach((sheet) => {
          try {
            Array.from(sheet.cssRules).forEach((rule) => {
              inlineCss.push(rule.cssText);
            });
          } catch {
            // Ignore cross-origin font stylesheets
          }
        });
        if (inlineCss.length > 0) {
          const inlineStyle = pip.document.createElement('style');
          inlineStyle.textContent = inlineCss.join('\n');
          pip.document.head.appendChild(inlineStyle);
        }
      } catch {
        // Ignore
      }

      pip.document.documentElement.style.backgroundColor = '#1b1c18';
      pip.document.documentElement.style.height = '100%';
      pip.document.title = 'Bworklingo — Overlay';
      pip.document.body.className = 'm-0 p-0 h-full w-full overflow-hidden bg-[#1b1c18] text-[#eee8da]';

      const container = pip.document.createElement('div');
      container.id = 'pip-overlay-root';
      container.style.height = '100vh';
      container.style.width = '100vw';
      pip.document.body.appendChild(container);

      pip.addEventListener('pagehide', () => {
        setPipWindow(null);
        setStatusMessage(isEn ? 'Overlay closed.' : 'Overlay refermé.');
        setTimeout(() => setStatusMessage(null), 3000);
      });

      setPipWindow(pip);
      setStatusMessage(
        isEn
          ? 'Always-On-Top Overlay active above your game window.'
          : 'Overlay Always-On-Top actif par-dessus votre fenêtre de jeu.'
      );
      setTimeout(() => setStatusMessage(null), 4000);
    } catch {
      openStandaloneWindow();
    }
  };

  const openStandaloneWindow = () => {
    const width = 440;
    const height = 400;
    const left = window.screen.width - width - 40;
    const top = 60;
    const baseUrl = window.location.href.split('?')[0];
    const newWin = window.open(
      `${baseUrl}?overlay_only=true`,
      'BworklingoHUD',
      `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=no,status=no,toolbar=no,menubar=no,location=no`
    );
    if (!newWin) {
      setStatusMessage(
        isEn
          ? 'Please allow pop-up windows in your browser to detach the overlay.'
          : 'Veuillez autoriser les fenêtres pop-up pour détacher l’overlay.'
      );
    }
  };

  return (
    <div className="space-y-3">
      <div className="p-4 rounded-xl border border-[#343c31] bg-[#1b201a] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-[#eee8da]">
              {isEn ? 'Mode Overlay (Always-On-Top) & Web' : 'Mode Overlay (Premier plan) & Utilisation Web'}
            </span>
            <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-[#252b22] text-[#d7a449] border border-[#343c31]">
              {isEn ? 'No install required' : 'Sans installation'}
            </span>
          </div>
          <p className="text-xs text-[#aea99a] max-w-2xl leading-relaxed">
            {isEn
              ? 'Use Bworklingo directly in the page below, or detach it as a floating Always-On-Top window that stays above your game.'
              : 'Utilisez Bworklingo directement dans la page ci-dessous, ou détachez-le en fenêtre flottante qui reste au premier plan par-dessus le jeu.'}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={openAlwaysOnTopPip}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors cursor-pointer ${
              pipWindow
                ? 'bg-[#3a2020] border border-[#7a3535] text-[#f2b8b8]'
                : 'bg-[#d7a449] hover:bg-[#e3b660] text-[#101210]'
            }`}
          >
            {pipWindow
              ? isEn
                ? 'Close Floating Overlay'
                : 'Fermer l’Overlay flottant'
              : isEn
                ? 'Detach Overlay (Always-On-Top)'
                : 'Détacher en Overlay (Premier plan)'}
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="px-3 py-2 bg-[#252b22] border border-[#343c31] text-[#eee8da] text-xs rounded-lg">
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Render via Portal inside PiP Window when detached */}
      {pipWindow &&
        pipWindow.document.getElementById('pip-overlay-root') &&
        createPortal(
          <div className="h-screen w-screen">
            {pipTab === 'overlay' ? (
              <OverlayWidget
                entries={entries}
                onNewTranslation={onNewTranslation}
                isFloating={false}
                onOpenDictionary={() => setPipTab('dictionary')}
              />
            ) : (
              <div className="dofus-panel h-full w-full flex flex-col overflow-hidden">
                <div className="dofus-header relative h-8 shrink-0 flex items-center justify-center px-2">
                  <button
                    type="button"
                    onClick={() => setPipTab('overlay')}
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
                <div className="flex-1 min-h-0 overflow-y-auto p-2.5">
                  <DictionaryBrowser entries={entries} uiLang={isEn ? 'en' : 'fr'} />
                </div>
              </div>
            )}
          </div>,
          pipWindow.document.getElementById('pip-overlay-root')!
        )}
    </div>
  );
};
