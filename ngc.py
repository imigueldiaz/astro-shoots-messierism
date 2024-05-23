import argparse
from datetime import datetime, timedelta
import numpy as np
from astropy.coordinates import EarthLocation, SkyCoord, AltAz
from astropy import units as u
from astropy.time import Time
from astroplan import Observer, FixedTarget
from astroquery.simbad import Simbad
from timezonefinder import TimezoneFinder
import pytz

def parse_arguments():
    parser = argparse.ArgumentParser(description='Calculate visibility of an astronomical object.')
    parser.add_argument('latitude', type=float, help='Latitude of the location')
    parser.add_argument('longitude', type=float, help='Longitude of the location')
    parser.add_argument('altitude', type=float, help='Altitude of the location in meters')
    parser.add_argument('date', type=str, help='ISO formatted date (YYYY-MM-DD)')
    parser.add_argument('min_angle', type=float, help='Minimum angle over the horizon in degrees')
    parser.add_argument('catalog_id', type=str, help='Catalog identifier (e.g., M1, IC10, NGC2021, Caldwell30)')
    return parser.parse_args()

def get_target(catalog_id):
    Simbad.add_votable_fields('ra(d)', 'dec(d)')
    
    # Determine the catalog and identifier
    if catalog_id.lower().startswith('m'):
        catalog = 'M '
        obj_id = catalog_id[1:]
    elif catalog_id.lower().startswith('ic'):
        catalog = 'IC '
        obj_id = catalog_id[2:]
    elif catalog_id.lower().startswith('ngc'):
        catalog = 'NGC '
        obj_id = catalog_id[3:]
    elif catalog_id.lower().startswith('caldwell'):
        catalog = 'Caldwell '
        obj_id = catalog_id[8:]
    else:
        raise ValueError(f"Invalid catalog identifier: {catalog_id}")
    
    result_table = Simbad.query_object(catalog + obj_id)
    if result_table is None:
        raise ValueError(f"Object {catalog + obj_id} not found.")
    
    ra = result_table['RA_d'][0]
    dec = result_table['DEC_d'][0]
    return FixedTarget(name=catalog + obj_id, coord=SkyCoord(ra=ra*u.deg, dec=dec*u.deg, frame='icrs'))

def get_local_timezone(latitude, longitude):
    tf = TimezoneFinder()
    return tf.timezone_at(lng=longitude, lat=latitude)

def main():
    args = parse_arguments()
    
    location = EarthLocation(lat=args.latitude*u.deg, lon=args.longitude*u.deg, height=args.altitude*u.m)
    observer = Observer(location=location, name="Observer")
    date = Time(args.date)
    
    target = get_target(args.catalog_id)
    
    # Calculate the start and end of astronomical night
    sunset = observer.sun_set_time(date, which='next')
    sunrise = observer.sun_rise_time(date + timedelta(1), which='nearest')
    
    # Check visibility
    times = sunset + np.linspace(0, (sunrise - sunset).sec, 100)*u.second
    altaz_frame = AltAz(obstime=times, location=location)
    altitudes = observer.altaz(times, target).alt
    
    visible_times = times[altitudes > args.min_angle*u.deg]
    
    if len(visible_times) > 0:
        visible_time_utc = visible_times[0].to_datetime()
        timezone_str = get_local_timezone(args.latitude, args.longitude)
        local_tz = pytz.timezone(timezone_str)
        local_time = pytz.utc.localize(visible_time_utc).astimezone(local_tz)
        print(f"{args.catalog_id} will be visible at {local_time} local time ({timezone_str}).")
    else:
        print(f"{args.catalog_id} will not be visible on the night of {args.date}.")

if __name__ == "__main__":
    main()
