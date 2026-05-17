"""GPX / KML export for Route — for users to load in mobile maps / Garmin / Google Earth."""
from gpxpy.gpx import GPX, GPXRoute, GPXRoutePoint
import simplekml


def export_route_as_gpx(route) -> str:
    gpx = GPX()
    gpx_route = GPXRoute(name=route.title, description=route.description)
    gpx.routes.append(gpx_route)
    for stop in route.stops.select_related('cultural_object'):
        obj = stop.cultural_object
        gpx_route.points.append(GPXRoutePoint(
            latitude=float(obj.latitude),
            longitude=float(obj.longitude),
            name=f'{stop.order}. {obj.title}',
            description=(obj.description or '')[:200],
        ))
    return gpx.to_xml()


def export_route_as_kml(route) -> str:
    kml = simplekml.Kml(name=route.title)
    coords: list[tuple[float, float]] = []
    for stop in route.stops.select_related('cultural_object'):
        obj = stop.cultural_object
        lng, lat = float(obj.longitude), float(obj.latitude)
        kml.newpoint(
            name=f'{stop.order}. {obj.title}',
            description=(obj.description or '')[:200],
            coords=[(lng, lat)],
        )
        coords.append((lng, lat))
    if len(coords) >= 2:
        kml.newlinestring(name=route.title, coords=coords)
    return kml.kml()
