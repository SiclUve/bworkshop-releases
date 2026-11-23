import React, { useState, useRef } from 'react';
import { BookOpen } from 'lucide-react';
import { DofusEntry, TranslationRecord, DofusLanguage } from '../types/dofus';
import {
  translateUniversally,
  translateNeuralDofusClient,
  assessMessageIntelligibility
} from '../utils/universalTranslator';
import { detectDofusTerms } from '../data/dofusDictionary';

const LANGUAGES: { code: DofusLanguage; label: string; name: string }[] = [
  { code: 'fr', label: 'FR', name: 'Français' },
  { code: 'en', label: 'EN', name: 'English' },
  { code: 'es', label: 'ES', name: 'Español' },
  { code: 'pt', label: 'PT', name: 'Português' }
];

const SOURCE_LANGUAGES: { code: DofusLanguage | 'auto'; label: string; name: string }[] = [
  { code: 'auto', label: 'AUTO', name: 'Auto-détection' },
  ...LANGUAGES
];

const UI_TEXT: Record<
  DofusLanguage,
  {
    lexicon: string;
    lexiconTitle: string;
    from: string;
    to: string;
    swapTitle: string;
    inputPlaceholder: string;
    clearTitle: string;
  privacyNote: string;
    translate: string;
    translating: string;
    autoTitle: string;
    outputLabel: string;
    outputPlaceholder: string;
    copy: string;
    copied: string;
    copyTitle: string;
    toastCopied: string;
    toastTranslatedCopied: string;
    toastClipboardRestricted: string;
    closeTitle: string;
    lexiconOn: string;
    lexiconOff: string;
    lexiconOnTitle: string;
    lexiconOffTitle: string;
  }
