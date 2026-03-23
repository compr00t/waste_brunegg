"""Constants for Brunegg Entsorgung integration."""

from __future__ import annotations

DOMAIN = "brunegg_entsorgung"
PLATFORMS = ["sensor"]

DEFAULT_NAME = "Brunegg Entsorgung"
DEFAULT_ENTSORGUNGSPLAN_URL = "https://www.brunegg.ch/entsorgungsplan"

CONF_ENTSORGUNGSPLAN_URL = "entsorgungsplan_url"
CONF_INCLUDE_HAUSKEHRICHT = "include_hauskehricht"
CONF_INCLUDE_GRUENGUT = "include_gruengut"
CONF_WASCHABO_TIER = "waschabo_tier"

WASCHABO_NONE = "none"
WASCHABO_BRONZE = "bronze"
WASCHABO_SILBER = "silber"
WASCHABO_GOLD = "gold"
WASCHABO_TIERS = [WASCHABO_NONE, WASCHABO_BRONZE, WASCHABO_SILBER, WASCHABO_GOLD]

DEFAULT_INCLUDE_HAUSKEHRICHT = True
DEFAULT_INCLUDE_GRUENGUT = True
DEFAULT_WASCHABO_TIER = WASCHABO_NONE

COORDINATOR_UPDATE_HOURS = 24
