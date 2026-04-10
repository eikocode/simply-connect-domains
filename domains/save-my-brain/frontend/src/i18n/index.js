/**
 * i18n — Lightweight translation hook.
 * Supports EN, ZH-TW, JA.
 */

import { useState, useCallback } from "react";
import en from "./en.json";
import zhTw from "./zh-tw.json";
import ja from "./ja.json";

const LOCALES = { en, "zh-tw": zhTw, ja };
const LANG_KEY = "smb_lang";

function getStoredLang() {
  return localStorage.getItem(LANG_KEY) || "en";
}

export function useTranslation() {
  const [lang, setLangState] = useState(getStoredLang);

  const setLang = useCallback((newLang) => {
    localStorage.setItem(LANG_KEY, newLang);
    setLangState(newLang);
  }, []);

  const t = useCallback(
    (key) => {
      const strings = LOCALES[lang] || LOCALES.en;
      const keys = key.split(".");
      let val = strings;
      for (const k of keys) {
        val = val?.[k];
        if (val === undefined) break;
      }
      // Fallback to English
      if (val === undefined) {
        val = LOCALES.en;
        for (const k of keys) {
          val = val?.[k];
          if (val === undefined) break;
        }
      }
      return val ?? key;
    },
    [lang]
  );

  return { t, lang, setLang };
}
