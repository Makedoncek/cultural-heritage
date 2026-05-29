import {useState} from 'react';
import {Link} from 'react-router';
import toast from 'react-hot-toast';
import {AxiosError} from 'axios';
import {useTranslation} from 'react-i18next';
import {translationsService} from '../../services/translations.service';
import {usePaginatedList} from '../../hooks/usePaginatedList';
import LoadMoreButton from '../Common/LoadMoreButton';
import type {MyTranslation, TranslationStatus} from '../../types/translations';

const LANG_LABEL: Record<string, string> = {uk: 'UA', en: 'EN', pl: 'PL', de: 'DE'};
const LANG_TO_ISO: Record<string, string> = {uk: 'ua', en: 'gb', pl: 'pl', de: 'de'};

const KIND_CLS: Record<string, string> = {
    object: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border border-blue-200 dark:border-blue-800',
    route: 'bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300 border border-teal-200 dark:border-teal-800',
};

const STATUS_CLS: Record<TranslationStatus, string> = {
    pending: 'bg-amber-500 text-white dark:bg-amber-500 dark:text-stone-900',
    approved: 'bg-green-600 text-white dark:bg-green-500 dark:text-stone-900',
    rejected: 'bg-red-600 text-white dark:bg-red-500 dark:text-white',
    archived: 'bg-stone-500 text-white dark:bg-stone-600 dark:text-white',
};

const STATUS_ICON: Record<TranslationStatus, string> = {
    pending: '⏳', approved: '✓', rejected: '✕', archived: '📦',
};

interface Props {
    status?: string;
}

