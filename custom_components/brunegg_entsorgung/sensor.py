from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_INCLUDE_GRUENGUT,
    CONF_INCLUDE_HAUSKEHRICHT,
    CONF_OCCURRENCES_COUNT,
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
    "health": "Zustand",
    "last_fetch": "Synchronisation",
}

def _next_date(dates: list[date], today: date) -> date | None:
    for d in dates:
        if d >= today:
            return d
    return None


def _next_occurrences(dates: list[date], today: date, count: int) -> list[date]:
    return [d for d in dates if d >= today][:count]


def _format_date_de(d: date) -> str:
    months = {
        1: "Januar",
        2: "Februar",
        3: "März",
        4: "April",
        5: "Mai",
        6: "Juni",
        7: "Juli",
        8: "August",
        9: "September",
        10: "Oktober",
        11: "November",
        12: "Dezember",
    }
    return f"{d.day:02d}. {months[d.month]} {d.year}"


def _join_lines(values: list[str]) -> str:
    # HA attribute popover tends to flatten lists; using U+2028 forces a visible line break.
    return "\u2028".join(values)


def _date_to_local_datetime(d: date) -> datetime:
    return datetime.combine(d, time(hour=7, minute=0), tzinfo=dt_util.DEFAULT_TIME_ZONE)


@dataclass(frozen=True, kw_only=True)
class BruneggSensorDescription(SensorEntityDescription):
    date_getter: Callable[[BruneggCoordinator, ConfigEntry], list[date]]


SENSOR_DESCRIPTIONS: tuple[BruneggSensorDescription, ...] = (
    BruneggSensorDescription(
        key="health",
        translation_key="health",
        icon="mdi:stethoscope",
        date_getter=lambda c, entry: [],
    ),
    BruneggSensorDescription(
        key="last_fetch",
        translation_key="last_fetch",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        date_getter=lambda c, entry: [],
    ),
    BruneggSensorDescription(
        key="hauskehricht",
        translation_key="hauskehricht",
        icon="mdi:trash-can-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        date_getter=lambda c, entry: (
            c.data.parsed.hauskehricht_dates
            if {**entry.data, **entry.options}.get(
                CONF_INCLUDE_HAUSKEHRICHT, DEFAULT_INCLUDE_HAUSKEHRICHT
            )
            else []
        ),
    ),
    BruneggSensorDescription(
        key="gruengut",
        translation_key="gruengut",
        icon="mdi:leaf",
        device_class=SensorDeviceClass.TIMESTAMP,
        date_getter=lambda c, entry: (
            c.data.parsed.gruengut_dates
            if {**entry.data, **entry.options}.get(
                CONF_INCLUDE_GRUENGUT, DEFAULT_INCLUDE_GRUENGUT
            )
            else []
        ),
    ),
    BruneggSensorDescription(
        key="waschabo",
        translation_key="waschabo",
        icon="mdi:washing-machine",
        device_class=SensorDeviceClass.TIMESTAMP,
        date_getter=lambda c, entry: (
            c.data.parsed.waschabo.get(
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
        device_class=SensorDeviceClass.TIMESTAMP,
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
        dates.extend(coordinator.data.parsed.hauskehricht_dates)
    if include_gg:
        dates.extend(coordinator.data.parsed.gruengut_dates)
    if tier != WASCHABO_NONE:
        tier_de = {"bronze": "Bronze", "silber": "Silber", "gold": "Gold"}[tier]
        dates.extend(coordinator.data.parsed.waschabo.get(tier_de, []))
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
        if description.key in ("health", "last_fetch"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Brunegg Entsorgung",
            manufacturer="Gemeinde Brunegg",
            model="Entsorgungsplan",
        )
        self._unsub_midnight = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.entity_description.key in ("hauskehricht", "gruengut", "waschabo", "gesamt"):
            # Recompute next-date state daily without triggering a PDF fetch.
            self._unsub_midnight = async_track_time_change(
                self.hass, self._async_handle_midnight, hour=0, minute=0, second=5
            )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_midnight is not None:
            self._unsub_midnight()
            self._unsub_midnight = None
        await super().async_will_remove_from_hass()

    async def _async_handle_midnight(self, now) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> Any:
        if self.entity_description.key == "health":
            return "OK" if self.coordinator.last_update_success else "Fehler"

        if self.entity_description.key == "last_fetch":
            last_update = getattr(self.coordinator, "last_update", None)
            if not last_update:
                return None
            return last_update

        today = dt_util.now().date()
        dates = self.entity_description.date_getter(self.coordinator, self._entry)
        nd = _next_date(dates, today)
        if nd is None:
            return None
        return _date_to_local_datetime(nd)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        if self.entity_description.key == "health":
            parsed = self.coordinator.data.parsed
            return {
                "plan_year": str(parsed.plan_year),
                "source_pdf": self.coordinator.data.pdf_url,
                "last_update_success": self.coordinator.last_update_success,
                "last_exception": str(self.coordinator.last_exception)
                if self.coordinator.last_exception
                else None,
            }

        if self.entity_description.key == "last_fetch":
            return {
                "last_update_success": self.coordinator.last_update_success,
                "last_exception": str(self.coordinator.last_exception)
                if self.coordinator.last_exception
                else None,
            }

        opts = {**self._entry.data, **self._entry.options}
        occurrences_count = opts.get(CONF_OCCURRENCES_COUNT, DEFAULT_OCCURRENCES_COUNT)

        include_hk = opts.get(CONF_INCLUDE_HAUSKEHRICHT, DEFAULT_INCLUDE_HAUSKEHRICHT)
        include_gg = opts.get(CONF_INCLUDE_GRUENGUT, DEFAULT_INCLUDE_GRUENGUT)
        tier = opts.get(CONF_WASCHABO_TIER, DEFAULT_WASCHABO_TIER)

        configured_tier = (
            {"none": "Kein Waschabo", "bronze": "Bronze", "silber": "Silber", "gold": "Gold"}
            .get(tier, "Kein Waschabo")
        )

        today = dt_util.now().date()
        used_dates = self.entity_description.date_getter(self.coordinator, self._entry)
        nd = _next_date(used_dates, today)
        next_dates = _next_occurrences(used_dates, today, occurrences_count)

        if self.entity_description.key == "gesamt":
            return {
                "Daten": _join_lines([_format_date_de(d) for d in used_dates]),
            }

        if self.entity_description.key in ("hauskehricht", "gruengut"):
            return {
                "Nächste Leerung": _format_date_de(nd) if nd else "Keine Termine",
                "Daten": _join_lines([_format_date_de(d) for d in next_dates]),
            }

        # waschabo
        return {
            "Nächste Reinigung": _format_date_de(nd) if nd else "Keine Termine",
            "Daten": _join_lines([_format_date_de(d) for d in next_dates]),
            "Abo": configured_tier,
        }
