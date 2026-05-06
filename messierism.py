import warnings
warnings.filterwarnings(
    "ignore",
    message=r".*pkg_resources is deprecated.*",
    category=UserWarning,
)

import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from astroplan import Observer, moon_illumination
from astropy import units as u
from astropy.coordinates import (
    AltAz,
    EarthLocation,
    GeocentricMeanEcliptic,
    SkyCoord,
    get_body,
    get_sun,
)
from astropy.time import Time
from pyongc import ongc
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from timezonefinder import TimezoneFinder


# ─────────────────────────────────────────────────────────────────────────────
# Constantes de scoring
# ─────────────────────────────────────────────────────────────────────────────

# Sensibilidad al brillo lunar y a la contaminación luminosa por tipo de objeto.
#  - Difusos (galaxias, nebulosas, restos SN) → muy afectados por sky glow
#  - Compactos brillantes (globulares, abiertos, dobles) → resisten bien
#  - Planetarias → intermedias (pequeñas, brillo superficial moderado)
MOON_SENSITIVITY = {
    'Galaxy':                       1.5,
    'Nebula':                       1.5,
    'Reflection Nebula':            1.5,
    'HII Ionized region':           1.5,
    'Supernova remnant':            1.5,
    'Star cluster + Nebula':        1.2,
    'Planetary Nebula':             1.0,
    'Globular Cluster':             0.7,
    'Open Cluster':                 0.7,
    'Double star':                  0.5,
    'Association of stars':         0.5,
    'Object of other/unknown type': 1.0,
}

# Pesos del score (suman 100)
W_ALT = 50    # altitud máxima en la noche
W_MOON = 30   # condiciones lunares + contaminación luminosa
W_SIZE = 20   # tamaño angular

# SQM por defecto si no se pasa --sqm ni --bortle: cielo de campo medio
DEFAULT_SQM = 21.0

# Tabla de equivalencia Bortle → SQM (mag/arcsec², zenith).
# Valores típicos centrales para cada clase.
BORTLE_TO_SQM = {
    1: 21.9,   # Cielo perfecto, prístino
    2: 21.7,   # Verdaderamente oscuro, rural
    3: 21.5,   # Rural
    4: 21.0,   # Transición rural/suburbio
    5: 20.5,   # Suburbio
    6: 19.5,   # Suburbio brillante
    7: 18.5,   # Transición urbano
    8: 18.0,   # Urbano
    9: 17.5,   # Centro urbano
}


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de zona horaria
# ─────────────────────────────────────────────────────────────────────────────

def get_local_tz(latitude, longitude):
    """Resuelve la zona horaria IANA a partir de coordenadas geográficas.

    Devuelve un ZoneInfo. Si timezonefinder no encuentra zona (océano,
    coordenadas inválidas), devuelve UTC como fallback seguro.
    """
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lat=latitude, lng=longitude)
    if tz_name is None:
        return ZoneInfo("UTC")
    return ZoneInfo(tz_name)


def fmt_local_hm(astropy_time, local_tz):
    """Formatea un astropy.Time como HH:MM en la zona horaria indicada."""
    return astropy_time.to_datetime(timezone=local_tz).strftime('%H:%M')


# ─────────────────────────────────────────────────────────────────────────────
# Resolución de calidad de cielo
# ─────────────────────────────────────────────────────────────────────────────

def resolve_sky_quality(sqm_arg, bortle_arg):
    """Resuelve el SQM efectivo a partir de los argumentos del usuario.

    Precedencia:
      1. --sqm si se especifica (continuo, preferido)
      2. --bortle si se especifica (mapeo a SQM por tabla)
      3. DEFAULT_SQM si no se da nada

    Devuelve una tupla (sqm, source_label) donde source_label describe
    el origen para mostrarlo al usuario.
    """
    if sqm_arg is not None:
        return sqm_arg, f"SQM {sqm_arg:.2f} (proporcionado)"
    if bortle_arg is not None:
        bortle_clamped = max(1, min(9, int(bortle_arg)))
        sqm = BORTLE_TO_SQM[bortle_clamped]
        return sqm, f"Bortle {bortle_clamped} → SQM {sqm:.2f}"
    return DEFAULT_SQM, f"SQM {DEFAULT_SQM:.2f} (asumido, cielo de campo medio)"


