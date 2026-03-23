from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_ENTSORGUNGSPLAN_URL, DEFAULT_ENTSORGUNGSPLAN_URL, DOMAIN
from .coordinator import BruneggCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = BruneggCoordinator(
        hass,
        entry.options.get(
            CONF_ENTSORGUNGSPLAN_URL,
            entry.data.get(CONF_ENTSORGUNGSPLAN_URL, DEFAULT_ENTSORGUNGSPLAN_URL),
        ),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: BruneggCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    if not coordinator or not coordinator.data:
        return {
            "last_update_success": getattr(coordinator, "last_update_success", None),
            "last_exception": str(getattr(coordinator, "last_exception", None)),
        }

    parsed = coordinator.data.parsed
    opts: dict[str, Any] = {**entry.data, **entry.options}
    waschabo_tier = opts.get("waschabo_tier")
    return {
        "plan_year": parsed.plan_year,
        "last_update_success": coordinator.last_update_success,
        "last_exception": str(coordinator.last_exception) if coordinator.last_exception else None,
        "entsorgungsplan_url": opts.get(CONF_ENTSORGUNGSPLAN_URL),
        "include_hauskehricht": opts.get("include_hauskehricht"),
        "include_gruengut": opts.get("include_gruengut"),
        "waschabo_tier": waschabo_tier,
        "extracted_counts": {
            "hauskehricht_dates": len(parsed.hauskehricht_dates),
            "gruengut_dates": len(parsed.gruengut_dates),
            "waschabo_bronze": len(parsed.waschabo.get("Bronze", [])),
            "waschabo_silber": len(parsed.waschabo.get("Silber", [])),
            "waschabo_gold": len(parsed.waschabo.get("Gold", [])),
        },
    }
