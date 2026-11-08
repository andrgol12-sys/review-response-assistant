import logging

import httpx

from config import get_settings
from models import RemoteReview, ReviewTone


logger = logging.getLogger("worker.telegram")
settings = get_settings()

TONE_LABELS = {
    ReviewTone.POSITIVE.value: "положительный",
    ReviewTone.NEGATIVE.value: "отрицательный",
    ReviewTone.NEUTRAL.value: "нейтральный",
}


def get_target_chat_id() -> str:
    return settings.telegram_user_chat_id or settings.telegram_chat_id


def build_review_message(review: RemoteReview) -> str:
    tone_label = TONE_LABELS.get(review.tone, "не определен")
    author = review.name or "Аноним"
    return (
        "Новый отзыв\n"
        f"ID: {review.id}\n"
        f"Имя: {author}\n"
        f"Тон: {tone_label}\n"
        f"Дата: {review.created_at}\n"
        f"Текст:\n{review.text}"
    )


async def send_new_review_notification(review: RemoteReview) -> bool:
    chat_id = get_target_chat_id()
    if not settings.telegram_bot_token or not chat_id:
        logger.info("Telegram personal chat settings are not configured, skipping notification")
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": build_review_message(review),
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        logger.info("Telegram notification sent to personal chat for review id=%s", review.id)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send Telegram notification for review id=%s: %s", review.id, exc)
        return False
