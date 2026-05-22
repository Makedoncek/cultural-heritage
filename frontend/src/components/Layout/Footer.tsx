import {useTranslation} from 'react-i18next';

const CONTACT_EMAIL = 'culturemap.ua@gmail.com';

export default function Footer() {
    const {t} = useTranslation();
    return (
        <footer className="bg-gray-50 dark:bg-stone-900 border-t border-gray-200 dark:border-stone-700">
            <div className="max-w-7xl mx-auto px-4 py-4 sm:py-6 text-center text-xs sm:text-sm text-gray-500 dark:text-stone-400 flex flex-col sm:flex-row sm:justify-center sm:gap-3 items-center gap-1">
                <span>&copy; CultureMap Ukraine — {new Date().getFullYear()}</span>
                <span className="hidden sm:inline">·</span>
                <a
                    href={`mailto:${CONTACT_EMAIL}`}
                    className="hover:text-amber-700 dark:hover:text-amber-400 transition-colors"
                >
                    ✉ {t('footer.contact')}: {CONTACT_EMAIL}
                </a>
            </div>
        </footer>
    );
}