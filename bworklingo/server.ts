import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import dotenv from 'dotenv';
import { GoogleGenAI } from '@google/genai';
import {
  translateUniversally,
  translateNeuralDofusClient,
  assessMessageIntelligibility
} from './src/utils/universalTranslator';
import { detectDofusTerms } from './src/data/dofusDictionary';
import { getAllExpandedDofusEntries, DOFUS_QUESTS_AND_BOUNTIES_ENTRIES } from './src/data/dofusQuestsAndBounties';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

app.use(express.json({ limit: '10mb' }));

// Load the 438 entries Dofus dictionary + 2,743 Official Encyclopedia entries (Quests, Dofus, Bounties, Archmonsters, Dungeons)
let dictionaryData: any = null;
try {
  const jsonPath = path.resolve(__dirname, 'public/assets/aistudio/dico_communautaire_438_08a5c870.json');
  const encPath = path.resolve(__dirname, 'public/assets/dofus_official_encyclopedia.json');
  if (fs.existsSync(jsonPath)) {
    const raw = fs.readFileSync(jsonPath, 'utf-8');
    const parsed = JSON.parse(raw);
    const officialEntries = fs.existsSync(encPath) ? (JSON.parse(fs.readFileSync(encPath, 'utf-8'))?.entries || []) : [];
    const expanded = [...getAllExpandedDofusEntries(), ...officialEntries];
    const existingMap = new Map<string, any>();
    const mergedEntries = [...(parsed.entries || [])];
    for (const e of mergedEntries) {
      if (e?.fr) existingMap.set(e.fr.toLowerCase(), e);
    }
    for (const item of expanded) {
      if (!item?.fr) continue;
      const key = item.fr.toLowerCase();
      const existing = existingMap.get(key);
      if (!existing) {
        existingMap.set(key, item);
        mergedEntries.push(item);
      } else if (key !== 'roub') {
        if (item.es && !existing.es) existing.es = item.es;
        if (item.pt && !existing.pt) existing.pt = item.pt;
        if (item.aliases_fr?.length) {
          existing.aliases_fr = Array.from(new Set([...(existing.aliases_fr || []), ...item.aliases_fr]));
        }
        if (item.aliases_en?.length) {
          existing.aliases_en = Array.from(new Set([...(existing.aliases_en || []), ...item.aliases_en]));
        }
      }
    }
    dictionaryData = {
      ...parsed,
      entries: mergedEntries
    };
  }
} catch (err) {
  console.warn('Failed to load local dictionary json on server:', err);
}

const LANG_NAMES: Record<string, string> = {
  fr: 'Français',
  en: 'Anglais',
  es: 'Espagnol',
  pt: 'Portugais',
  auto: 'Détection automatique'
};

