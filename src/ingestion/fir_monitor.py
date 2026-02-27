"""FIR activity monitoring via OGD Platform India."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from src.config.settings import settings

logger = logging.getLogger(__name__)

_OGD_BASE = "https://data.gov.in/api/datastore/resource.json"

# Mock FIR data for demo mode
_MOCK_FIRS: list[dict[str, Any]] = [
    {
        "fir_id": "DEMO-001",
        "district": "South Delhi",
        "crime_type": "Corruption",
        "date_filed": "2024-01-15",
        "status": "Under Investigation",
    },
    {
        "fir_id": "DEMO-002",
        "district": "South Delhi",
        "crime_type": "Assault",
        "date_filed": "2024-01-20",
        "status": "Chargesheet Filed",
    },
]


@dataclass
class FIRData:
    """A single First Information Report record."""

    fir_id: str
    district: str
    crime_type: str
    date_filed: str
    status: str
    accused_details: dict = field(default_factory=dict)


class FIRMonitor:
    """Tracks FIR activity using OGD Platform India data."""

    def __init__(self) -> None:
        self._api_key = settings.ogd_api_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_firs_by_district(
        self, district: str, crime_type: str = ""
    ) -> list[FIRData]:
        """Return FIRs filed in *district*, optionally filtered by *crime_type*."""
        if not self._api_key:
            logger.warning("OGD_API_KEY not set – returning mock FIRs.")
            return self._mock_firs(district, crime_type)

        params: dict[str, Any] = {
            "api-key": self._api_key,
            "format": "json",
            "filters[district]": district,
            "limit": 50,
        }
        if crime_type:
            params["filters[crime_type]"] = crime_type

        try:
            resp = requests.get(_OGD_BASE, params=params, timeout=15)
            resp.raise_for_status()
            return self._parse(resp.json())
        except requests.RequestException as exc:
            logger.error("OGD API request failed: %s", exc)
            return []

    def calculate_fir_velocity(self, district: str) -> float:
        """Return FIRs-per-day for the last 30 days in *district*."""
        firs = self.get_firs_by_district(district)
        if not firs:
            return 0.0
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=30)
        recent = [
            f
            for f in firs
            if self._parse_date(f.date_filed) >= cutoff
        ]
        return round(len(recent) / 30.0, 3)

    def check_fir_gap(self, incident: str, district: str) -> dict:
        """Assess the gap between reported incidents and actual FIRs.

        Returns a dict describing coverage and any notable gap.
        """
        firs = self.get_firs_by_district(district)
        matching = [
            f for f in firs if incident.lower() in f.crime_type.lower()
        ]
        total = len(firs)
        matched = len(matching)
        coverage = matched / total if total else 0.0
        return {
            "incident": incident,
            "district": district,
            "total_firs": total,
            "matching_firs": matched,
            "coverage_ratio": round(coverage, 3),
            "gap_detected": coverage < 0.3 and total > 0,
            "note": (
                "Significant under-reporting gap detected."
                if coverage < 0.3 and total > 0
                else "Coverage appears adequate."
            ),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse(data: dict[str, Any]) -> list[FIRData]:
        records = data.get("records", [])
        result: list[FIRData] = []
        for r in records:
            result.append(
                FIRData(
                    fir_id=str(r.get("fir_id", "")),
                    district=r.get("district", ""),
                    crime_type=r.get("crime_type", r.get("crimeType", "")),
                    date_filed=r.get("date_filed", r.get("dateFiled", "")),
                    status=r.get("status", ""),
                )
            )
        return result

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return datetime.now(tz=timezone.utc)

    @staticmethod
    def _mock_firs(district: str, crime_type: str) -> list[FIRData]:
        firs = [
            FIRData(**{k: v for k, v in f.items()}) for f in _MOCK_FIRS
        ]
        if district:
            firs = [f for f in firs if district.lower() in f.district.lower()]
        if crime_type:
            firs = [
                f for f in firs if crime_type.lower() in f.crime_type.lower()
            ]
        return firs
