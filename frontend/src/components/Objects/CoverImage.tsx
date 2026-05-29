import type {Tag} from '../../types';

interface Props {
    coverUrl?: string | null;
    tags?: Tag[];
    className?: string;
    alt?: string;
}

export default function CoverImage({coverUrl, tags, className = '', alt = ''}: Readonly<Props>) {
    if (coverUrl) {
        return (
            <img
                src={coverUrl}
                alt={alt}
                loading="lazy"
                className={`object-cover ${className}`}
            />
        );
    }

    const icon = tags?.[0]?.icon || '📍';
    return (
        <div className={`bg-gray-100 flex items-center justify-center text-4xl ${className}`}>
            <span>{icon}</span>
        </div>
    );
}
