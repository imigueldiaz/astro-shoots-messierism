# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- **Ethical Statement** (`ETHICAL.md`): a comprehensive ethical commitment document covering non-violence, anti-exploitation, anti-concentration, anti-military use, anti-racism, anti-surveillance, and environmental and social justice.
- **Sky quality input** via `--sqm` (mag/arcsec², continuous) and `--bortle` (Bortle scale 1–9) command-line arguments. `--sqm` takes precedence; when neither is given, a default of SQM 21.0 (mid-rural) is assumed.
- **Light-pollution penalty** in the observability score: a background sky-glow component derived from SQM that always applies, even on moonless nights, penalizing diffuse objects more than compact ones.
- **Type-aware Moon sensitivity**: each object type (galaxy, nebula, globular cluster, open cluster, planetary nebula, etc.) has its own sensitivity weight that modulates all three moon/sky score sub-penalties.
- **Meridian transit column** in the Messier table: shows the local time of meridian transit when it falls within the astronomical night window, and `—` otherwise.
- **Maximum altitude column**: displays the peak altitude each object reaches at meridian transit (within the night), giving observers a sense of the best possible viewing conditions.
- **Moon angular distance** computed at the optimal observation moment (transit if within the night, otherwise nightfall) rather than only at the start of the night.
- **Hard lunar exclusion rule**: objects within 15° of a Moon that is more than 50 % illuminated and above the horizon are automatically excluded from the results.
- **Astronomical night end time** calculation: the tool now computes both the start and end of astronomical night and uses the full window for transit and scoring logic.
- **Moon session interference warning**: the Moon panel now shows time-until-moonrise when the Moon is below the horizon but expected to rise within 8 hours, and warns if moonlight will affect the session.
- **Sky quality summary line** displayed in the terminal output, showing the effective SQM and its source.
- **CHANGELOG.md**: this file.

### Changed
- **Observability score algorithm** rewritten with three weighted components (altitude 0–50 pts, moon & sky 0–30 pts, angular size 0–20 pts) replacing the previous simpler calculation. The moon/sky component now includes diffuse sky glow, local scatter near the Moon, and light-pollution background as separate sub-penalties.
- **Angular size score** is now modulated by moonlight: large diffuse objects lose their size bonus when a bright Moon is present and they are sensitive to sky glow.
- **Score sorting**: the Messier table is now sorted by composite observability score (descending) rather than by altitude alone.
- **Moon panel** expanded with moonrise/moonset times, time-until-rise, session interference detection, and a more detailed phase name based on ecliptic elongation.

### Fixed
- Duplicate Messier entries caused by PyOngc mapping multiple Messier numbers to the same NGC object (e.g. M101/M102) are now deduplicated.
- Timezone resolution now falls back to UTC instead of crashing when `timezonefinder` returns `None` (open-ocean or invalid coordinates).

---

## [0.1.0] — 2024-04-20

### Added
- Initial release of `messierism.py` with basic Messier catalog visibility.
- Astronomical twilight detection (Sun at −18°) via `astroplan`.
- Automatic timezone resolution from geographic coordinates.
- Rich terminal output with colour-coded tables.
- Moon information panel with phase, illumination, and position.
- Visible planets table (Mercury through Neptune).
- Command-line arguments for latitude, longitude, altitude, date, and minimum altitude angle.
- Default location set to Madrid, Spain (40.4168° N, 3.7038° W).
- `ngc.py`: single-object visibility calculator querying SIMBAD.
- `iau.py`: IAU constellation map downloader and PDF compiler.
- `requirements.txt` with pinned dependencies.
- MIT License.
