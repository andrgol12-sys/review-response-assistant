import asyncio
import logging

from client import ReviewSiteClient
from config import get_settings
from models import ReviewCreatePayload, ReviewStatus, ReviewTone, ReviewUpdatePayload
from processor import detect_tone, generate_response
from state import get_worker_state
from telegram_bot import send_new_review_notification


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("worker")
settings = get_settings()
state = get_worker_state()
client = ReviewSiteClient()


def is_ai_authored(review_name: str | None) -> bool:
    if not review_name:
        return False
    return review_name.strip().casefold() == settings.ai_author_name.strip().casefold()


async def wait_for_site() -> None:
    logger.info("Waiting for target site at %s", settings.target_site_url)
    while True:
        try:
            await client.check_site()
            logger.info("Target site is ready")
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Target site is not ready yet: %s", exc)
            await asyncio.sleep(3)


async def process_new_reviews() -> int:
    reviews = await client.fetch_new_reviews()

    for review in reviews:
        logger.info("Processing review id=%s", review.id)

        if is_ai_authored(review.name):
            logger.info("Review id=%s was created by AI, marking as processed without reply", review.id)
            await client.update_review(
                review.id,
                ReviewUpdatePayload(
                    status=ReviewStatus.PROCESSED,
                    tone=ReviewTone.NEUTRAL,
                ),
            )
            state.mark_processed(review.id)
            continue

        tone = detect_tone(review.text)
        review.tone = tone.value

        if not state.is_notified(review.id):
            notification_sent = await send_new_review_notification(review)
            if notification_sent:
                state.mark_notified(review.id)

        if state.is_processed(review.id):
            logger.info("Review id=%s already processed in local state, skipping duplicate", review.id)
            continue

        response_text = await generate_response(review.text)
        ai_reply = await client.create_review(
            ReviewCreatePayload(
                parent_id=review.id,
                name=settings.ai_author_name,
                text=response_text,
            ),
        )
        await client.update_review(
            review.id,
            ReviewUpdatePayload(
                status=ReviewStatus.PROCESSED,
                tone=tone,
            ),
        )
        await client.update_review(
            ai_reply.id,
            ReviewUpdatePayload(
                status=ReviewStatus.PROCESSED,
                tone=ReviewTone.NEUTRAL,
            ),
        )
        state.mark_processed(ai_reply.id)
        state.mark_processed(review.id)
        logger.info("Review id=%s processed", review.id)

    return len(reviews)


async def main() -> None:
    await wait_for_site()
    logger.info(
        "Worker started with poll interval=%s seconds, target site=%s",
        settings.worker_poll_interval,
        settings.target_site_url,
    )

    while True:
        processed_count = await process_new_reviews()
        if processed_count:
            logger.info("Processed %s review(s) in current iteration", processed_count)
        await asyncio.sleep(settings.worker_poll_interval)


if __name__ == "__main__":
    asyncio.run(main())
