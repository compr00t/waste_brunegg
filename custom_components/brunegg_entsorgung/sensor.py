from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_INCLUDE_GRUENGUT,
    CONF_INCLUDE_HAUSKEHRICHT,
    CONF_OCCURRENCES_COUNT,
    CONF_OVERRIDE_GRUENGUT_DATES,
    CONF_OVERRIDE_HAUSKEHRICHT_DATES,
    CONF_OVERRIDE_WASCHABO_DATES,
    CONF_WASCHABO_TIER,
    DEFAULT_INCLUDE_GRUENGUT,
    DEFAULT_INCLUDE_HAUSKEHRICHT,
    DEFAULT_OCCURRENCES_COUNT,
    DEFAULT_WASCHABO_TIER,
    DOMAIN,
    WASCHABO_NONE,
)
from .coordinator import BruneggCoordinator

SENSOR_NAMES_DE: dict[str, str] = {
    "hauskehricht": "Hauskehricht",
    "gruengut": "Grüngutabfuhr",
    "waschabo": "Waschaboservice",
    "gesamt": "Entsorgungskalender",
}


def _parse_override_dates(raw: str | None) -> list[date]:
    if not raw:
        return []
    dates: list[date] = []
    tokens = [t for t in re.split(r"[,\n;\s]+", raw.strip()) if t]
    for t in tokens:
        try:
            dates.append(date.fromisoformat(t))
        except ValueError:
            continue
    return sorted(set(dates))


def _relative_text(today: date, next_date: date | None) -> str:
    if not next_date:
        return "Keine Termine"
    diff = (next_date - today).days
    if diff <= 0:
        return "Heute"
    if diff == 1:
        return "Morgen"
    return f"in {diff} Tagen"


def _next_date(dates: list[date], today: date) -> date | None:
    for d in dates:
        if d >= today:
            return d
    return None


def _next_occurrences(dates: list[date], today: date, count: int) -> list[date]:
    return [d for d in dates if d >= today][:count]


@dataclass(frozen=True, kw_only=True)
class BruneggSensorDescription(SensorEntityDescription):
    date_getter: Callable[[BruneggCoordinator, ConfigEntry], list[date]]


SENSOR_DESCRIPTIONS: tuple[BruneggSensorDescription, ...] = (
    BruneggSensorDescription(
        key="hauskehricht",
        translation_key="hauskehricht",
        icon="mdi:trash-can-outline",
        date_getter=lambda c, entry: (
            _parse_override_dates(
                ({**entry.data, **entry.options}).get(CONF_OVERRIDE_HAUSKEHRICHT_DATES)
            )
            or c.data.parsed.hauskehricht_dates
        )
        if {**entry.data, **entry.options}.get(
            CONF_INCLUDE_HAUSKEHRICHT, DEFAULT_INCLUDE_HAUSKEHRICHT
        )
        else [],
    ),
    BruneggSensorDescription(
        key="gruengut",
        translation_key="gruengut",
        icon="mdi:leaf",
        date_getter=lambda c, entry: (
            _parse_override_dates(
                ({**entry.data, **entry.options}).get(CONF_OVERRIDE_GRUENGUT_DATES)
            )
            or c.data.parsed.gruengut_dates
        )
        if {**entry.data, **entry.options}.get(
            CONF_INCLUDE_GRUENGUT, DEFAULT_INCLUDE_GRUENGUT
        )
        else [],
    ),
    BruneggSensorDescription(
        key="waschabo",
        translation_key="waschabo",
        icon="mdi:washing-machine",
        date_getter=lambda c, entry: (
            _parse_override_dates(
                ({**entry.data, **entry.options}).get(CONF_OVERRIDE_WASCHABO_DATES)
            )
            or c.data.parsed.waschabo.get(
                {
                    "bronze": "Bronze",
                    "silber": "Silber",
                    "gold": "Gold",
                }.get(
                    entry.options.get(
                        CONF_WASCHABO_TIER,
                        entry.data.get(CONF_WASCHABO_TIER, DEFAULT_WASCHABO_TIER),
                    ),
                    "",
                ),
                [],
            )
        ),
    ),
    BruneggSensorDescription(
        key="gesamt",
        translation_key="gesamt",
        icon="mdi:calendar-month",
        date_getter=lambda c, entry: _combined_dates(c, entry),
    ),
)