> = {
  fr: {
    lexicon: 'Lexique',
    lexiconTitle: 'Ouvrir le lexique du jeu (19 030+ termes)',
    from: 'De :',
    to: 'Vers :',
    swapTitle: 'Inverser le sens',
    inputPlaceholder: 'Écrivez ou collez votre texte ici...',
    clearTitle: 'Effacer',
  privacyNote: 'Traduction via service en ligne (aucune donnée conservée)',
    translate: 'Traduire',
    translating: 'Traduction...',
    autoTitle: 'Auto-copie : copie automatiquement la traduction dans le presse-papier',
    outputLabel: 'Traduction',
    outputPlaceholder: 'La traduction apparaîtra ici et sera copiée automatiquement dans votre presse-papier...',
    copy: 'Copier',
    copied: 'Copié',
    copyTitle: 'Copier le texte traduit',
    toastCopied: 'Copié dans le presse-papier !',
    toastTranslatedCopied: 'Traduit & copié — Ctrl+V dans Dofus',
    toastClipboardRestricted: 'Presse-papier restreint. Cliquez sur Copier manuellement.',
    closeTitle: 'Fermer',
    lexiconOn: 'Lexique : ON',
    lexiconOff: 'Lexique : OFF',
    lexiconOnTitle: 'Lexique Dofus activé — protège les noms et abréviations du jeu. Cliquer pour traduire en discussion libre (small talk).',
    lexiconOffTitle: 'Lexique Dofus désactivé — mode discussion libre (small talk). Cliquer pour réactiver le lexique du jeu.'
  },
  en: {
    lexicon: 'Lexicon',
    lexiconTitle: 'Open the game lexicon (19,030+ terms)',
    from: 'From :',
    to: 'To :',
    swapTitle: 'Swap languages',
    inputPlaceholder: 'Type or paste your text here...',
    clearTitle: 'Clear',
  privacyNote: 'Translated via online service (no data stored)',
    translate: 'Translate',
    translating: 'Translating...',
    autoTitle: 'Auto-copy: automatically copies the translation to your clipboard',
    outputLabel: 'Translation',
    outputPlaceholder: 'The translation will appear here and will be automatically copied to your clipboard...',
    copy: 'Copy',
    copied: 'Copied',
    copyTitle: 'Copy translated text',
    toastCopied: 'Copied to clipboard!',
    toastTranslatedCopied: 'Translated & copied — Ctrl+V in Dofus',
    toastClipboardRestricted: 'Clipboard restricted. Click Copy manually.',
    closeTitle: 'Close',
    lexiconOn: 'Lexicon : ON',
    lexiconOff: 'Lexicon : OFF',
    lexiconOnTitle: 'Game lexicon ON — protects Dofus terms and slang. Click for casual small-talk mode.',
    lexiconOffTitle: 'Game lexicon OFF — casual small-talk mode. Click to re-enable game terminology.'
  },
  es: {
    lexicon: 'Léxico',
    lexiconTitle: 'Abrir el léxico del juego (19 030+ términos)',
    from: 'De :',
    to: 'A :',
    swapTitle: 'Invertir idiomas',
    inputPlaceholder: 'Escribe o pega tu texto aquí...',
    clearTitle: 'Borrar',
  privacyNote: 'Traducido mediante servicio en línea (no se almacenan datos)',
    translate: 'Traducir',
    translating: 'Traduciendo...',
    autoTitle: 'Auto-copia: copia automáticamente la traducción al portapapeles',
    outputLabel: 'Traducción',
    outputPlaceholder: 'La traducción aparecerá aquí y se copiará automáticamente en tu portapapeles...',
    copy: 'Copiar',
    copied: 'Copiado',
    copyTitle: 'Copiar texto traducido',
    toastCopied: '¡Copiado al portapapeles!',
    toastTranslatedCopied: 'Traducido y copiado — Ctrl+V en Dofus',
    toastClipboardRestricted: 'Portapapeles restringido. Haz clic en Copiar manualmente.',
    closeTitle: 'Cerrar',
    lexiconOn: 'Léxico : ON',
    lexiconOff: 'Léxico : OFF',
    lexiconOnTitle: 'Léxico del juego ACTIVADO — protege términos y jerga. Clic para charla libre.',
    lexiconOffTitle: 'Léxico del juego DESACTIVADO — modo charla libre. Clic para reactivar el léxico.'
  },
  pt: {
    lexicon: 'Léxico',
    lexiconTitle: 'Abrir o léxico do jogo (19 030+ termos)',
    from: 'De :',
    to: 'Para :',
    swapTitle: 'Inverter idiomas',
    inputPlaceholder: 'Digite ou cole seu texto aqui...',
    clearTitle: 'Limpar',
  privacyNote: 'Traduzido via serviço online (nenhum dado armazenado)',
    translate: 'Traduzir',
    translating: 'Traduzindo...',
    autoTitle: 'Auto-cópia: copia automaticamente a tradução para a área de transferência',
    outputLabel: 'Tradução',
    outputPlaceholder: 'A tradução aparecerá aqui e será copiada automaticamente para a sua área de transferência...',
    copy: 'Copiar',
    copied: 'Copiado',
    copyTitle: 'Copiar texto traduzido',
    toastCopied: 'Copiado para a área de transferência!',
    toastTranslatedCopied: 'Traduzido e copiado — Ctrl+V no Dofus',
    toastClipboardRestricted: 'Área de transferência restrita. Clique em Copiar manualmente.',
    closeTitle: 'Fechar',
    lexiconOn: 'Léxico : ON',
    lexiconOff: 'Léxico : OFF',
    lexiconOnTitle: 'Léxico do jogo ATIVADO — protege termos e gírias. Clique para conversa livre.',
    lexiconOffTitle: 'Léxico do jogo DESATIVADO — modo conversa livre. Clique para reativar o léxico.'
  }
};

interface OverlayWidgetProps {
  entries: DofusEntry[];
  onNewTranslation?: (record: TranslationRecord) => void;
  isFloating?: boolean;
  onCloseFloating?: () => void;
  onRequestPip?: () => void;
  /** Extra buttons rendered on the right of the Dofus header (minimize, close...). */
  headerRight?: React.ReactNode;
  /** Opens the game lexicon tab. */
  onOpenDictionary?: () => void;
  /** Propagates active UI language changes to parent tabs (e.g. Lexicon). */
  onUiLangChange?: (lang: DofusLanguage) => void;
  /** Marks the header as a native drag region (Tauri .exe). */
  dragRegion?: boolean;
}

