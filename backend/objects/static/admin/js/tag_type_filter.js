/* Динамічна фільтрація тегів за типом об'єкта у формі CulturalObject.
   Початковий список віддає сервер (formfield_for_manytomany); при зміні
   object_type довантажуємо теги відповідного tag_type з API і перебудовуємо
   ліву колонку віджета filter_horizontal. */
'use strict';
{
    const TAG_TYPE_BY_OBJECT_TYPE = {permanent: 'object', event: 'event'};

    function rebuildAvailable(tags) {
        const from = document.getElementById('id_tags_from');
        const to = document.getElementById('id_tags_to');
        if (!from || !to) {
            return;
        }
        const chosen = new Set(Array.from(to.options, o => o.value));
        from.innerHTML = '';
        for (const tag of tags) {
            if (!chosen.has(String(tag.id))) {
                from.add(new Option(tag.name, tag.id));
            }
        }
        // Синхронізуємо кеш django SelectBox, інакше пошук-фільтр віджета
        // працюватиме зі старим списком.
        if (window.SelectBox && window.SelectBox.cache['id_tags_from']) {
            window.SelectBox.cache['id_tags_from'] = Array.from(
                from.options, o => ({value: o.value, text: o.text, displayed: 1})
            );
        }
    }

    function syncTagsWithType() {
        const typeSelect = document.getElementById('id_object_type');
        const tagType = typeSelect && TAG_TYPE_BY_OBJECT_TYPE[typeSelect.value];
        if (!tagType) {
            return;
        }
        fetch(`/api/tags/?tag_type=${tagType}`)
            .then(r => r.json())
            .then(data => rebuildAvailable(data.results || data))
            .catch(() => {});
    }

    // 'load', а не DOMContentLoaded: SelectFilter2 має встигнути створити
    // елементи id_tags_from / id_tags_to.
    window.addEventListener('load', () => {
        const typeSelect = document.getElementById('id_object_type');
        if (!typeSelect) {
            return;
        }
        typeSelect.addEventListener('change', syncTagsWithType);
        syncTagsWithType(); // початкова синхронізація (add-форма отримує всі теги)
    });
}
