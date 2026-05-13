(function () {
    function initMaps() {
        if (typeof L === 'undefined') {
            console.warn('[admin_map] Leaflet (L) not loaded — skipping');
            return;
        }
        var els = document.querySelectorAll('[data-admin-map]');
        console.log('[admin_map] containers found:', els.length);
        els.forEach(function (el) {
            if (el.dataset.initialized) return;
            el.dataset.initialized = '1';
            var lat = parseFloat(el.dataset.lat);
            var lng = parseFloat(el.dataset.lng);
            if (isNaN(lat) || isNaN(lng)) {
                console.warn('[admin_map] invalid coords on', el);
                return;
            }
            try {
                L.Icon.Default.imagePath = '/static/admin/leaflet/images/';
                var map = L.map(el).setView([lat, lng], 14);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap',
                    maxZoom: 19
                }).addTo(map);
                L.marker([lat, lng]).addTo(map);
                setTimeout(function () { map.invalidateSize(); }, 100);
            } catch (e) {
                console.error('[admin_map] init failed:', e);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMaps);
    } else {
        initMaps();
    }
    window.addEventListener('load', initMaps);
})();
