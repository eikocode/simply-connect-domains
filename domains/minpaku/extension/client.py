"""
Minpaku API Client

Integration with Minpaku vacation rental system.
Used by simply-connect extensions to sync properties and query bookings.

Reads MINPAKU_API_URL and MINPAKU_API_KEY from environment / .env.
"""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv(override=False)


class MinpakuClient:
    """Client for Minpaku vacation rental API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize Minpaku client.

        Args:
            base_url: Base URL for Minpaku API. Falls back to MINPAKU_API_URL env var.
            api_key:  API key for authentication. Falls back to MINPAKU_API_KEY env var.
        """
        self.base_url = base_url or os.getenv("MINPAKU_API_URL") or os.getenv("MINPAKU_BASE_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("MINPAKU_API_KEY", "")
        self.timeout = 30.0

    def _headers(self) -> dict:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    @staticmethod
    def _flatten_records(value) -> list[dict]:
        records: list[dict] = []

        def _walk(item) -> None:
            if isinstance(item, dict):
                records.append(item)
                return
            if isinstance(item, list):
                for child in item:
                    _walk(child)

        _walk(value)
        return records

    def _inventory_search(self, payload: Optional[dict] = None) -> list[dict]:
        """Query the richer inventory endpoint, which includes houseRules inline."""
        import httpx

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/ucp/inventory/search",
                json=payload or {},
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("offers", data if isinstance(data, list) else [])

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

    # -------------------------------------------------------------------------
    # Property queries
    # -------------------------------------------------------------------------

    def list_properties(self) -> list[dict]:
        """
        List all properties in Minpaku.

        Returns:
            List of property dicts.
        """
        try:
            return self._inventory_search({})
        except Exception:
            import httpx

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/acp/properties",
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
                return data.get("products", data if isinstance(data, list) else [])

    def search_properties(self, query: str) -> list[dict]:
        """
        Search properties by name or identifier.

        Args:
            query: Search string to match against property name or ID.

        Returns:
            Filtered list of matching property dicts.
        """
        all_props = self._inventory_search({})
        if not query.strip():
            return all_props
        return [p for p in all_props if self._matches_query(p, query)]

    # -------------------------------------------------------------------------
    # Booking queries
    # -------------------------------------------------------------------------

    def get_bookings_by_property(self, property_id: str) -> dict:
        """
        Get all bookings for a specific property.

        Args:
            property_id: ID of property to get bookings for.

        Returns:
            Bookings dict for the property.
        """
        import httpx

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/ucp/bookings/by-property",
                params={"propertyId": property_id},
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def confirm_booking(self, booking_id: str, payment_method_token: str | None = None) -> dict:
        import httpx

        payload: dict[str, str] = {"bookingId": booking_id}
        if payment_method_token:
            payload["paymentMethodToken"] = payment_method_token

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/ucp/bookings/confirm",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    # -------------------------------------------------------------------------
    # Listing queries
    # -------------------------------------------------------------------------

    def list_listings(
        self,
        property_id: str | None = None,
        platform: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        import httpx

        params: dict[str, str] = {}
        if property_id:
            params["propertyId"] = property_id
        if platform:
            params["platform"] = platform
        if status:
            params["status"] = status

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/listings",
                params=params or None,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                raw_rows = data.get("listings", [])
            elif isinstance(data, list):
                raw_rows = data
            else:
                raw_rows = []
            return self._flatten_records(raw_rows)

    def search_listings(self, query: str) -> list[dict]:
        query_lower = query.lower().strip()
        listings = self._flatten_records(self.list_listings())
        if not query_lower:
            return listings

        def _matches(listing: dict) -> bool:
            property_info = listing.get("property") or {}
            fields = (
                listing.get("id", ""),
                listing.get("propertyId", ""),
                listing.get("platform", ""),
                listing.get("externalId", ""),
                listing.get("title", ""),
                listing.get("description", ""),
                property_info.get("title", ""),
            )
            return any(query_lower in str(value).lower() for value in fields)

        return [listing for listing in listings if _matches(listing)]

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

    def create_listing(self, payload: dict) -> dict:
        import httpx

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/listings",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def get_property(self, property_id: str) -> dict:
        import httpx

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/acp/properties/{property_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                prop = data.get("property")
                if isinstance(prop, dict):
                    return prop
            return data if isinstance(data, dict) else {}

    def update_listing(self, listing_id: str, payload: dict) -> dict:
        import httpx

        with httpx.Client(timeout=self.timeout) as client:
            response = client.put(
                f"{self.base_url}/listings/{listing_id}",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def delete_listing(self, listing_id: str) -> dict:
        import httpx

        with httpx.Client(timeout=self.timeout) as client:
            response = client.delete(
                f"{self.base_url}/listings/{listing_id}",
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


# -----------------------------------------------------------------------------
# Convenience function
# -----------------------------------------------------------------------------

def get_minpaku_client() -> MinpakuClient:
    """Get a configured MinpakuClient from environment variables."""
    return MinpakuClient()
