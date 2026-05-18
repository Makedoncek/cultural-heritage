import i18n from 'i18next';
import {initReactI18next} from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import uk from './locales/uk.json';
import en from './locales/en.json';

void i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
        resources: {
            uk: {translation: uk},
            en: {translation: en},
        },
        fallbackLng: 'uk',
        supportedLngs: ['uk', 'en'],
        load: 'languageOnly',
        interpolation: {
            escapeValue: false,
        },
        detection: {
            order: ['localStorage', 'navigator'],
            lookupLocalStorage: 'culturemap_lang',
            caches: ['localStorage'],
        },
    });

export default i18n;
