from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

import httpx
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import COORDINATOR_UPDATE_HOURS, DOMAIN
from .parser import ParsedPlan, parse_entsorgungsplan_pdf
from .scraper import fetch_entsorgungsplan_pdf

_LOGGER = logging.getLogger(__name__)


@dataclass
class BruneggData:
    parsed: ParsedPlan
    pdf_url: str


class BruneggCoordinator(DataUpdateCoordinator[BruneggData]):
    def __init__(self, hass: HomeAssistant, entsorgungsplan_url: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=COORDINATOR_UPDATE_HOURS),
        )
        self._entsorgungsplan_url = entsorgungsplan_url

    async def _async_update_data(self) -> BruneggData:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": "ha-brunegg-entsorgung/1.0"}
            ) as client:
                pdf_url, pdf_bytes = await fetch_entsorgungsplan_pdf(
                    client, self._entsorgungsplan_url
                )
            parsed = await self.hass.async_add_executor_job(
                parse_entsorgungsplan_pdf, pdf_bytes
            )
        except Exception as err:
            raise UpdateFailed(str(err)) from err

        _LOGGER.debug(
            "Fetched plan year %s from %s", parsed.plan_year, self._entsorgungsplan_url
        )
        return BruneggData(parsed=parsed, pdf_url=pdf_url)
