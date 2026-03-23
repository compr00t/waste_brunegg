# Brunegg Entsorgung (Home Assistant)

Home Assistant custom integration for Brunegg waste schedules.

It fetches the latest PDF from the Gemeinde Brunegg Entsorgungsplan page, extracts:

- Hauskehricht dates
- Grüngutabfuhr dates
- Waschaboservice dates (Bronze / Silber / Gold)

and creates Home Assistant sensors with human-readable next occurrence states:

- `Heute`
- `Morgen`
- `in X Tagen`

## Features

- Daily automatic update (every 24h)
- Config flow in Home Assistant UI
- Select which streams to include:
  - Hauskehricht (on/off)
  - Grüngutabfuhr (on/off)
  - Waschabo tier (`none`, `bronze`, `silber`, `gold`)
- Combined sensor: `Entsorgungskalender`
- Health sensor: `Entsorgung Health` (`ok` / `error`)
- No local PDF persistence (PDF is processed in memory)

## Installation

### Option 1: HACS (recommended)

This follows the common HACS installation flow used by integrations such as `hacs_waste_collection_schedule`.

1. Push this repository to GitHub.
2. In Home Assistant, open **HACS**.
3. Go to **Custom repositories**.
4. Add your repository URL as category **Integration**.
5. Search for **Brunegg Entsorgung** and install it.
6. Restart Home Assistant.

### Option 2: Manual install

1. Copy `custom_components/brunegg_entsorgung` to:
   - `/config/custom_components/brunegg_entsorgung`
2. Restart Home Assistant.

## Configuration

1. Open **Settings → Devices & Services**.
2. Click **Add Integration**.
3. Search for **Brunegg Entsorgung**.
4. Configure:
   - Entsorgungsplan URL (default: `https://www.brunegg.ch/entsorgungsplan`)
   - Include Hauskehricht
   - Include Grüngutabfuhr
   - Waschabo tier

You can adjust these later via integration **Configure** (options flow).

## Entities

The integration provides these sensors:

- `Hauskehricht`
- `Grüngutabfuhr`
- `Waschaboservice`
- `Entsorgungskalender` (combined)
- `Entsorgung Health`

Each schedule sensor includes attributes:

- `next_date`
- `upcoming_dates`
- `plan_year`
- `source_pdf`

Health sensor attributes:

- `last_update_success`
- `last_exception`
- `plan_year`
- `source_pdf`

## HACS / Repository notes

Repository layout is aligned with HACS integration requirements:

- one integration under `custom_components/brunegg_entsorgung`
- `hacs.json` in repository root
- `brands/icon.png` present

Before publishing, ensure `manifest.json` values are set to your actual GitHub account/repository:

- `codeowners`
- `issue_tracker`

