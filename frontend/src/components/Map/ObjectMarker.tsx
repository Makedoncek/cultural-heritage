import {Marker, Popup} from 'react-leaflet';
import {useNavigate} from 'react-router';
import type {CulturalObject} from '../../types';

interface ObjectMarkerProps {
    object: CulturalObject;
}

export default function ObjectMarker({object}: ObjectMarkerProps) {
    const navigate = useNavigate();

    return (
        <Marker position={[parseFloat(object.latitude), parseFloat(object.longitude)]}>
            <Popup>
                <h3 className="font-bold text-sm mb-1">{object.title}</h3>
                {object.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                        {object.tags.map(tag => (
                            <span
                                key={tag.id}
                                className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-amber-100 text-amber-800 rounded text-xs"
                            >
                                {tag.icon} {tag.name}
                            </span>
                        ))}
                    </div>
                )}
                <button
                    onClick={() => navigate(`/objects/${object.id}`)}
                    className="text-xs text-blue-600 hover:text-blue-800 underline cursor-pointer"
                >
                    Детальніше
                </button>
            </Popup>
        </Marker>
    );
}