def sqm_to_pollution_factor(sqm):
    """Convierte SQM a un factor de contaminación luminosa de fondo (0..1).

    SQM 21.9 (cielo perfecto) → 0.0
    SQM 17.5 (centro urbano)  → 1.0
    Lineal entre ambos extremos, recortado fuera del rango.
    """
    return max(0.0, min(1.0, (21.9 - sqm) / (21.9 - 17.5)))


# ─────────────────────────────────────────────────────────────────────────────
# Cálculo de la puntuación de observabilidad
# ─────────────────────────────────────────────────────────────────────────────

def compute_score(alt_deg, size_major, moon_sep_deg, moon_alt_deg,
                  illum, obj_type, sqm):
    """Calcula la puntuación de observabilidad (0-100) para un objeto.

    Tres componentes lunares/de cielo en moon_score:

      1. Sky glow lunar: depende de la luna sobre el horizonte y de su
         iluminación. Aplica a todo el cielo.

      2. Dispersión local lunar: cae con la distancia angular y se anula
         a partir de ~60°.

      3. Contaminación luminosa de fondo: deriva del SQM y aplica
         siempre, también con luna nueva. Es lo que distingue una noche
         en La Hiruela (Bortle 4) de una en Madrid (Bortle 8).

    Las tres componentes se ponderan por la sensibilidad del tipo de
    objeto: galaxias y nebulosas sufren todas las penalizaciones; los
    cúmulos las absorben mucho mejor.

    El tamaño angular también se modula por la luna: un objeto sensible
    grande con luna brillante deja de tener su tamaño como virtud.
    """
    # Componente altitud (0..W_ALT): factor dominante
    alt_score = (alt_deg / 90) * W_ALT

    # Componente lunar + cielo (0..W_MOON)
    sensitivity = MOON_SENSITIVITY.get(obj_type, 1.0)
    moon_above = 1.0 if moon_alt_deg > 0 else 0.0
    moon_glow_factor = illum * moon_above  # 0..1, intensidad global de luna

    # 1. Brillo difuso del cielo por luna
    sky_glow = moon_glow_factor * sensitivity * 12

    # 2. Dispersión local cerca de la luna (a < 60°)
    local_scatter = max(0.0, 1.0 - moon_sep_deg / 60.0)
    local_penalty = moon_glow_factor * local_scatter * sensitivity * 8

    # 3. Contaminación luminosa del cielo (siempre activa)
    pollution = sqm_to_pollution_factor(sqm)
    sky_pollution_penalty = pollution * sensitivity * 8

    moon_score = max(
        0.0,
        W_MOON - sky_glow - local_penalty - sky_pollution_penalty
    )

    # Componente tamaño (0..W_SIZE), modulado por luna y sensibilidad.
    sz = size_major if size_major else 0
    size_modifier = 1.0 - moon_glow_factor * (sensitivity - 1.0) * 0.4
    size_modifier = max(0.3, min(1.0, size_modifier))
    size_score = min(sz / 30.0, 1.0) * W_SIZE * size_modifier

    return alt_score + moon_score + size_score


# ─────────────────────────────────────────────────────────────────────────────
# Lógica principal
# ─────────────────────────────────────────────────────────────────────────────

def main(latitude, longitude, altitude, date, min_angle, sqm_arg, bortle_arg):
    console = Console()
    location = EarthLocation(
        lat=latitude * u.deg, lon=longitude * u.deg, height=altitude * u.m
    )

    local_tz = get_local_tz(latitude, longitude)
    sqm, sky_source = resolve_sky_quality(sqm_arg, bortle_arg)

    base_time = (
        Time(datetime.strptime(date, "%Y%m%d"), scale='utc')
        if date else Time.now()
    )
    observer = Observer(location=location)

    # Ventana de la noche astronómica del día indicado
    night_start_time = observer.twilight_evening_astronomical(
        base_time, which='next'
    )
    night_end_time = observer.twilight_morning_astronomical(
        night_start_time, which='next'
    )
    night_start_local = night_start_time.to_datetime(timezone=local_tz)

    # Iluminación lunar: aprox. constante durante la noche
    illum = float(moon_illumination(night_start_time))

    # ── Catálogo Messier ──
    visible_objects = build_messier_table_data(
        observer, location, night_start_time, night_end_time,
        min_angle, illum, local_tz, sqm
    )
    visible_objects.sort(key=lambda x: -x['score'])

    console.print(render_messier_table(visible_objects, night_start_local))

    # ── Calidad de cielo ──
    console.print(
        f"[dim italic]Calidad de cielo: {sky_source}[/]"
    )

    # ── Luna ──
    console.print(build_moon_panel(night_start_local, location, local_tz))

    # ── Planetas ──
    planet_table = build_planet_table(night_start_local, location, min_angle)
    if planet_table is not None:
        console.print(planet_table)
    else:
        console.print(
            f"[dim]Sin planetas por encima de {min_angle}° en ese momento.[/]"
        )


