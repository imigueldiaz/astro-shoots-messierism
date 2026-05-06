# Messierism

Messierism is a command-line tool that helps amateur astronomers plan observation sessions. Given a geographic location and a date, it calculates which Messier catalog objects, planets, and the Moon are visible during the astronomical night, and presents the results in rich, colour-coded tables in the terminal.

## Features

- **Astronomical night window** — automatically computes the start and end of astronomical twilight (Sun at −18°) for the given date and location, and evaluates object visibility across the entire window.
- **Automatic timezone resolution** — derives the local timezone from geographic coordinates via `timezonefinder`, so all displayed times are in the observer's local time. Falls back to UTC for open-ocean or invalid coordinates.
- **Sky quality modelling** — accepts sky brightness as either a continuous **SQM** value (mag/arcsec²) or a **Bortle class** (1–9), which is mapped internally to SQM. When neither is given, a default of SQM 21.0 (mid-rural) is assumed. Light pollution always penalizes the observability score, even on moonless nights.
- **Messier catalog visibility** — lists every Messier object above a configurable minimum altitude, sorted by a composite **observability score** (highest first), with:
  - Messier number and NGC/IC designation
  - Common name (when available)
  - J2000 Right Ascension and Declination
  - Current Azimuth and Altitude
  - **Maximum altitude** at meridian transit (if transit falls within the astronomical night)
  - **Meridian transit time** in local time (or `—` if transit is outside the night)
  - **Angular distance to the Moon** (in degrees, computed at the optimal observation moment)
  - Angular size (major/minor axis in arcminutes) and position angle
  - Composite observability **score** (0–100)
- **Type-aware Moon sensitivity** — each Messier object type (galaxy, nebula, globular cluster, open cluster, planetary nebula, etc.) has its own sensitivity weight. Diffuse objects like galaxies and emission nebulae are penalized more heavily by moonlight and light pollution than compact objects like globular clusters.
- **Hard lunar exclusion** — objects within 15° of a Moon that is more than 50 % illuminated and above the horizon are automatically excluded from the list.
- **Moon information panel** — displays:
  - Phase name (Nueva, Creciente, Cuarto creciente, Gibosa creciente, Llena, Gibosa menguante, Cuarto menguante, Menguante)
  - Illumination percentage and ecliptic elongation
  - Moonrise and moonset times in local time
  - Current altitude and azimuth (if above the horizon)
  - Time until moonrise (if below the horizon but rising within 8 hours)
  - Warning when strong moonlight may affect deep-sky observation
- **Visible planets table** — shows any of the seven naked-eye-to-telescope planets (Mercury through Neptune) above the minimum altitude, with their equatorial and horizontal coordinates, sorted by altitude.

## Observability Score

Each Messier object receives a composite score from **0 to 100**, computed from three weighted components:

| Component | Weight | Description |
|---|---|---|
| **Altitude** | 0–50 pts | Dominant factor. Higher altitude means less atmospheric extinction and better seeing. Based on the best altitude during the night (transit if within the night, otherwise the altitude at nightfall). |
| **Moon & Sky** | 0–30 pts | Three sub-penalties, each modulated by the object's type sensitivity: **(1)** diffuse lunar sky glow (global, proportional to illumination × whether the Moon is up); **(2)** local scatter near the Moon (falls off linearly to zero at 60° separation); **(3)** light-pollution background (derived from SQM, always active). |
| **Angular size** | 0–20 pts | Favours larger targets that are easier to frame and photograph, saturating at 30 arcmin. Modulated downward when a bright Moon is present and the object type is sensitive to sky glow. |

### Moon sensitivity by object type

| Type | Sensitivity | Rationale |
|---|---|---|
| Galaxy, Nebula, Reflection Nebula, HII region, Supernova remnant | 1.5 | Low surface brightness; strongly affected by any sky glow |
| Star cluster + Nebula | 1.2 | Mixed; nebular component is sensitive |
| Planetary Nebula | 1.0 | Small and moderately bright |
| Globular Cluster, Open Cluster | 0.7 | Compact, bright; tolerate moonlight well |
| Double star, Association of stars | 0.5 | Point-like; largely unaffected |

## Requirements

