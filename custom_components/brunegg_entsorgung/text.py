from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.text import TextEntity, TextEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_OVERRIDE_GRUENGUT_DATES,
    CONF_OVERRIDE_HAUSKEHRICHT_DATES,
    CONF_OVERRIDE_WASCHABO_DATES,
    DOMAIN,
)
from .coordinator import BruneggCoordinator


@dataclass(frozen=True, kw_only=True)
class BruneggTextDescription(TextEntityDescription):
    option_key: str


TEXT_DESCRIPTIONS: tuple[BruneggTextDescription, ...] = (
    BruneggTextDescription(
        key="override_hauskehricht_dates",
        translation_key="override_hauskehricht_dates",
        icon="mdi:calendar-edit-outline",
        option_key=CONF_OVERRIDE_HAUSKEHRICHT_DATES,
    ),
    BruneggTextDescription(
        key="override_gruengut_dates",
        translation_key="override_gruengut_dates",
        icon="mdi:calendar-edit-outline",
        option_key=CONF_OVERRIDE_GRUENGUT_DATES,
    ),
    BruneggTextDescription(
        key="override_waschabo_dates",
        translation_key="override_waschabo_dates",
        icon="mdi:calendar-edit-outline",
        option_key=CONF_OVERRIDE_WASCHABO_DATES,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    coordinator: BruneggCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        BruneggOverrideTextEntity(coordinator, entry, description)
        for description in TEXT_DESCRIPTIONS
    )


class BruneggOverrideTextEntity(
    CoordinatorEntity[BruneggCoordinator], TextEntity
):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BruneggCoordinator,
        entry: ConfigEntry,
        description: BruneggTextDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Brunegg Entsorgung",
            manufacturer="Gemeinde Brunegg",
            model="Entsorgungsplan",
        )

    @property
    def native_value(self) -> str | None:
        opts: dict[str, Any] = {**self._entry.data, **self._entry.options}
        return opts.get(self.entity_description.option_key, "") or ""

    async def async_set_value(self, value: str) -> None:
        # Persist override strings into the config entry options.
        opts = dict(self._entry.options)
        opts[self.entity_description.option_key] = value
        self.hass.config_entries.async_update_entry(self._entry, options=opts)

        # Notify sensor listeners (without re-fetching the PDF).
        self.coordinator.async_set_updated_data(self.coordinator.data)

        self.async_write_ha_state()