def build_messier_table_data(observer, location, night_start_time,
                             night_end_time, min_angle, illum, local_tz,
                             sqm):
    """Recorre el catálogo Messier y genera la lista de objetos visibles.

    Para cada objeto calcula altitud actual, altitud máxima dentro de la
    noche, hora de tránsito, distancia a la luna en el mejor momento de
    observación y puntuación.
    """
    altaz_at_start = AltAz(location=location, obstime=night_start_time)
    visible = []
    nombres_vistos = set()  # PyOngc puede repetir un NGC ligado a varios M (M101/M102)

    for messier in ongc.listObjects(catalog="M"):
        if messier.name in nombres_vistos:
            continue
        nombres_vistos.add(messier.name)

        coord = SkyCoord(messier.ra, messier.dec, unit=(u.hourangle, u.deg))
        altaz_now = coord.transform_to(altaz_at_start)
        alt_now_deg = altaz_now.alt.to(u.degree).value

        if altaz_now.alt <= min_angle * u.deg:
            continue

        # Metadatos del objeto
        data = json.loads(messier.to_json())
        obj_type = data.get("type", "Object of other/unknown type")
        size_major = data["dimensions"]["major axis"] or 0
        size_minor = data["dimensions"]["minor axis"] or 0
        pa = data["dimensions"]["position angle"] or 0
        messier_id = data["other identifiers"]["messier"]
        common_name = (
            messier._commonnames.split(",")[0] if messier._commonnames else ""
        )

        # ── Tránsito meridiano ──
        # Si el tránsito cae dentro de la noche astronómica, ese es el mejor
        # momento. Si no (objeto que ya pasó el meridiano antes del ocaso o
        # que transitará después del amanecer), la altitud actual ya es lo
        # mejor que vamos a tener.
        transit_time = observer.target_meridian_transit_time(
            night_start_time, coord, which='nearest'
        )
        transit_in_night = (
            night_start_time <= transit_time <= night_end_time
        )
        if transit_in_night:
            transit_altaz = coord.transform_to(
                AltAz(location=location, obstime=transit_time)
            )
            max_alt_deg = transit_altaz.alt.deg
            transit_str = fmt_local_hm(transit_time, local_tz)
            best_time = transit_time
            best_alt_deg = max_alt_deg
        else:
            max_alt_deg = alt_now_deg
            transit_str = "—"
            best_time = night_start_time
            best_alt_deg = alt_now_deg

        # ── Posición de la luna en el mejor momento ──
        moon_at_best = get_body('moon', best_time, location=location)
        moon_sep = coord.separation(moon_at_best).deg
        moon_altaz_best = moon_at_best.transform_to(
            AltAz(location=location, obstime=best_time)
        )
        moon_alt_best = moon_altaz_best.alt.deg

        # ── Umbral duro: si la luna brillante está prácticamente encima ──
        if moon_sep < 15 and illum > 0.50 and moon_alt_best > 0:
            continue

        score = compute_score(
            alt_deg=best_alt_deg,
            size_major=size_major,
            moon_sep_deg=moon_sep,
            moon_alt_deg=moon_alt_best,
            illum=illum,
            obj_type=obj_type,
            sqm=sqm,
        )

        visible.append({
            'messier_id': messier_id,
            'notation': messier.name,
            'common_name': common_name,
            'ra': coord.ra.to_string(u.hour),
            'dec': coord.dec.to_string(u.degree),
            'az_deg': altaz_now.az.to(u.degree).value,
            'alt_deg': alt_now_deg,
            'max_alt': f"{max_alt_deg:.1f}",
            'transit': transit_str,
            'moon_sep': moon_sep,
            'size_major': size_major,
            'size_minor': size_minor,
            'pa': pa,
            'score': score,
        })

    return visible