- Python ≥ 3.12
- See [`requirements.txt`](requirements.txt) for the full list of dependencies. Key libraries:
  - [`astropy`](https://www.astropy.org/) — coordinate transforms, time scales, unit handling
  - [`astroplan`](https://astroplan.readthedocs.io/) — observer, twilight, moon-rise/set, and meridian transit calculations
  - [`PyOngc`](https://github.com/mattiaverga/PyOngc) — Messier & NGC/IC catalog data
  - [`rich`](https://rich.readthedocs.io/) — terminal tables and styled output
  - [`timezonefinder`](https://github.com/jannikmi/timezonefinder) — timezone lookup from coordinates

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/imigueldiaz/astro-shoots-messierism.git
   cd astro-shoots-messierism
   ```

2. Create and activate a virtual environment:

   - **Windows (PowerShell)**:

     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```

   - **Linux / macOS**:

     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

```bash
python messierism.py [--lat LATITUDE] [--lon LONGITUDE] [--alt ALTITUDE] [--date DATE] [--angle ANGLE] [--sqm SQM] [--bortle BORTLE]
```

| Argument | Description | Default |
|---|---|---|
| `--lat` | Observer latitude in decimal degrees | `40.4168` (Madrid) |
| `--lon` | Observer longitude in decimal degrees | `-3.7038` (Madrid) |
| `--alt` | Observer altitude above sea level in metres | `0` |
| `--date` | Observation date in `YYYYMMDD` format | current date |
| `--angle` | Minimum altitude above the horizon in degrees | `10` |
| `--sqm` | Sky quality in mag/arcsec² (e.g. `20.36` for a rural site, `18.0` for urban). Takes precedence over `--bortle`. | `21.0` (mid-rural) |
| `--bortle` | Bortle scale class 1–9 (1 = pristine dark sky, 9 = inner-city). Used only when `--sqm` is not given. | — |

### Bortle-to-SQM mapping

| Bortle | SQM (mag/arcsec²) | Description |
|---|---|---|
| 1 | 21.9 | Pristine, perfect sky |
| 2 | 21.7 | Truly dark, rural |
| 3 | 21.5 | Rural |
| 4 | 21.0 | Rural/suburban transition |
| 5 | 20.5 | Suburban |
| 6 | 19.5 | Bright suburban |
| 7 | 18.5 | Suburban/urban transition |
| 8 | 18.0 | Urban |
| 9 | 17.5 | Inner city |

### Examples

```bash
# Observe from a rural site near Segovia on August 1st 2026
python messierism.py --lat 41.0786 --lon -3.4544 --date 20260801 --angle 10

# Same location, specifying sky quality via Bortle class
python messierism.py --lat 41.0786 --lon -3.4544 --date 20260801 --bortle 4

# Urban observation from Madrid with explicit SQM
python messierism.py --lat 40.4168 --lon -3.7038 --sqm 18.5
```

## Output

The script produces four sections in the terminal:

### 1. Messier Objects Table

A table of all Messier objects above the minimum altitude at the start of astronomical night, sorted by observability score (highest first):

| Column | Description |
|---|---|
| Messier | Messier catalog number (e.g. `M092`) |
| Notation | NGC or IC designation |
| Name | Common name, if any |
| RA (J2000) | Right Ascension in sexagesimal |
| Dec (J2000) | Declination in sexagesimal |
| Azimuth (°) | Horizontal azimuth in degrees |
| Altitude (°) | Horizontal altitude in degrees |
| Max Alt (°) | Peak altitude at meridian transit (`—` if transit is outside the astronomical night) |
| Transit | Local time of meridian transit (`—` if outside the astronomical night) |
| Moon dist (°) | Angular distance to the Moon in degrees |
| Size major (arcmin) | Major-axis angular size |
| Size minor (arcmin) | Minor-axis angular size |
| PA | Position angle in degrees |
| Score | Composite observability score (0–100) |

### 2. Sky Quality Line

A one-line summary showing the effective sky quality used for scoring, and its source (`--sqm`, `--bortle`, or the assumed default).

### 3. Moon Panel

A panel showing the Moon's phase, illumination, elongation, rise/set times, current position (if above the horizon), time until moonrise (if applicable), and a warning if lunar brightness may interfere with deep-sky imaging.

### 4. Planets Table

A table of planets above the minimum altitude (Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune), showing RA, Dec, azimuth, and altitude, sorted by altitude. If no planets are visible, a short message is displayed instead.

## Companion Scripts

| Script | Description |
|---|---|
| [`ngc.py`](ngc.py) | Calculates the visibility window of any single catalog object (Messier, NGC, IC, Caldwell) for a given location and date, querying SIMBAD for coordinates. |
| [`iau.py`](iau.py) | Downloads IAU constellation map images from Wikimedia Commons and compiles them into a PDF document. |

## Ethics

This project ships with an [Ethical Statement](ETHICAL.md) that outlines the values guiding its development and use. It covers seven core principles:

1. **Non-Violence** — the software must not facilitate violence of any kind, including sexual, gender-based, or institutional violence. It explicitly defends trans, non-binary, and LGBTQIA+ safety.
2. **Anti-Exploitation** — the software must not be an instrument of labour exploitation or degradation of human wellbeing.
3. **Anti-Concentration** — it must not serve to concentrate excessive wealth or corporate power.
4. **Anti-Military** — it must not be used for military purposes, weapons development, or warfare.
5. **Anti-Racism and Anti-Xenophobia** — it rejects all forms of racial discrimination and xenophobia, grounded in the scientific consensus that biological human races do not exist.
6. **Anti-Surveillance** — it must not enable mass surveillance or algorithmic oppression.
7. **Environmental and Social Justice** — it must resist environmental destruction and the privatization of essential human goods.

The Ethical Statement is not a legal mechanism but an appeal to conscience and community accountability. It operates alongside the project's [MIT License](LICENSE) without contradiction. Please read it and consider its principles when using or contributing to this project.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request. By contributing, you implicitly agree to advance the ethical principles outlined in [`ETHICAL.md`](ETHICAL.md).

## License

This project is licensed under the [MIT License](LICENSE).
