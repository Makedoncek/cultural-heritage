import {useNavigate} from 'react-router';
import {objectsService} from '../services/objects.service';
import ObjectForm from '../components/Objects/ObjectForm';
import type {CulturalObjectWrite} from '../types';

export default function AddObjectPage() {
    const navigate = useNavigate();

    const handleSubmit = async (data: CulturalObjectWrite) => {
        const result = await objectsService.create(data);
        navigate(`/objects/${result.id}`);
    };

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 mb-6">Додати культурний об'єкт</h1>
                <ObjectForm onSubmit={handleSubmit} submitLabel="Додати" submittingLabel="Додавання..."/>
            </div>
        </div>
    );
}