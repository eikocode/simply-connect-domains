"""
Super-Landlord Minpaku API client.

Publishes approved listing drafts to the remote Minpaku ACP surface.
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv(override=False)


class SuperLandlordMinpakuClient:
    """Thin ACP client for Minpaku property publishing."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.base_url = base_url or os.getenv("MINPAKU_API_URL") or os.getenv("MINPAKU_BASE_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("MINPAKU_API_KEY", "")
        self.timeout = 30.0

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    @staticmethod
    def _matches_query(prop: dict, query: str) -> bool:
        query_lower = query.lower()
        fields = (
            prop.get("title", ""),
            prop.get("name", ""),
            prop.get("id", ""),
            prop.get("property_id", ""),
            prop.get("location", ""),
            prop.get("description", ""),
        )
        return any(query_lower in str(value).lower() for value in fields)

    def list_properties(self) -> list[dict]:
        import httpx

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/acp/properties",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                return data.get("products", [])
            if isinstance(data, list):
                return data
            return []

    def search_properties(self, query: str) -> list[dict]:
        props = self.list_properties()
        if not query.strip():
            return props
        return [prop for prop in props if self._matches_query(prop, query)]

    def create_property(self, payload: dict) -> dict:
        import httpx

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/acp/properties",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def update_property(self, property_id: str, payload: dict) -> dict:
        import httpx

        with httpx.Client(timeout=self.timeout) as client:
            response = client.put(
                f"{self.base_url}/acp/properties/{property_id}",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def delete_property(self, property_id: str, host_id: str | None = None) -> dict:
        import httpx

        params = {"host_id": host_id} if host_id else None
        with httpx.Client(timeout=self.timeout) as client:
            response = client.delete(
                f"{self.base_url}/acp/properties/{property_id}",
                params=params,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def list_listings(self, property_id: str | None = None) -> list[dict]:
        import httpx

        params = {"propertyId": property_id} if property_id else None
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/listings",
                params=params,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                listings = data.get("listings", [])
            elif isinstance(data, list):
                listings = data
            else:
                listings = []
            return [listing for listing in listings if isinstance(listing, dict)]

    def delete_listing(self, listing_id: str) -> dict:
        import httpx

        with httpx.Client(timeout=self.timeout) as client:
            response = client.delete(
                f"{self.base_url}/listings/{listing_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()
