# Brunegg Entsorgung

Home Assistant custom integration for Brunegg waste schedules.

It fetches the latest PDF from the Gemeinde Brunegg Entsorgungsplan page, extracts:

- Hauskehricht dates
- Grüngutabfuhr dates
- Waschaboservice dates (Bronze / Silber / Gold)

and creates Home Assistant sensors with human-readable next occurrence states:

- `Heute`
- `Morgen`
- `in X Tagen`

## Installation

### Option 1: HACS (recommended)

This follows the common HACS installation flow used by integrations such as `hacs_waste_collection_schedule`.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=compr00t&repository=waste_brunegg&category=integration)

1. In Home Assistant, open **HACS**.
2. Go to **Custom repositories**.
3. Add your repository URL as category **Integration**.
4. Search for **Brunegg Entsorgung** and install it.
5. Restart Home Assistant.

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