// Translation endpoint with Smart Incomprehensible-Only Gemini Escalation + Free GTX Neural Engine
app.post('/api/translate', async (req, res) => {
  try {
    const {
      text,
      sourceLang = 'fr',
      targetLang = 'en',
      mode = 'incomprehensible_only',
      useLexicon = true
    } = req.body;

    if (!text || typeof text !== 'string' || !text.trim()) {
      return res.status(400).json({ error: 'Texte requis pour la traduction.' });
    }

    const trimmed = text.trim();
    const useGameLexicon = useLexicon !== false;
    const allEntries = (dictionaryData?.entries || DOFUS_QUESTS_AND_BOUNTIES_ENTRIES) as any[];
    const intelligibility = assessMessageIntelligibility(trimmed, sourceLang, allEntries, null, targetLang);
    const effectiveSource = sourceLang === 'auto' ? intelligibility.detectedLanguage : sourceLang;
    const detectedTerms = useGameLexicon ? findDetectedTerms(trimmed, effectiveSource, targetLang) : [];

    const apiKey = process.env.GEMINI_API_KEY;
    const hasValidKey = apiKey && apiKey !== 'MY_GEMINI_API_KEY' && apiKey.trim().length > 10;
    const shouldTryAi = hasValidKey && useGameLexicon && (mode === 'force_ai' || intelligibility.isIncomprehensible);

    // 1. Only invoke Gemini LLM when phrase is flagged as incomprehensible / ultra-slang (saving server quota)
    if (shouldTryAi) {
      try {
        const ai = new GoogleGenAI();
        const modelName = process.env.GEMINI_MODEL || 'gemini-3.8-flash';
        const srcLabel = LANG_NAMES[effectiveSource] || effectiveSource.toUpperCase();
        const tgtLabel = LANG_NAMES[targetLang] || targetLang.toUpperCase();

        const dynamicGlossary = detectedTerms.length > 0
          ? detectedTerms
              .map((t: any) => `- "${t.source}" => "${t.targetValue || t[targetLang] || t.en || t.fr}" (${t.category || 'dofus'})`)
              .join('\n')
          : '(Aucun nom propre officiel Dofus détecté — respecte le jargon PvM/PvP/FM/commerce Dofus.)';

        const systemPrompt = `Tu es le traducteur expert du MMORPG DOFUS (Dofus 3 / Unity), spécialisé dans l'argot extrême, les fautes de frappe et le langage SMS des joueurs (canaux Recrutement, Commerce, Combat, Alliance).
Règles absolues :
1. Traduis de "${srcLabel}" vers "${tgtLabel}".
2. Préserve intacts les liens [Shift+Click], les coordonnées [x,y] et les préfixes /w ou [HH:MM].
3. Respecte strictement le glossaire Dofus détecté pour ce message :
${dynamicGlossary}
4. Décrypte l'argot, les fautes phonétiques et les abréviations gaming FR/EN/ES/PT pour produire une phrase naturelle pour un joueur Dofus en ${tgtLabel}.
5. Rends UNIQUEMENT la traduction finale (aucun commentaire, aucune note).`;

        const userPrompt = `Traduis ce message de joueur Dofus vers ${tgtLabel} :\n\n${trimmed}`;

        const timeoutPromise = new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('AI timeout')), 4500)
        );

        const aiCallPromise = ai.models.generateContent({
          model: modelName,
          contents: userPrompt,
          config: {
            systemInstruction: systemPrompt,
            temperature: 0.2,
          }
        });

        const response = await Promise.race([aiCallPromise, timeoutPromise]);
        const translatedText = response.text ? response.text.trim() : trimmed;

        return res.json({
          translatedText,
          engine: 'ai_smart_rescue',
          detectedDofusTerms: detectedTerms,
          intelligibility
        });
      } catch (aiErr) {
        console.warn('Gemini smart rescue timed out or failed, falling back to GTX neural engine:', aiErr);
      }
    }

    // 2. High-performance Free Neural Dofus Engine (GTX + game lexicon protection, handles FR/EN/ES/PT)
    try {
      const neuralTrans = await performNeuralDofusTranslation(trimmed, sourceLang, targetLang, useGameLexicon);
      if (neuralTrans && neuralTrans.trim()) {
        return res.json({
          translatedText: neuralTrans,
          engine: 'neural_dofus_gtx',
          detectedDofusTerms: detectedTerms,
          intelligibility
        });
      }
    } catch (neuralErr) {
      console.warn('Neural Dofus engine failed, using universal rule engine:', neuralErr);
    }

    // 3. Robust Universal Linguistic Offline Engine (100% offline, zero latency)
    const fallback = performFallbackRuleTranslation(trimmed, effectiveSource, targetLang);
    return res.json({
      translatedText: fallback,
      engine: 'universal_offline_rules',
      detectedDofusTerms: detectedTerms,
      intelligibility,
      notice: 'Traduction instantanée via le dictionnaire et grammaire Dofus.'
    });
  } catch (err: any) {
    console.error('Translation route error:', err);
    const fallback = performFallbackRuleTranslation(req.body?.text || '', req.body?.sourceLang || 'fr', req.body?.targetLang || 'en');
    return res.json({
      translatedText: fallback,
      engine: 'universal_offline_rules',
      warning: 'Erreur serveur, lexique Dofus utilisé.'
    });
  }
});

// Endpoint to get the complete dictionary
app.get('/api/dictionary', (_req, res) => {
  if (dictionaryData) {
    res.json(dictionaryData);
  } else {
    res.status(404).json({ error: 'Dictionary not found' });
  }
});

// Helper for offline universal translation fallback
function performFallbackRuleTranslation(text: string, sourceLang: string, targetLang: string): string {
  const entries = (dictionaryData?.entries || []) as any[];
  return translateUniversally(text, entries, sourceLang as any, targetLang as any);
}

/**
 * Free Neural Dofus translation using public GTX translation engine with domain token protection.
 * Supports FR, EN, ES, and PT with full game encyclopedia protection and zero API key.
 */
async function performNeuralDofusTranslation(
  text: string,
  sourceLang: string,
  targetLang: string,
  useLexicon: boolean = true
): Promise<string> {
  if (sourceLang === targetLang) return text;
  const allEntries = (dictionaryData?.entries || DOFUS_QUESTS_AND_BOUNTIES_ENTRIES) as any[];
  const res = await translateNeuralDofusClient(text, allEntries, sourceLang as any, targetLang as any, { useLexicon });
  if (!res) throw new Error('Neural translation unavailable');
  return res;
}

function findDetectedTerms(text: string, sourceLang: string, targetLang: string = 'en') {
  const entries = (dictionaryData?.entries || []) as any[];
  return detectDofusTerms(text, entries, sourceLang as any, targetLang as any);
}

// In production, serve built frontend. In dev, Vite middleware is used.
if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(__dirname, 'dist')));
  app.get('*', (_req, res) => {
    res.sendFile(path.join(__dirname, 'dist', 'index.html'));
  });
} else {
  // Dev mode with Vite
  import('vite').then(({ createServer }) => {
    createServer({
      server: { middlewareMode: true },
      appType: 'spa',
    }).then((vite) => {
      app.use(vite.middlewares);
    });
  });
}

app.listen(PORT, () => {
  console.log(`Dofus QuickTranslate server running on http://localhost:${PORT}`);
});