def render_messier_table(rows, night_start_local):
    """Construye la rich.Table con los objetos Messier visibles."""
    table = Table(
        title=(
            f"Visible Messier Objects on "
            f"{night_start_local.strftime('%d/%m/%Y %H:%M:%S %Z%z')}"
        ),
        show_lines=True,
    )
    columns = [
        ("Messier",             "left",  "green"),
        ("Notation",            "left",  "cyan"),
        ("Name",                "left",  "magenta"),
        ("RA (J2000)",          "right", None),
        ("Dec (J2000)",         "right", None),
        ("Azimuth (°)",         "right", None),
        ("Altitude (°)",        "right", None),
        ("Max Alt (°)",         "right", None),
        ("Transit",             "right", None),
        ("Moon dist (°)",       "right", None),
        ("Size major (arcmin)", "right", None),
        ("Size minor (arcmin)", "right", None),
        ("PA",                  "right", None),
        ("Score",               "right", "bold yellow"),
    ]
    for col, justify, style in columns:
        table.add_column(col, justify=justify, style=style)

    for r in rows:
        table.add_row(
            str(r['messier_id']),
            str(r['notation']),
            str(r['common_name']),
            str(r['ra']),
            str(r['dec']),
            f"{r['az_deg']:.4f}",
            f"{r['alt_deg']:.4f}",
            r['max_alt'],
            r['transit'],
            f"{r['moon_sep']:.1f}",
            '-' if r['size_major'] == 0 else str(r['size_major']),
            '-' if r['size_minor'] == 0 else str(r['size_minor']),
            '-' if r['pa'] == 0 else str(r['pa']),
            f"{r['score']:.0f}",
        )
    return table


# ─────────────────────────────────────────────────────────────────────────────
# Panel de la Luna
# ─────────────────────────────────────────────────────────────────────────────

def moon_phase_name(elongation_deg):
    """Devuelve el nombre de la fase a partir de la elongación geocéntrica.

    La elongación es la diferencia de longitud eclíptica Luna - Sol;
    distingue de forma inequívoca creciente (0-180°) de menguante (180-360°).
    """
    e = elongation_deg % 360
    if e < 5 or e >= 355:
        return "Nueva"
    if e < 85:
        return "Creciente"
    if e < 95:
        return "Cuarto creciente"
    if e < 175:
        return "Gibosa creciente"
    if e < 185:
        return "Llena"
    if e < 265:
        return "Gibosa menguante"
    if e < 275:
        return "Cuarto menguante"
    return "Menguante"


