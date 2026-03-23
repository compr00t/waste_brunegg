from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    CONF_ENTSORGUNGSPLAN_URL,
    CONF_INCLUDE_GRUENGUT,
    CONF_INCLUDE_HAUSKEHRICHT,
    CONF_OCCURRENCES_COUNT,
    CONF_OVERRIDE_GRUENGUT_DATES,
    CONF_OVERRIDE_HAUSKEHRICHT_DATES,
    CONF_OVERRIDE_WASCHABO_DATES,
    CONF_WASCHABO_TIER,
    DEFAULT_ENTSORGUNGSPLAN_URL,
    DEFAULT_INCLUDE_GRUENGUT,
    DEFAULT_INCLUDE_HAUSKEHRICHT,
    DEFAULT_OCCURRENCES_COUNT,
    DEFAULT_WASCHABO_TIER,
    DOMAIN,
    MAX_OCCURRENCES_COUNT,
    MIN_OCCURRENCES_COUNT,
    WASCHABO_TIERS,
)


def _schema(defaults: dict[str, Any], *, include_overrides: bool = False) -> vol.Schema:
    data: dict[Any, Any] = {
        vol.Required(
            CONF_ENTSORGUNGSPLAN_URL,
            default=defaults.get(CONF_ENTSORGUNGSPLAN_URL, DEFAULT_ENTSORGUNGSPLAN_URL),
        ): str,
        vol.Required(
            CONF_INCLUDE_HAUSKEHRICHT,
            default=defaults.get(CONF_INCLUDE_HAUSKEHRICHT, DEFAULT_INCLUDE_HAUSKEHRICHT),
        ): bool,
        vol.Required(
            CONF_INCLUDE_GRUENGUT,
            default=defaults.get(CONF_INCLUDE_GRUENGUT, DEFAULT_INCLUDE_GRUENGUT),
        ): bool,
        vol.Required(
            CONF_WASCHABO_TIER,
            default=defaults.get(CONF_WASCHABO_TIER, DEFAULT_WASCHABO_TIER),
        ): vol.In(WASCHABO_TIERS),
        vol.Required(
            CONF_OCCURRENCES_COUNT,
            default=defaults.get(CONF_OCCURRENCES_COUNT, DEFAULT_OCCURRENCES_COUNT),
        ): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_OCCURRENCES_COUNT, max=MAX_OCCURRENCES_COUNT),
        ),
    }
    if include_overrides:
        data.update(
            {
                vol.Optional(
                    CONF_OVERRIDE_HAUSKEHRICHT_DATES,
                    default=defaults.get(CONF_OVERRIDE_HAUSKEHRICHT_DATES, ""),
                ): str,
                vol.Optional(
                    CONF_OVERRIDE_GRUENGUT_DATES,
                    default=defaults.get(CONF_OVERRIDE_GRUENGUT_DATES, ""),
                ): str,
                vol.Optional(
                    CONF_OVERRIDE_WASCHABO_DATES,
                    default=defaults.get(CONF_OVERRIDE_WASCHABO_DATES, ""),
                ): str,
            }
        )
    return vol.Schema(data)


class BruneggConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            await self.async_set_unique_id("brunegg_entsorgung")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Brunegg Entsorgung", data=user_input
            )
        return self.async_show_form(step_id="user", data_schema=_schema({}))

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return BruneggOptionsFlow(config_entry)


class BruneggOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        defaults = {**self._entry.data, **self._entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(defaults, include_overrides=False),
        )
