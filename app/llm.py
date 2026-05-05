from __future__ import annotations

import json
from typing import Any

from app.config import settings


class LLMUnavailable(RuntimeError):
    pass


def generate_recipe_payload(url: str, scraped_text: str, schema_json: dict[str, Any] | None) -> dict[str, Any] | None:
    if not settings.use_llm or not settings.google_api_key:
        return None

    try:
        extraction = _call_gemini_json(
            "recipe_extraction.txt",
            {
                "url": url,
                "schema_json": json.dumps(schema_json or {}, ensure_ascii=True)[:9000],
                "scraped_text": scraped_text[: settings.max_scraped_chars],
            },
        )
        nutrition = _call_gemini_json(
            "nutrition_estimation.txt",
            {"recipe_json": json.dumps(extraction, ensure_ascii=True)},
        )
        substitutions = _call_gemini_json(
            "substitutions.txt",
            {"recipe_json": json.dumps({**extraction, **nutrition}, ensure_ascii=True)},
        )
    except LLMUnavailable:
        return None

    return {
        "recipe": extraction,
        "nutrition": nutrition.get("nutrition_estimate", nutrition),
        "shopping_list": nutrition.get("shopping_list", {}),
        "related_recipes": nutrition.get("related_recipes", []),
        "substitutions": substitutions.get("substitutions", []),
        "raw": {
            "recipe_extraction": extraction,
            "nutrition_estimation": nutrition,
            "substitutions": substitutions,
        },
    }


def generate_meal_plan_with_llm(recipes_json: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not settings.use_llm or not settings.google_api_key:
        return None
    try:
        return _call_gemini_json(
            "meal_planner.txt",
            {"recipes_json": json.dumps(recipes_json, ensure_ascii=True)},
        )
    except LLMUnavailable:
        return None


def _call_gemini_json(template_name: str, values: dict[str, Any]) -> dict[str, Any]:
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:
        raise LLMUnavailable("LangChain Gemini dependencies are not installed.") from exc

    prompt = ChatPromptTemplate.from_template(_read_prompt(template_name))
    model = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.1,
    )
    response = (prompt | model).invoke(values)
    content = getattr(response, "content", str(response))
    return extract_json_object(content)


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise LLMUnavailable("LLM did not return valid JSON.")


def _read_prompt(template_name: str) -> str:
    path = settings.prompts_dir / template_name
    return path.read_text(encoding="utf-8")
