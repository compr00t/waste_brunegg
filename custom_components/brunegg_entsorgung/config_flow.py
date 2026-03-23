from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    CONF_ENTSORGUNGSPLAN_URL,
    CONF_INCLUDE_GRUENGUT,
    CONF_INCLUDE_HAUSKEHRICHT,
    CONF_WASCHABO_TIER,
    DEFAULT_ENTSORGUNGSPLAN_URL,
    DEFAULT_INCLUDE_GRUENGUT,
    DEFAULT_INCLUDE_HAUSKEHRICHT,
    DEFAULT_WASCHABO_TIER,
    DOMAIN,
    WASCHABO_TIERS,
)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_ENTSORGUNGSPLAN_URL,
                default=defaults.get(
                    CONF_ENTSORGUNGSPLAN_URL, DEFAULT_ENTSORGUNGSPLAN_URL
                ),
            ): str,
            vol.Required(
                CONF_INCLUDE_HAUSKEHRICHT,
                default=defaults.get(
                    CONF_INCLUDE_HAUSKEHRICHT, DEFAULT_INCLUDE_HAUSKEHRICHT
                ),
            ): bool,
            vol.Required(
                CONF_INCLUDE_GRUENGUT,
                default=defaults.get(CONF_INCLUDE_GRUENGUT, DEFAULT_INCLUDE_GRUENGUT),
            ): bool,
            vol.Required(
                CONF_WASCHABO_TIER,
                default=defaults.get(CONF_WASCHABO_TIER, DEFAULT_WASCHABO_TIER),
            ): vol.In(WASCHABO_TIERS),
        }
    )


class BruneggConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            await self.async_set_unique_id("brunegg_entsorgung")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Brunegg Entsorgung", data=user_input)
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
        return self.async_show_form(step_id="init", data_schema=_schema(defaults))
