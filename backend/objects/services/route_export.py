"""GPX / KML / KMZ export for Route — for users to load in mobile maps / Garmin / Google Earth.

Per-stop POI data (description, tags, link to our site) is included so that target
apps display it as part of the imported route.
"""
import io
import re
import zipfile

from django.conf import settings
from gpxpy.gpx import GPX, GPXRoute, GPXRoutePoint, GPXWaypoint
import simplekml

# Strip "Координати: 50.123456, 28.123456" / "Coordinates: ..." / "lat: 50.. lon: 28.." mentions
# from the description — the coordinates are already shown separately by every GPS app.
_COORD_PATTERNS = [
    re.compile(r'(?:Координати|Coordinates|Coords|Координаты)\s*[:\-—]?[-\d.,\s°]{1,60}', re.IGNORECASE),
    re.compile(r'\(?\s*\d{1,3}\.\d{3,}\s*,\s*\d{1,3}\.\d{3,}\s*\)?', re.IGNORECASE),
]


def _clean_description(text: str) -> str:
    """Remove redundant coordinate mentions so the GPS app shows clean prose."""
    if not text:
        return ''
    for pat in _COORD_PATTERNS:
        text = pat.sub('', text)
    # Collapse the whitespace left behind by the stripped chunks.
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s{1,200}([.,;])', r'\1', text)
    return text.strip(' .,;')


def _frontend_base_url() -> str:
    """Production origin where this route can be viewed (used as fallback)."""
    return getattr(settings, 'FRONTEND_BASE_URL', '') or 'https://culturemap.ua'


def _stop_description(obj, route_title: str, base_url: str | None = None) -> str:
    """Build a short multi-line POI description: tags + truncated description + URL."""
    parts: list[str] = []
    tags = list(obj.tags.values_list('name', flat=True))
    if tags:
        parts.append(f"#{', #'.join(tags)}")
    cleaned = _clean_description(obj.description or '')
    if cleaned:
        parts.append(cleaned[:280] + ('…' if len(cleaned) > 280 else ''))
    parts.append(f"{base_url or _frontend_base_url()}/objects/{obj.id}")
    parts.append(f"— from route «{route_title}»")
    return '\n'.join(parts)


def export_route_as_gpx(route, base_url: str | None = None) -> str:
    """Emit a GPX with three parallel representations of the stops:

    - `<wpt>` per stop → OsmAnd / Garmin show as interactive POIs (tap = open info).
    - `<rte>` with `<rtept>` → navigators that support route playback follow the order.

    Apps differ in which container they prefer; including both is the broadly compatible pattern.
    """
    base = base_url or _frontend_base_url()
    gpx = GPX()
    gpx.name = route.title
    gpx.description = route.description or ''

    gpx_route = GPXRoute(name=route.title, description=route.description or '')
    gpx_route.link = f'{base}/routes/{route.pk}'
    gpx.routes.append(gpx_route)

    for stop in route.stops.select_related('cultural_object').prefetch_related('cultural_object__tags'):
        obj = stop.cultural_object
        lng, lat = float(obj.longitude), float(obj.latitude)
        name = f'{stop.order}. {obj.title}'
        desc = _stop_description(obj, route.title, base_url=base)
        link = f'{base}/objects/{obj.id}'

        # Waypoint — shows up under "Waypoints" tab in OsmAnd and as POI in Garmin.
        wpt = GPXWaypoint(latitude=lat, longitude=lng, name=name, description=desc)
        wpt.link = link
        wpt.link_text = obj.title
        wpt.symbol = 'Flag, Blue'  # standard GPX symbol — most apps render a marker
        if stop.note:
            wpt.comment = stop.note
        gpx.waypoints.append(wpt)

        # Route point — used for ordered playback / navigation.
        rtept = GPXRoutePoint(latitude=lat, longitude=lng, name=name, description=desc)
        rtept.link = link
        rtept.link_text = obj.title
        if stop.note:
            rtept.comment = stop.note
        gpx_route.points.append(rtept)
    return gpx.to_xml()


def _build_kml(route, base_url: str | None = None) -> simplekml.Kml:
    """Build a KML with markers + polyline. Photos are referenced via their
    external Cloudinary URLs — Google Earth Web only fetches external image
    URLs (not paths inside KMZ archives), and Cloudinary serves over HTTPS
    with a CDN so the load is light even on mobile.
    """
    base = base_url or _frontend_base_url()
    kml = simplekml.Kml(name=route.title)
    doc = kml.document
    doc.description = f"{route.description or ''}\n\n{base}/routes/{route.pk}"

    coords: list[tuple[float, float]] = []
    for stop in route.stops.select_related('cultural_object').prefetch_related(
        'cultural_object__tags', 'cultural_object__photos',
    ):
        obj = stop.cultural_object
        lng, lat = float(obj.longitude), float(obj.latitude)
        desc_html = _stop_description(obj, route.title, base_url=base).replace('\n', '<br/>')
        approved_photo = next(
            (p for p in obj.photos.all() if p.status == 'approved' and p.thumbnail_url),
            None,
        )
        if approved_photo:
            desc_html = f'<img src="{approved_photo.thumbnail_url}" width="320"/><br/>{desc_html}'
        pt = kml.newpoint(
            name=f'{stop.order}. {obj.title}',
            description=desc_html,
            coords=[(lng, lat)],
        )
        pt.atomauthor = obj.author.username
        coords.append((lng, lat))

    if len(coords) >= 2:
        line = kml.newlinestring(name=route.title, coords=coords)
        line.style.linestyle.width = 4
        line.style.linestyle.color = simplekml.Color.hex('d97706')  # amber
    return kml


def _unescape_description_html(kml_text: str) -> str:
    """simplekml escapes HTML inside <description> (e.g. `<img>` → `&lt;img&gt;`),
    which renders as literal text in Google Earth instead of an image. Wrap each
    description block in CDATA after un-escaping, so HTML tags render properly.
    """
    def replace(match: re.Match) -> str:
        body = match.group(1)
        # Decode the entities that simplekml introduced.
        decoded = (body
                   .replace('&lt;', '<')
                   .replace('&gt;', '>')
                   .replace('&quot;', '"')
                   .replace('&#39;', "'")
                   .replace('&amp;', '&'))
        return f'<description><![CDATA[{decoded}]]></description>'
    return re.sub(r'<description>([^<]{0,2000}?(?:&lt;|&gt;)[^<]{0,2000}?)</description>', replace, kml_text, flags=re.DOTALL)


def export_route_as_kml(route, base_url: str | None = None) -> str:
    return _unescape_description_html(_build_kml(route, base_url=base_url).kml())


def export_route_as_kmz(route, base_url: str | None = None) -> bytes:
    """KMZ — single-file compressed container with doc.kml.

    Photos are referenced via external Cloudinary URLs (not packed inside the
    archive) because Google Earth Web doesn't fetch relative-path images from
    KMZ files. With external URLs the same file works in both Web and Desktop.
    """
    kml_text = _unescape_description_html(_build_kml(route, base_url=base_url).kml()).encode('utf-8')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('doc.kml', kml_text)
    return buffer.getvalue()