def _combined_dates(coordinator: BruneggCoordinator, entry: ConfigEntry) -> list[date]:
    opts = {**entry.data, **entry.options}
    include_hk = opts.get(CONF_INCLUDE_HAUSKEHRICHT, DEFAULT_INCLUDE_HAUSKEHRICHT)
    include_gg = opts.get(CONF_INCLUDE_GRUENGUT, DEFAULT_INCLUDE_GRUENGUT)
    tier = opts.get(CONF_WASCHABO_TIER, DEFAULT_WASCHABO_TIER)

    dates: list[date] = []
    if include_hk:
        dates.extend(
            _parse_override_dates(opts.get(CONF_OVERRIDE_HAUSKEHRICHT_DATES))
            or coordinator.data.parsed.hauskehricht_dates
        )
    if include_gg:
        dates.extend(
            _parse_override_dates(opts.get(CONF_OVERRIDE_GRUENGUT_DATES))
            or coordinator.data.parsed.gruengut_dates
        )
    if tier != WASCHABO_NONE:
        tier_de = {"bronze": "Bronze", "silber": "Silber", "gold": "Gold"}[tier]
        dates.extend(
            _parse_override_dates(opts.get(CONF_OVERRIDE_WASCHABO_DATES))
            or coordinator.data.parsed.waschabo.get(tier_de, [])
        )
    return sorted(set(dates))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BruneggCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BruneggSensorEntity(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class BruneggSensorEntity(CoordinatorEntity[BruneggCoordinator], SensorEntity):
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: BruneggCoordinator,
        entry: ConfigEntry,
        description: BruneggSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = SENSOR_NAMES_DE.get(description.key, description.key)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Brunegg Entsorgung",
            manufacturer="Gemeinde Brunegg",
            model="Entsorgungsplan",
        )

    @property
    def native_value(self) -> str:
        today = date.today()
        dates = self.entity_description.date_getter(self.coordinator, self._entry)
        return _relative_text(today, _next_date(dates, today))

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        opts = {**self._entry.data, **self._entry.options}
        occurrences_count = opts.get(
            CONF_OCCURRENCES_COUNT, DEFAULT_OCCURRENCES_COUNT
        )

        extracted_logic = (
            "Hauskehricht: ab Startdatum woechentlich Dienstag. "
            "Grüngut: explizite Termine + woechentlicher Bereich aus PDF. "
            "Waschabo: Termine der gewaehlenen Stufe."
        )

        tier = opts.get(CONF_WASCHABO_TIER, DEFAULT_WASCHABO_TIER)
        tier_de = {"bronze": "Bronze", "silber": "Silber", "gold": "Gold"}[tier]
        configured_tier = (
            {"none": "Kein Waschabo", "bronze": "Bronze", "silber": "Silber", "gold": "Gold"}
            .get(tier, "Kein Waschabo")
        )

        extracted_hk = self.coordinator.data.parsed.hauskehricht_dates
        extracted_gg = self.coordinator.data.parsed.gruengut_dates
        extracted_wa = self.coordinator.data.parsed.waschabo.get(tier_de, [])

        override_hk = _parse_override_dates(opts.get(CONF_OVERRIDE_HAUSKEHRICHT_DATES))
        override_gg = _parse_override_dates(opts.get(CONF_OVERRIDE_GRUENGUT_DATES))
        override_wa = _parse_override_dates(opts.get(CONF_OVERRIDE_WASCHABO_DATES))

        extracted_dates: list[date]
        override_dates: list[date]

        if self.entity_description.key == "hauskehricht":
            extracted_dates = extracted_hk
            override_dates = override_hk
        elif self.entity_description.key == "gruengut":
            extracted_dates = extracted_gg
            override_dates = override_gg
        elif self.entity_description.key == "waschabo":
            extracted_dates = extracted_wa
            override_dates = override_wa
        else:
            include_hk = opts.get(CONF_INCLUDE_HAUSKEHRICHT, DEFAULT_INCLUDE_HAUSKEHRICHT)
            include_gg = opts.get(CONF_INCLUDE_GRUENGUT, DEFAULT_INCLUDE_GRUENGUT)

            extracted_dates = []
            override_dates = []
            if include_hk:
                extracted_dates.extend(extracted_hk)
                override_dates.extend(override_hk)
            if include_gg:
                extracted_dates.extend(extracted_gg)
                override_dates.extend(override_gg)
            if tier != WASCHABO_NONE:
                extracted_dates.extend(extracted_wa)
                override_dates.extend(override_wa)

        extracted_dates = sorted(set(extracted_dates))
        override_dates = sorted(set(override_dates))

        used_dates = self.entity_description.date_getter(
            self.coordinator, self._entry
        )

        today = date.today()
        nd = _next_date(used_dates, today)
        next_dates = _next_occurrences(used_dates, today, occurrences_count)

        return {
            "configured_waschabo_tier": configured_tier,
            "extraction_logic": extracted_logic,
            "extracted_dates": [d.isoformat() for d in extracted_dates],
            "override_dates": [d.isoformat() for d in override_dates],
            "using_override": bool(override_dates),
            "next_date": nd.isoformat() if nd else None,
            "next_occurrences": [d.isoformat() for d in next_dates],
        }
