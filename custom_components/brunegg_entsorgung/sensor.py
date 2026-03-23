from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
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
        key="health",
        translation_key="health",
        date_getter=lambda _c, _entry: [],
    ),
    BruneggSensorDescription(
        key="hauskehricht",
        translation_key="hauskehricht",
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
    _attr_has_entity_name = True

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
        self._attr_name = None

    @property
    def native_value(self) -> str:
        if self.entity_description.key == "health":
            return "ok" if self.coordinator.last_update_success else "error"
        today = date.today()
        dates = self.entity_description.date_getter(self.coordinator, self._entry)
        return _relative_text(today, _next_date(dates, today))

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        if self.entity_description.key == "health":
            return {
                "last_update_success": self.coordinator.last_update_success,
                "last_exception": (
                    str(self.coordinator.last_exception)
                    if self.coordinator.last_exception
                    else None
                ),
                "plan_year": self.coordinator.data.parsed.plan_year,
                "source_pdf": self.coordinator.data.pdf_url,
            }
        today = date.today()
        dates = self.entity_description.date_getter(self.coordinator, self._entry)
        nd = _next_date(dates, today)
        options = {**self._entry.data, **self._entry.options}
        occurrences_count = options.get(CONF_OCCURRENCES_COUNT, DEFAULT_OCCURRENCES_COUNT)
        next_dates = _next_occurrences(dates, today, occurrences_count)
        return {
            "next_date": nd.isoformat() if nd else None,
            "next_occurrences": [d.isoformat() for d in next_dates],
            "occurrences_count": occurrences_count,
            "plan_year": self.coordinator.data.parsed.plan_year,
            "source_pdf": self.coordinator.data.pdf_url,
        }
