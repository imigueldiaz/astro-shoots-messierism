import argparse
from datetime import datetime
import json
import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord, AltAz, get_sun, get_body
from astropy.time import Time
from pyongc import ongc
from rich.console import Console
from rich.table import Table

def main(latitude, longitude, altitude, date, min_angle):
    location = EarthLocation(lat=latitude*u.deg, lon=longitude*u.deg, height=altitude*u.m)

    if date:
        time = Time(datetime.strptime(date, "%Y%m%d"))
    else:
        time = Time.now()

    altaz = AltAz(location=location, obstime=time)

    sun = get_sun(time)
    sun_altaz = sun.transform_to(altaz)

    # Calculate the start of the astronomical night (when the sun is 18 degrees below the horizon)
    # This requires iterating over times and checking the sun's altitude until it reaches -18 degrees.
    astronomical_night_start = None
    for hour in range(-12, 13): # Adjust the range as needed
        test_time = time + hour * u.hour
        test_sun = get_sun(test_time)
        test_sun_altaz = test_sun.transform_to(AltAz(location=location, obstime=test_time))
        if test_sun_altaz.alt.deg < -18:
            astronomical_night_start = test_time
            break

    if astronomical_night_start is None:
        print("Could not calculate the start of the astronomical night.")
        return

    print(f"Astronomical night time on {time.datetime.strftime('%d/%m/%Y')}:")
    print(f"Start: {astronomical_night_start.datetime.strftime('%d/%m/%Y %H:%M:%S')}")

    messier_catalog = ongc.listObjects(catalog="M")

    visible_objects = []
    for messier in messier_catalog:
        coord = SkyCoord(messier.ra, messier.dec, unit=(u.hourangle, u.deg))
        altaz_coord = coord.transform_to(altaz)

        messier_json = messier.to_json()
        messier_data = json.loads(messier_json)

        size_major = messier_data["dimensions"]["major axis"]
        size_minor = messier_data["dimensions"]["minor axis"]
        pa = messier_data["dimensions"]["position angle"]

        if size_major is None:
            size_major = 0
        if size_minor is None:
            size_minor = 0
        if pa is None:
            pa = 0

        other_identifiers_messier = messier_data["other identifiers"]["messier"]

        if altaz_coord.alt > min_angle*u.deg and time > astronomical_night_start:
            visible_objects.append((
                other_identifiers_messier,
                messier.name,
                messier._commonnames,
                coord.ra.to_string(u.hour),
                coord.dec.to_string(u.degree),
                altaz_coord.az.to(u.degree).value,
                altaz_coord.alt.to(u.degree).value,
                size_major,
                size_minor,
                pa
            ))

    visible_objects.sort(key=lambda x: (-x[6], -x[7]))

    table = Table(title=f"Visible Messier Objects on {time.datetime.strftime('%d/%m/%Y')} after {astronomical_night_start.datetime.strftime('%H:%M:%S')}", show_lines=True)
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
        # Format Azimuth and Altitude with 4 decimal places
        azimuth = f"{obj[5]:.4f}"
        altitude = f"{obj[6]:.4f}"
        # Create a new list with the formatted values
        formatted_obj = list(obj[:5]) + [azimuth, altitude] + list(obj[7:])
        table.add_row(*[str(x) for x in formatted_obj])


    console = Console()
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
        # Set default values for latitude and longitude if not provided
        args.lat = 40.4168  # Example: Latitude of Madrid, Spain
        args.lon = -3.7038  # Example: Longitude of Madrid, Spain

    main(args.lat, args.lon, args.alt, args.date, args.angle)
