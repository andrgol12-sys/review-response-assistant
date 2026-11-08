import logging

from openai import AsyncOpenAI

from config import get_settings
from models import ReviewTone


logger = logging.getLogger("worker.processor")
settings = get_settings()

POSITIVE_MARKERS = {
    "спасибо", "отлично", "супер", "класс", "хорош", "понрав", "рекоменд",
    "быстро", "удобно", "прекрас", "идеально", "love", "great", "awesome",
}
NEGATIVE_MARKERS = {
    "плохо", "ужас", "отврат", "проблем", "не работает", "ошибка", "долго",
    "медленно", "разочар", "сломал", "недоволен", "bad", "terrible", "awful",
}


def detect_tone(review_text: str) -> ReviewTone:
    text = review_text.lower()
    positive_score = sum(1 for marker in POSITIVE_MARKERS if marker in text)
    negative_score = sum(1 for marker in NEGATIVE_MARKERS if marker in text)

    if negative_score > positive_score:
        return ReviewTone.NEGATIVE
    if positive_score > negative_score:
        return ReviewTone.POSITIVE
    return ReviewTone.NEUTRAL


def build_fallback_response(review_text: str) -> str:
    tone = detect_tone(review_text)

    if tone == ReviewTone.NEGATIVE:
        return (
            "Нам жаль, что у вас остались негативные впечатления. "
            "Спасибо, что сообщили об этом. Пожалуйста, свяжитесь с нашей поддержкой, "
            "и мы постараемся помочь как можно быстрее."
        )

    if tone == ReviewTone.POSITIVE:
        return (
            "Спасибо за ваш отзыв и добрые слова. Нам очень приятно, "
            "что у вас остались положительные впечатления."
        )

    return (
        "Спасибо за ваш отзыв. Мы внимательно его изучили и учтем ваши замечания. "
        "Если захотите, можете поделиться деталями, чтобы мы смогли отреагировать точнее."
    )


async def generate_response(review_text: str) -> str:
    if not settings.openai_api_key:
        logger.info("OPENAI_API_KEY is not set, using fallback response generation")
        return build_fallback_response(review_text)

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = (
        "Ты помощник поддержки, который отвечает на отзывы и комментарии клиентов на русском языке. "
        "Нужно отвечать на каждый входящий текст: позитивный, негативный, нейтральный, короткий или эмоциональный. "
        "Сформируй естественный, вежливый и уместный ответ от лица компании. "
        "Если текст негативный, извинись и предложи помочь. "
        "Если текст позитивный, поблагодари. "
        "Если текст нейтральный, коротко отреагируй по существу без просьбы обязательно что-то уточнять. "
        "Не используй markdown, канцелярит, шаблонные фразы и подписи. "
        "Не повторяй отзыв дословно. "
        "Ответ должен быть на русском языке и не длиннее 3 предложений.\n\n"
        f"Отзыв: {review_text}"
    )

    try:
        response = await client.responses.create(
            model=settings.openai_model,
            input=prompt,
        )
        text = (response.output_text or "").strip()
        if text:
            return text
        logger.warning("OpenAI returned empty output_text, using fallback")
    except Exception as exc:  # noqa: BLE001
        logger.exception("OpenAI request failed, using fallback: %s", exc)

    return build_fallback_response(review_text)