export default function MyTranslationsTab({status}: Readonly<Props>) {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const {items, setItems, count: totalCount, nextUrl, loading, loadingMore, loadMore, error} = usePaginatedList<MyTranslation>({
        initialFetch: () => translationsService.listMine(status ? {status} : undefined),
        fetchByUrl: (url) => translationsService.listMineByUrl(url),
        onError: () => toast.error(t('common.loadMoreError')),
        deps: [status],
    });

    const [editingKey, setEditingKey] = useState<string | null>(null);
    const [editTitle, setEditTitle] = useState('');
    const [editDescription, setEditDescription] = useState('');
    const [busy, setBusy] = useState(false);

    const keyOf = (tr: MyTranslation) => `${tr.kind}-${tr.id}`;

    const errText = (e: unknown, fallback: string) =>
        ((e as AxiosError)?.response?.data as {detail?: string} | undefined)?.detail ?? fallback;

    const startEdit = (tr: MyTranslation) => {
        setEditingKey(keyOf(tr));
        setEditTitle(tr.title);
        setEditDescription('');
    };

    const saveEdit = async (tr: MyTranslation) => {
        if (!editTitle.trim()) {
            toast.error(t('translations.errorTitleRequired'));
            return;
        }
        setBusy(true);
        try {
            await translationsService.edit(tr.kind, tr.id, {title: editTitle.trim(), description: editDescription.trim()});
            setItems(prev => prev.map(x => keyOf(x) === keyOf(tr)
                ? {...x, title: editTitle.trim(), status: 'pending'} : x));
            setEditingKey(null);
            toast.success(t('contributions.editTranslationSuccess'));
        } catch (e) {
            toast.error(errText(e, t('contributions.editTranslationError')));
        } finally {
            setBusy(false);
        }
    };

    const handleArchive = async (tr: MyTranslation) => {
        if (!confirm(t('contributions.archiveTranslationConfirm'))) return;
        setBusy(true);
        try {
            await translationsService.archive(tr.kind, tr.id);
            setItems(prev => prev.map(x => keyOf(x) === keyOf(tr) ? {...x, status: 'archived'} : x));
            toast.success(t('contributions.archiveSuccess'));
        } catch (e) {
            toast.error(errText(e, t('contributions.archiveError')));
        } finally {
            setBusy(false);
        }
    };

    const handleRestore = async (tr: MyTranslation) => {
        setBusy(true);
        try {
            await translationsService.restore(tr.kind, tr.id);
            setItems(prev => prev.map(x => keyOf(x) === keyOf(tr) ? {...x, status: 'pending'} : x));
            toast.success(t('contributions.restoreSuccess'));
        } catch (e) {
            toast.error(errText(e, t('contributions.restoreError')));
        } finally {
            setBusy(false);
        }
    };

    const handleDelete = async (tr: MyTranslation) => {
        if (!confirm(t('contributions.deleteTranslationConfirm'))) return;
        setBusy(true);
        try {
            await translationsService.remove(tr.kind, tr.id);
            setItems(prev => prev.filter(x => keyOf(x) !== keyOf(tr)));
            toast.success(t('contributions.deleteTranslationSuccess'));
        } catch (e) {
            toast.error(errText(e, t('contributions.deleteTranslationError')));
        } finally {
            setBusy(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
            </div>
        );
    }
    if (error && items.length === 0) {
        return <p className="text-red-600 text-center py-6">{t('myPhotos.loadError')}</p>;
    }
    if (items.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500 dark:text-stone-400 mb-4">{t('contributions.translationsEmpty')}</p>
                <Link to="/" className="text-amber-600 dark:text-amber-400 hover:underline">
                    {t('myPhotos.goToMap')}
                </Link>
            </div>
        );
    }

    return (
        <>
            <div className="space-y-2">
                {items.map(tr => {
                    const isEditing = editingKey === keyOf(tr);
                    return (
                        <div
                            key={keyOf(tr)}
                            className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3"
                        >
                            <div className="flex items-center justify-between gap-2 flex-wrap">
                                <div className="flex items-center gap-2 min-w-0">
                                    <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${KIND_CLS[tr.kind] ?? KIND_CLS.object}`}>
                                        {tr.kind === 'route' ? t('contributions.kindRoute') : t('contributions.kindObject')}
                                    </span>
                                    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 font-semibold">
                                        <img
                                            src={`https://flagcdn.com/20x15/${LANG_TO_ISO[tr.language] ?? 'ua'}.png`}
                                            alt=""
                                            width={16}
                                            height={12}
                                            className="rounded-[2px]"
                                        />
                                        {LANG_LABEL[tr.language] ?? tr.language}
                                    </span>
                                    <Link
                                        to={tr.target_url}
                                        className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300 truncate"
                                    >
                                        {tr.target_title}
                                    </Link>
                                </div>
                                <span className={`inline-flex items-center gap-1 px-3 py-1 text-sm rounded-full font-semibold shrink-0 ${STATUS_CLS[tr.status]}`}>
                                    {STATUS_ICON[tr.status]}
                                    {t(`contributions.translationStatus.${tr.status}`)}
                                </span>
                            </div>

                            {isEditing ? (
                                <div className="mt-2 space-y-2">
                                    <input
                                        type="text"
                                        value={editTitle}
                                        onChange={e => setEditTitle(e.target.value)}
                                        maxLength={200}
                                        placeholder={t('translations.fieldTitle')}
                                        className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-stone-600 rounded-lg bg-white dark:bg-stone-800 text-gray-900 dark:text-stone-100"
                                    />
                                    <textarea
                                        value={editDescription}
                                        onChange={e => setEditDescription(e.target.value)}
                                        rows={3}
                                        placeholder={t('translations.fieldDescription')}
                                        className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-stone-600 rounded-lg bg-white dark:bg-stone-800 text-gray-900 dark:text-stone-100 resize-y"
                                    />
                                    <div className="flex gap-2 justify-end">
                                        <button
                                            type="button"
                                            onClick={() => setEditingKey(null)}
                                            disabled={busy}
                                            className="px-3 py-1 text-sm border border-gray-300 dark:border-stone-600 text-gray-700 dark:text-stone-200 rounded-lg cursor-pointer disabled:opacity-50"
                                        >
                                            {t('form.cancel')}
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => saveEdit(tr)}
                                            disabled={busy}
                                            className="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-400 text-white rounded-lg cursor-pointer disabled:opacity-50"
                                        >
                                            {t('contributions.saveAndResubmit')}
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <p className="text-sm text-gray-700 dark:text-stone-300 mt-2 truncate">
                                    {tr.title}
                                </p>
                            )}

                            {tr.status === 'rejected' && tr.reviewer_note && (
                                <p className="text-xs text-red-700 dark:text-red-300 mt-1">
                                    {t('contributions.reviewerNote')}: {tr.reviewer_note}
                                </p>
                            )}

                            {!isEditing && (
                                <div className="flex items-center justify-between gap-2 mt-2 flex-wrap">
                                    <p className="text-xs text-gray-400 dark:text-stone-500">
                                        {new Date(tr.created_at).toLocaleDateString(dateLocale)}
                                    </p>
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {tr.status === 'archived' ? (
                                            <>
                                                <button
                                                    type="button"
                                                    onClick={() => handleRestore(tr)}
                                                    disabled={busy}
                                                    className="inline-flex items-center gap-1 px-3 py-1 text-sm rounded-full font-semibold bg-green-600 hover:bg-green-700 text-white cursor-pointer disabled:opacity-50"
                                                >
                                                    ↩ {t('contributions.restore')}
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => handleDelete(tr)}
                                                    disabled={busy}
                                                    className="inline-flex items-center gap-1 px-3 py-1 text-sm rounded-full font-semibold bg-red-600 hover:bg-red-700 text-white cursor-pointer disabled:opacity-50"
                                                >
                                                    🗑 {t('contributions.deletePermanently')}
                                                </button>
                                            </>
                                        ) : (
                                            <>
                                                <button
                                                    type="button"
                                                    onClick={() => startEdit(tr)}
                                                    disabled={busy}
                                                    className="inline-flex items-center gap-1 px-3 py-1 text-sm rounded-full font-semibold bg-blue-600 hover:bg-blue-700 text-white cursor-pointer disabled:opacity-50"
                                                >
                                                    ✏ {t('contributions.editTranslation')}
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => handleArchive(tr)}
                                                    disabled={busy}
                                                    className="inline-flex items-center gap-1 px-3 py-1 text-sm rounded-full font-semibold bg-stone-200 hover:bg-stone-300 dark:bg-stone-700 dark:hover:bg-stone-600 text-stone-700 dark:text-stone-200 cursor-pointer disabled:opacity-50"
                                                >
                                                    📦 {t('contributions.archive')}
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
            <LoadMoreButton
                show={!!nextUrl}
                loading={loadingMore}
                shown={items.length}
                total={totalCount}
                onClick={loadMore}
            />
        </>
    );
}
