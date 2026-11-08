import logging

import httpx

from config import get_settings
from models import RemoteReview, ReviewCreatePayload, ReviewStatus, ReviewUpdatePayload


logger = logging.getLogger("worker.client")
settings = get_settings()


class ReviewSiteClient:
    def __init__(self) -> None:
        self._base_url = settings.target_site_url.rstrip("/")
        self._headers = {"X-Worker-Token": settings.worker_api_token}

    async def check_site(self) -> None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{self._base_url}/")
            response.raise_for_status()

    async def fetch_reviews(self) -> list[RemoteReview]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{self._base_url}/api/reviews")
            response.raise_for_status()
        payload = response.json()
        return [RemoteReview.model_validate(item) for item in payload]

    async def fetch_new_reviews(self) -> list[RemoteReview]:
        reviews = await self.fetch_reviews()
        return [review for review in reviews if review.status == ReviewStatus.NEW]

    async def create_review(self, payload: ReviewCreatePayload) -> RemoteReview:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self._base_url}/api/reviews",
                json=payload.model_dump(mode="json", exclude_none=True),
            )
            response.raise_for_status()
        logger.info("Created reply review for parent id=%s", payload.parent_id)
        return RemoteReview.model_validate(response.json())

    async def update_review(self, review_id: int, payload: ReviewUpdatePayload) -> RemoteReview:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.patch(
                f"{self._base_url}/api/reviews/{review_id}",
                headers=self._headers,
                json=payload.model_dump(mode="json", exclude_none=True),
            )
            response.raise_for_status()
        logger.info("Review id=%s updated on target site", review_id)
        return RemoteReview.model_validate(response.json())