export const OverlayWidget: React.FC<OverlayWidgetProps> = ({
  entries,
  onNewTranslation,
  isFloating = false,
  onCloseFloating,
  headerRight,
  onOpenDictionary,
  onUiLangChange,
  dragRegion = false
}) => {
  const [inputText, setInputText] = useState('');
  const [outputText, setOutputText] = useState('');
  const [sourceLang, setSourceLang] = useState<DofusLanguage | 'auto'>('auto');
  const [targetLang, setTargetLang] = useState<DofusLanguage>('fr');
  const [uiLang, setUiLang] = useState<DofusLanguage>('fr');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedJustNow, setCopiedJustNow] = useState(false);
  const [autoCopy, setAutoCopy] = useState(true);
  const [useLexicon, setUseLexicon] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const toastTimeoutRef = useRef<number | null>(null);

  const t = UI_TEXT[uiLang];

  const showToast = (msg: string) => {
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    setToastMessage(msg);
    toastTimeoutRef.current = window.setTimeout(() => {
      setToastMessage(null);
    }, 2500);
  };

  // Swap translation direction
  const handleSwapLanguages = () => {
    const prevSource = sourceLang;
    const prevTarget = targetLang;
    if (prevSource === 'auto') {
      setSourceLang(prevTarget);
      setTargetLang(prevTarget === 'fr' ? 'en' : 'fr');
      setUiLang(prevTarget);
      onUiLangChange?.(prevTarget);
    } else {
      setSourceLang(prevTarget);
      setTargetLang(prevSource);
      setUiLang(prevTarget);
      onUiLangChange?.(prevTarget);
    }

    if (outputText) {
      setInputText(outputText);
      setOutputText('');
    }
  };

  const handleSelectSourceLang = (lang: DofusLanguage | 'auto') => {
    if (lang !== 'auto' && lang === targetLang) {
      setTargetLang(sourceLang === 'auto' ? (lang === 'fr' ? 'en' : 'fr') : sourceLang);
    }
    setSourceLang(lang);
    if (lang !== 'auto') {
      setUiLang(lang);
      onUiLangChange?.(lang);
    }
  };

  const handleSelectTargetLang = (lang: DofusLanguage) => {
    if (sourceLang !== 'auto' && lang === sourceLang) {
      setSourceLang(targetLang);
    }
    setTargetLang(lang);
    setUiLang(lang);
    onUiLangChange?.(lang);
  };

  const copyToClipboard = async (textToCopy: string, customNotice?: string) => {
    if (!textToCopy) return;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopiedJustNow(true);
      showToast(customNotice || t.toastCopied);
      setTimeout(() => {
        setCopiedJustNow(false);
      }, 2200);
    } catch {
      showToast(t.toastClipboardRestricted);
    }
  };

  // Perform translation (Client-Side Neural Dofus Engine + game lexicon protection -> Server -> Offline fallback)
  const performTranslation = async (textToTranslate: string) => {
    const trimmed = textToTranslate.trim();
    if (!trimmed) {
      setOutputText('');
      return;
    }

    setIsLoading(true);

    const effectiveSource: DofusLanguage = sourceLang === 'auto' ? 'fr' : sourceLang;
    const localDetected = useLexicon ? detectDofusTerms(trimmed, entries, effectiveSource, targetLang) : [];

    // 1. Instant offline preview while neural engine completes (~120ms) — skipped when lexicon is OFF for small talk
    const instantTrans = useLexicon ? translateUniversally(trimmed, entries, effectiveSource, targetLang) : trimmed;
    if (useLexicon) {
      setOutputText(instantTrans);
    }

    let finalTranslation = instantTrans;
    let finalEngine: TranslationRecord['engine'] = 'offline_rules';

    try {
      // 2. Direct browser Neural Engine (CORS-enabled, works on static hosting & PiP windows)
      const clientNeural = await translateNeuralDofusClient(trimmed, entries, sourceLang, targetLang, { useLexicon });
      if (clientNeural && clientNeural.trim()) {
        finalTranslation = clientNeural;
        finalEngine = 'neural_dofus_gtx';
      }

      // 3. Smart AI Escalation ONLY when message is genuinely incomprehensible / ultra-slang (when lexicon is ON)
      //    or if neural engine returned nothing
      const intelligibility = useLexicon
        ? assessMessageIntelligibility(trimmed, sourceLang, entries, clientNeural, targetLang)
        : null;
      const shouldEscalate = !clientNeural?.trim() || Boolean(intelligibility?.isIncomprehensible);

      if (shouldEscalate) {
        const aiEndpoint = (import.meta as any).env?.VITE_BWORKSHOP_AI_URL || '/api/translate';
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 3500);
        try {
          const res = await fetch(aiEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal,
            body: JSON.stringify({
              text: trimmed,
              sourceLang,
              targetLang,
              mode: 'incomprehensible_only',
              useLexicon,
              intelligibility
            })
          });
          clearTimeout(timer);
          if (res.ok) {
            const data = await res.json();
            if (data.translatedText && (!clientNeural?.trim() || data.engine === 'ai_smart_rescue' || data.engine === 'gemini-3.8-flash')) {
              finalTranslation = data.translatedText;
              finalEngine = data.engine || 'neural_dofus_gtx';
            }
          }
        } catch {
          clearTimeout(timer);
          // Graceful fallback: keep clientNeural (GTX) or offline instantTrans
        }
      }
    } catch {
      // Offline fallback already computed in instantTrans
    } finally {
      setOutputText(finalTranslation);
      setIsLoading(false);

      if (autoCopy) {
        await copyToClipboard(finalTranslation, t.toastTranslatedCopied);
      }

      if (onNewTranslation) {
        onNewTranslation({
          id: String(Date.now()),
          originalText: trimmed,
          translatedText: finalTranslation,
          sourceLang: effectiveSource,
          targetLang,
          timestamp: Date.now(),
          engine: finalEngine,
          detectedTerms: localDetected
        });
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      performTranslation(inputText);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleClear();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const pasted = e.clipboardData.getData('text');
    if (pasted && pasted.trim()) {
      e.preventDefault();
      const el = textareaRef.current;
      const start = el?.selectionStart ?? 0;
      const end = el?.selectionEnd ?? inputText.length;
      const isReplacingAll = start === 0 && end === inputText.length;
      const nextText = !inputText || isReplacingAll
        ? pasted
        : inputText.slice(0, start) + pasted + inputText.slice(end);
      setInputText(nextText);
      requestAnimationFrame(() => {
        if (el) {
          const caret = !inputText || isReplacingAll ? pasted.length : start + pasted.length;
          el.setSelectionRange(caret, caret);
        }
      });
      setTimeout(() => performTranslation(nextText), 10);
    }
  };

  const handleClear = () => {
    setInputText('');
    setOutputText('');
    textareaRef.current?.focus();
  };

  return (
    <div
      className={`dofus-panel relative flex flex-col h-full w-full overflow-hidden select-none ${
        isFloating ? 'fixed bottom-6 right-6 z-50 w-96 h-[430px] max-w-[calc(100vw-2rem)]' : ''
      }`}
    >
      {/* Toast Notification */}
      {toastMessage && (
        <div className="pointer-events-none absolute top-9 left-1/2 -translate-x-1/2 z-30 px-2.5 py-1 bg-[#2f3a17] border border-[#7f9a2e] text-[#dff08a] text-xs font-medium rounded-[3px] shadow-lg flex items-center gap-1.5">
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Dofus 3 / Unity Window Titlebar */}
      <div
        {...(dragRegion ? { 'data-tauri-drag-region': true } : {})}
        className={`dofus-header relative h-8 shrink-0 flex items-center justify-center px-2 ${
          dragRegion ? 'cursor-move' : ''
        }`}
      >
        {/* Left quick-action icon (Lexique — the only icon kept) */}
        <div className="absolute left-1.5 top-0 bottom-0 flex items-center gap-1">
          {onOpenDictionary && (
            <button
              type="button"
              onClick={onOpenDictionary}
              className="h-6 px-1.5 rounded-[3px] bg-[#262822] border border-[#43463b] hover:border-[#7f9a2e] text-[#a9ab9c] hover:text-[#e9e7da] text-[11px] flex items-center gap-1 transition-colors cursor-pointer"
              title={t.lexiconTitle}
            >
              <BookOpen className="w-3 h-3 text-[#b8d638]" />
              <span>{t.lexicon}</span>
            </button>
          )}
        </div>

        {/* Centered Dofus Window Title */}
        <div className="flex items-center pointer-events-none">
          <span className="text-[12px] font-bold tracking-[0.12em] uppercase text-[#e9e7da]">
            BWORKLINGO
          </span>
        </div>

        {/* Right Window Controls */}
        <div className="absolute right-1.5 top-0 bottom-0 flex items-center gap-0.5">
          {headerRight}
          {isFloating && onCloseFloating && (
            <button
              type="button"
              onClick={onCloseFloating}
              className="px-1.5 py-0.5 rounded text-xs text-[#a9ab9c] hover:text-[#ff8a4c] transition-colors"
              title={t.closeTitle}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Main Translator Body */}
      <div className="flex-1 min-h-0 flex flex-col p-2.5 gap-2.5 overflow-y-auto">
        {/* Language Selector Bar (FR / EN / ES / PT + Interactive Swap Arrow) */}
        <div className="shrink-0 flex items-center justify-between gap-1.5 px-2.5 py-1.5 rounded-[3px] bg-[#1b1d18] border border-[#3d4035] text-xs">
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-[#8d8f80] font-semibold uppercase mr-0.5">{t.from}</span>
            {SOURCE_LANGUAGES.map((l) => (
              <button
                key={`src-${l.code}`}
                type="button"
                onClick={() => handleSelectSourceLang(l.code)}
                className={`px-1.5 py-0.5 rounded-[2px] font-bold text-[11px] transition-colors cursor-pointer ${
                  sourceLang === l.code
                    ? 'bg-[#b8d638] text-[#181a14] shadow-sm'
                    : 'text-[#9ea090] hover:text-[#e9e7da] hover:bg-[#2c2f27]'
                }`}
                title={`${t.from} ${l.name}`}
              >
                {l.label}
              </button>
            ))}
          </div>

          <span
            role="button"
            tabIndex={0}
            onClick={handleSwapLanguages}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleSwapLanguages();
              }
            }}
            title={`${t.swapTitle} (${sourceLang.toUpperCase()} ⇄ ${targetLang.toUpperCase()})`}
            className="px-2 py-0.5 rounded-[2px] bg-[#2a2d25] hover:bg-[#3a4224] border border-[#474a3e] hover:border-[#8da832] text-[#c8e04a] font-bold cursor-pointer select-none transition-all active:scale-95"
          >
            ⇄
          </span>

          <div className="flex items-center gap-1">
            <span className="text-[10px] text-[#8d8f80] font-semibold uppercase mr-0.5">{t.to}</span>
            {LANGUAGES.map((l) => (
              <button
                key={`tgt-${l.code}`}
                type="button"
                onClick={() => handleSelectTargetLang(l.code)}
                className={`px-1.5 py-0.5 rounded-[2px] font-bold text-[11px] transition-colors cursor-pointer ${
                  targetLang === l.code
                    ? 'bg-[#ff7a1a] text-[#181a14] shadow-sm'
                    : 'text-[#9ea090] hover:text-[#e9e7da] hover:bg-[#2c2f27]'
                }`}
                title={`${t.to} ${l.name}`}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>

        {/* Input Section (stretches when window height increases) */}
        <div className="flex-1 min-h-[84px] flex flex-col gap-1.5">
          <div className="relative flex-1 flex flex-col">
            <textarea
              ref={textareaRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              placeholder={t.inputPlaceholder}
              className="dofus-input w-full flex-1 min-h-[72px] p-2.5 pr-7 text-[13px] leading-relaxed text-[#f2f0e4] placeholder:text-[#6f7164] resize-none select-text"
            />
            {inputText && (
              <button
                type="button"
                onClick={handleClear}
                className="absolute top-1.5 right-2 text-xs text-[#7d7f72] hover:text-[#e9e7da] px-1 py-0.5 rounded transition-colors cursor-pointer"
                title={t.clearTitle}
              >
                ✕
              </button>
            )}
          </div>

          {/* Action Toolbar */}
          <div className="shrink-0 flex flex-wrap items-center justify-between gap-1.5">
            <span className="text-[9px] leading-tight text-[#6f7164] select-none">{t.privacyNote}</span>
            <div className="flex items-center gap-1.5 ml-auto">
              <button
                type="button"
                onClick={() => setUseLexicon(!useLexicon)}
                className={`px-2 py-1 rounded-[3px] text-[11px] font-semibold flex items-center gap-1 border transition-colors cursor-pointer whitespace-nowrap ${
                  useLexicon
                    ? 'bg-[#253015] border-[#7f9a2e] text-[#c8e04a]'
                    : 'bg-[#2a2118] border-[#b45309] text-[#fdba74] hover:text-[#fed7aa]'
                }`}
                title={useLexicon ? t.lexiconOnTitle : t.lexiconOffTitle}
              >
                <BookOpen className="w-3 h-3 shrink-0" />
                <span>{useLexicon ? t.lexiconOn : t.lexiconOff}</span>
              </button>

              <button
                type="button"
                onClick={() => setAutoCopy(!autoCopy)}
                className={`px-2.5 py-1 rounded-[3px] text-xs font-semibold flex items-center border transition-colors cursor-pointer ${
                  autoCopy
                    ? 'bg-[#2f3a17] border-[#7f9a2e] text-[#c8e04a]'
                    : 'bg-[#1f211b] border-[#3d4035] text-[#8d8f80] hover:text-[#d9d7c8]'
                }`}
                title={t.autoTitle}
              >
                <span className="text-[11px]">Auto</span>
              </button>

              <button
                type="button"
                disabled={isLoading || !inputText.trim()}
                onClick={() => performTranslation(inputText)}
                className="px-3.5 py-1 rounded-[3px] bg-[#b8d638] hover:bg-[#c8e448] disabled:opacity-45 text-[#181a14] font-bold text-xs flex items-center shadow-sm transition-colors cursor-pointer"
              >
                <span>{isLoading ? t.translating : t.translate}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Translation Output Box */}
        <div className="flex-1 min-h-[76px] flex flex-col gap-1">
          <div className="flex items-center justify-between text-[11px] text-[#9ea090] px-0.5">
            <span className="font-semibold uppercase tracking-wide text-[#c8e04a]">
              {t.outputLabel} ({sourceLang === 'auto' ? 'AUTO → ' : ''}{targetLang.toUpperCase()}) :
            </span>
          </div>

          <div data-no-drag className="relative flex-1 min-h-[62px] rounded-[3px] bg-[#121310] border border-[#475227] p-2.5 flex items-start cursor-text">
            {outputText ? (
              <p className="text-[13px] font-medium text-[#e9f5b8] pr-16 select-text whitespace-pre-wrap leading-relaxed">
                {outputText}
              </p>
            ) : (
              <p className="text-xs text-[#5d6052] italic select-none">
                {t.outputPlaceholder}
              </p>
            )}

            {outputText && (
              <button
                type="button"
                onClick={() => copyToClipboard(outputText)}
                className={`absolute top-2 right-2 px-2.5 py-1 rounded-[3px] text-[11px] font-semibold transition-all cursor-pointer ${
                  copiedJustNow
                    ? 'bg-[#7f9a2e] text-[#141610]'
                    : 'bg-[#262921] hover:bg-[#34382c] text-[#d9d7c8] border border-[#474a3e]'
                }`}
                title={t.copyTitle}
              >
                {copiedJustNow ? t.copied : t.copy}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