def build_moon_panel(obstime, location, local_tz):
    """Panel con fase, iluminación, salida/puesta y posición actual."""
    t = Time(obstime)
    observer = Observer(location=location)

    # Sol y luna geocéntricos para calcular elongación
    sun = get_sun(t)
    moon = get_body('moon', t, location=location)

    # Elongación eclíptica (Luna - Sol)
    sun_ecl = sun.transform_to(GeocentricMeanEcliptic())
    moon_ecl = moon.transform_to(GeocentricMeanEcliptic())
    elong = (moon_ecl.lon - sun_ecl.lon).wrap_at(360 * u.deg).deg

    illum = moon_illumination(t) * 100

    # Posición horaria actual desde el observador
    moon_altaz = moon.transform_to(AltAz(location=location, obstime=t))
    alt = moon_altaz.alt.deg
    az = moon_altaz.az.deg

    # Salida y puesta. Si la luna ya está arriba miramos su salida más
    # reciente y la próxima puesta; si está abajo, próxima salida y
    # puesta posteriores.
    horizon = 0 * u.deg
    if alt > 0:
        rise_time = observer.moon_rise_time(t, which='previous', horizon=horizon)
        set_time = observer.moon_set_time(t, which='next', horizon=horizon)
    else:
        rise_time = observer.moon_rise_time(t, which='next', horizon=horizon)
        set_time = observer.moon_set_time(t, which='next', horizon=horizon)

    def fmt_time(time_val):
        try:
            local = time_val.to_datetime(timezone=local_tz)
            return local.strftime('%d/%m %H:%M %Z')
        except (ValueError, TypeError, AttributeError):
            return "—"

    def hours_between(future, ref):
        """Horas entre dos Time, o None si no se puede computar."""
        try:
            delta = float((future - ref).to(u.hour).value)
            return delta if delta == delta else None  # filtra NaN
        except (TypeError, ValueError, AttributeError):
            return None

    # ¿Molestará la luna durante la sesión?
    horas_hasta_salida = hours_between(rise_time, t) if alt <= 0 else None
    luna_molestara = (alt > 0) or (
        horas_hasta_salida is not None and 0 <= horas_hasta_salida < 8
    )

    lines = [
        f"[bold yellow]Fase:[/] {moon_phase_name(elong)}",
        f"[bold yellow]Iluminación:[/] {illum:.1f}%",
        f"[bold yellow]Elongación:[/] {elong:.1f}°",
        f"[bold yellow]Salida:[/] {fmt_time(rise_time)}",
        f"[bold yellow]Puesta:[/] {fmt_time(set_time)}",
    ]

    if alt > 0:
        lines.append(
            f"[bold orange1]Posición ahora:[/] Alt {alt:.1f}°  Az {az:.1f}°"
        )
    elif horas_hasta_salida is not None and horas_hasta_salida < 8:
        lines.append(
            f"[orange1]Bajo horizonte ahora — saldrá en "
            f"{horas_hasta_salida:.1f}h[/]"
        )
    else:
        lines.append("[green]Bajo horizonte y no sale en la sesión[/]")

    if illum > 40 and luna_molestara:
        lines.append(
            "[red]Aviso: brillo lunar afectará a DSO de bajo brillo "
            "superficial[/]"
        )

    return Panel(
        "\n".join(lines), title="Luna", border_style="yellow", expand=False
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tabla de planetas
# ─────────────────────────────────────────────────────────────────────────────

def build_planet_table(obstime, location, min_angle):
    """Tabla de planetas por encima del ángulo mínimo, o None si ninguno."""
    t = Time(obstime)
    altaz_frame = AltAz(location=location, obstime=t)
    nombres = {
        'mercury': 'Mercurio',
        'venus':   'Venus',
        'mars':    'Marte',
        'jupiter': 'Júpiter',
        'saturn':  'Saturno',
        'uranus':  'Urano',
        'neptune': 'Neptuno',
    }
    visibles = []
    for clave_en, nombre_es in nombres.items():
        body = get_body(clave_en, t, location=location)
        body_altaz = body.transform_to(altaz_frame)
        if body_altaz.alt > min_angle * u.deg:
            visibles.append((
                nombre_es,
                body.ra.to_string(u.hour, precision=1),
                body.dec.to_string(u.degree, precision=1),
                body_altaz.az.to(u.degree).value,
                body_altaz.alt.to(u.degree).value,
            ))
    if not visibles:
        return None
    visibles.sort(key=lambda x: -x[4])

    table = Table(
        title=(
            f"Planetas visibles (Alt > {min_angle}°) al inicio de la "
            f"noche astronómica"
        ),
        show_lines=True,
    )
    table.add_column("Planeta", style="cyan")
    table.add_column("RA (J2000)", justify="right")
    table.add_column("Dec (J2000)", justify="right")
    table.add_column("Azimut (°)", justify="right")
    table.add_column("Altura (°)", justify="right")
    for p in visibles:
        table.add_row(p[0], p[1], p[2], f"{p[3]:.4f}", f"{p[4]:.4f}")
    return table


# ─────────────────────────────────────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float,
                        help="latitude of location in degrees")
    parser.add_argument("--lon", type=float,
                        help="longitude of location in degrees")
    parser.add_argument("--alt", type=float, default=0,
                        help="altitude of location in meters")
    parser.add_argument("--date", type=str, default="",
                        help="date in YYYYMMDD format")
    parser.add_argument("--angle", type=float, default=10,
                        help="minimum angle above horizon in degrees")
    parser.add_argument("--sqm", type=float, default=None,
                        help="sky quality in mag/arcsec² (e.g. 20.36 for "
                             "rural site, 18.0 for urban). Preferred over "
                             "--bortle.")
    parser.add_argument("--bortle", type=int, default=None,
                        help="Bortle scale 1-9 (1=pristine, 9=inner city). "
                             "Used only if --sqm is not given.")
    args = parser.parse_args()
    if args.lat is None or args.lon is None:
        args.lat = 40.4168
        args.lon = -3.7038
    main(args.lat, args.lon, args.alt, args.date, args.angle,
         args.sqm, args.bortle)