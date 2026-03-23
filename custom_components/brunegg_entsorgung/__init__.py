from __future__ import annotations

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
