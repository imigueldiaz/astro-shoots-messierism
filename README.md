# Messierism

Messierism is a Python script that calculates the visible Messier objects in the night sky for a given location and date. It uses the `astropy` and `pyongc` libraries to perform astronomical calculations and retrieve data from the Messier catalog.

## Features

- Calculates the start of the astronomical night based on the sun's position
- Determines the visible Messier objects above a specified minimum altitude
- Displays the results in a formatted table using the `rich` library
- Allows customization of location, date, and minimum altitude through command-line arguments

## Requirements

- Python 3.x
- `astropy` library
- `pyongc` library
- `rich` library

## Installation

1. Clone the repository:

```bash
git clone https://github.com/your-username/messierism.git
```

2. Install the required libraries:

```bash
pip install -r requirements.txt
```

## Usage

To run the script, use the following command:

```bash
python messierism.py [--lat LATITUDE] [--lon LONGITUDE] [--alt ALTITUDE] [--date DATE] [--angle ANGLE]
```


- `--lat LATITUDE`: Latitude of the location in degrees (default: 40.4168, latitude of Madrid, Spain)
- `--lon LONGITUDE`: Longitude of the location in degrees (default: -3.7038, longitude of Madrid, Spain)
- `--alt ALTITUDE`: Altitude of the location in meters (default: 0)
- `--date DATE`: Date in YYYYMMDD format (default: current date)
- `--angle ANGLE`: Minimum angle above the horizon in degrees (default: 10)

Example:
````bash
python messierism.py --lat 40.4168 --lon -3.7038 --date 20230415 --angle 20
````

## Output

The script will display a formatted table showing the visible Messier objects for the specified location and date. The table includes the following columns:

- Messier: Messier catalog number
- Notation: Common notation for the object
- Name: Name of the object
- RA (J2000): Right Ascension in J2000 epoch
- Dec (J2000): Declination in J2000 epoch
- Azimuth (°): Azimuth angle in degrees
- Altitude (°): Altitude angle in degrees
- Size major (arcmin): Major axis size in arcminutes
- Size minor (arcmin): Minor axis size in arcminutes
- PA: Position angle

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).


