import {useState, useEffect} from 'react';
import {useForm} from 'react-hook-form';
import {AxiosError} from 'axios';
import {tagsService} from '../../services/tags.service';
import LocationPicker from '../Map/LocationPicker';
import type {Tag, ObjectFormData, CulturalObjectWrite} from '../../types';

interface ObjectFormProps {
    initialData?: ObjectFormData;
    onSubmit: (data: CulturalObjectWrite) => Promise<void>;
    submitLabel: string;
    submittingLabel: string;
}

const URL_PATTERN = /^https?:\/\/.+/;

const inputClass = (hasError: boolean) =>
    `w-full border rounded-lg px-3 py-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400 transition-colors ${
        hasError ? 'border-red-400' : 'border-gray-200'
    }`;

export default function ObjectForm({initialData, onSubmit, submitLabel, submittingLabel}: ObjectFormProps) {
    const [tags, setTags] = useState<Tag[]>([]);
    const [tagsLoading, setTagsLoading] = useState(true);

    const {
        register,
        handleSubmit,
        watch,
        setValue,
        setError,
        clearErrors,
        formState: {errors, isSubmitting},
    } = useForm<ObjectFormData>({
        defaultValues: initialData || {
            title: '',
            description: '',
            tags: [],
            latitude: null,
            longitude: null,
            wikipedia_url: '',
            official_website: '',
            google_maps_url: '',
        },
    });


    const selectedTags = watch('tags');
    const latitude = watch('latitude');
    const longitude = watch('longitude');

    useEffect(() => {
        tagsService.getAll()
            .then(data => setTags(data.results))
            .catch(() => {})
            .finally(() => setTagsLoading(false));
    }, []);

    const toggleTag = (tagId: number) => {
        const current = selectedTags || [];
        if (current.includes(tagId)) {
            const updated = current.filter(id => id !== tagId);
            setValue('tags', updated);
            if (updated.length === 0) setError('tags', {message: 'Оберіть хоча б один тег'});
            else clearErrors('tags');
        } else if (current.length < 5) {
            setValue('tags', [...current, tagId]);
            clearErrors('tags');
        }
    };

    const handleFormSubmit = async (data: ObjectFormData) => {
        if (!data.latitude || !data.longitude) {
            setError('latitude', {message: 'Оберіть місце на карті'});
            return;
        }
        if (!data.tags || data.tags.length === 0) {
            setError('tags', {message: 'Оберіть хоча б один тег'});
            return;
        }

        const writeData: CulturalObjectWrite = {
            title: data.title.trim(),
            description: data.description.trim(),
            latitude: parseFloat(data.latitude.toFixed(6)),
            longitude: parseFloat(data.longitude.toFixed(6)),
            tags: data.tags,
        };
        if (data.wikipedia_url.trim()) writeData.wikipedia_url = data.wikipedia_url.trim();
        if (data.official_website.trim()) writeData.official_website = data.official_website.trim();
        if (data.google_maps_url.trim()) writeData.google_maps_url = data.google_maps_url.trim();

        try {
            await onSubmit(writeData);
        } catch (err) {
            if (err instanceof AxiosError && err.response?.status === 400) {
                const serverErrors = err.response.data as Record<string, string[]>;
                for (const [field, messages] of Object.entries(serverErrors)) {
                    if (field in data) {
                        setError(field as keyof ObjectFormData, {message: messages[0]});
                    } else {
                        setError('root', {message: messages[0]});
                    }
                }
            } else {
                setError('root', {message: 'Не вдалося зберегти. Спробуйте пізніше.'});
            }
        }
    };

    return (
        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-5">

            <div>
                <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
                    Назва *
                </label>
                <input
                    id="title"
                    type="text"
                    className={inputClass(!!errors.title)}
                    {...register('title', {required: 'Це поле обов\'язкове'})}
                />
                {errors.title && <p className="text-red-600 text-sm mt-1">{errors.title.message}</p>}
            </div>

            <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                    Опис *
                </label>
                <textarea
                    id="description"
                    rows={5}
                    className={inputClass(!!errors.description)}
                    {...register('description', {required: 'Це поле обов\'язкове'})}
                />
                {errors.description && <p className="text-red-600 text-sm mt-1">{errors.description.message}</p>}
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Теги * <span className="font-normal text-gray-500">Обрано: {selectedTags?.length || 0}/5</span>
                </label>
                {tagsLoading ? (
                    <p className="text-sm text-gray-400">Завантаження тегів...</p>
                ) : (
                    <div className="flex flex-wrap gap-2">
                        {tags.map(tag => {
                            const selected = selectedTags?.includes(tag.id);
                            return (
                                <button
                                    key={tag.id}
                                    type="button"
                                    onClick={() => toggleTag(tag.id)}
                                    className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm border transition-colors cursor-pointer ${
                                        selected
                                            ? 'bg-amber-100 border-amber-400 text-amber-800'
                                            : 'bg-white border-gray-200 text-gray-600 hover:border-gray-400'
                                    }`}
                                >
                                    {tag.icon} {tag.name}
                                </button>
                            );
                        })}
                    </div>
                )}
                {errors.tags && <p className="text-red-600 text-sm mt-1">{errors.tags.message}</p>}
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Місцезнаходження *
                </label>
                <LocationPicker
                    value={latitude && longitude ? {latitude, longitude} : null}
                    onChange={(coords) => {
                        setValue('latitude', coords.latitude);
                        setValue('longitude', coords.longitude);
                        clearErrors('latitude');
                    }}
                    error={errors.latitude?.message}
                />
            </div>

            <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Посилання (необов'язково)</h3>
                <div className="space-y-3">
                    <div>
                        <label htmlFor="wikipedia_url" className="block text-sm text-gray-500 mb-1">
                            Wikipedia URL
                        </label>
                        <input
                            id="wikipedia_url"
                            type="text"
                            placeholder="https://uk.wikipedia.org/wiki/..."
                            className={inputClass(!!errors.wikipedia_url)}
                            {...register('wikipedia_url', {
                                validate: v => !v || URL_PATTERN.test(v) || 'Введіть коректне посилання (https://...)',
                            })}
                        />
                        {errors.wikipedia_url && <p className="text-red-600 text-sm mt-1">{errors.wikipedia_url.message}</p>}
                    </div>
                    <div>
                        <label htmlFor="official_website" className="block text-sm text-gray-500 mb-1">
                            Офіційний вебсайт
                        </label>
                        <input
                            id="official_website"
                            type="text"
                            placeholder="https://..."
                            className={inputClass(!!errors.official_website)}
                            {...register('official_website', {
                                validate: v => !v || URL_PATTERN.test(v) || 'Введіть коректне посилання (https://...)',
                            })}
                        />
                        {errors.official_website && <p className="text-red-600 text-sm mt-1">{errors.official_website.message}</p>}
                    </div>
                    <div>
                        <label htmlFor="google_maps_url" className="block text-sm text-gray-500 mb-1">
                            Google Maps
                        </label>
                        <input
                            id="google_maps_url"
                            type="text"
                            placeholder="https://maps.google.com/..."
                            className={inputClass(!!errors.google_maps_url)}
                            {...register('google_maps_url', {
                                validate: v => !v || URL_PATTERN.test(v) || 'Введіть коректне посилання (https://...)',
                            })}
                        />
                        {errors.google_maps_url && <p className="text-red-600 text-sm mt-1">{errors.google_maps_url.message}</p>}
                    </div>
                </div>
            </div>

            {errors.root && (
                <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                    <p className="text-red-700 text-sm text-center">{errors.root.message}</p>
                </div>
            )}

            {/* Submit */}
            <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-amber-600 text-white py-2.5 rounded-lg font-medium hover:bg-amber-700 active:bg-amber-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
                {isSubmitting ? submittingLabel : submitLabel}
            </button>
        </form>
    );
}
