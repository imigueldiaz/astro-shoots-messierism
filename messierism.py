import argparse
from datetime import datetime, timedelta
import json
import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord, AltAz, get_sun, get_body
from astropy.time import Time
from pyongc import ongc
from rich.console import Console
from rich.table import Table
from pytz import timezone
from astroplan import Observer

def main(latitude, longitude, altitude, date, min_angle):
    console = Console()
    location = EarthLocation(lat=latitude*u.deg, lon=longitude*u.deg, height=altitude*u.m)
    time = Time(datetime.strptime(date, "%Y%m%d"), scale='utc') if date else Time.now()
    time.format = 'iso'
    time.out_subfmt = 'date_hm'
    altaz = AltAz(location=location, obstime=time)
    observer = Observer(location=location)
    astronomical_night_start = observer.twilight_evening_astronomical(time, which='next').to_datetime()
    messier_catalog = ongc.listObjects(catalog="M")
    visible_objects = []
    for messier in messier_catalog:
        coord = SkyCoord(messier.ra, messier.dec, unit=(u.hourangle, u.deg))
        altaz_coord = coord.transform_to(AltAz(location=location, obstime=astronomical_night_start))
        messier_json = messier.to_json()
        messier_data = json.loads(messier_json)
        size_major = messier_data["dimensions"]["major axis"] or 0
        size_minor = messier_data["dimensions"]["minor axis"] or 0
        pa = messier_data["dimensions"]["position angle"] or 0
        other_identifiers_messier = messier_data["other identifiers"]["messier"]
        common_name = messier._commonnames.split(",")[0] if messier._commonnames else ""
        if altaz_coord.alt > min_angle*u.deg:
            visible_objects.append((
                other_identifiers_messier,
                messier.name,
                common_name,
                coord.ra.to_string(u.hour),
                coord.dec.to_string(u.degree),
                altaz_coord.az.to(u.degree).value,
                altaz_coord.alt.to(u.degree).value,
                size_major,
                size_minor,
                pa
            ))
    visible_objects.sort(key=lambda x: (-x[6], -x[7]))
    table = Table(title=f"Visible Messier Objects on {astronomical_night_start.strftime('%d/%m/%Y %H:%M:%S %Z%z')}", show_lines=True)
    table.add_column("Messier", style="green")
    table.add_column("Notation", style="cyan")
    table.add_column("Name", style="magenta", justify="left")
    table.add_column("RA (J2000)", justify="right")
    table.add_column("Dec (J2000)", justify="right")
    table.add_column("Azimuth (°)", justify="right")
    table.add_column("Altitude (°)", justify="right")
    table.add_column("Size major (arcmin)", justify="right")
    table.add_column("Size minor (arcmin)", justify="right")
    table.add_column("PA", justify="right")
    for obj in visible_objects:
        azimuth = f"{obj[5]:.4f}"
        altitude = f"{obj[6]:.4f}"
        size_major = '-' if obj[7] == 0 else obj[7]
        size_minor = '-' if obj[8] == 0 else obj[8]
        pa = '-' if obj[9] == 0 else obj[9]
        formatted_obj = list(obj[:5]) + [azimuth, altitude] + [size_major, size_minor, pa]
        table.add_row(*[str(x) for x in formatted_obj])
    console.print(table)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, help="latitude of location in degrees")
    parser.add_argument("--lon", type=float, help="longitude of location in degrees")
    parser.add_argument("--alt", type=float, help="altitude of location in meters", default=0)
    parser.add_argument("--date", type=str, help="date in YYYYMMDD format", default="")
    parser.add_argument("--angle", type=float, help="minimum angle above horizon in degrees", default=10)
    args = parser.parse_args()
    if args.lat is None or args.lon is None:
        args.lat = 40.4168
        args.lon = -3.7038
    main(args.lat, args.lon, args.alt, args.date, args.angle)
