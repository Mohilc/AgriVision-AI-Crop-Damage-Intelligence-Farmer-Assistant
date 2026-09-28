"""
AgriVision - AI Analyzer Module
Handles crop image analysis and follow-up Q&A using Google GenAI Interactions API.
"""

import os
import io
import json
import re
import base64
from typing import Dict, Any, List, Optional, Union
from PIL import Image
from dotenv import load_dotenv
from google import genai

from prompts import (
    AGRIVISION_SYSTEM_PROMPT,
    IMAGE_ANALYSIS_PROMPT,
    FOLLOW_UP_SYSTEM_PROMPT
)

load_dotenv()

MODEL = "gemini-3.8-flash"


def get_gemini_api_key() -> Optional[str]:
    """Retrieves the Gemini API key from env or Streamlit secrets."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key and api_key != "your-gemini-api-key-here":
        return api_key

    secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            import toml
            secrets = toml.load(secrets_path)
            key = secrets.get("GEMINI_API_KEY") or secrets.get("GOOGLE_API_KEY")
            if key and key != "your-gemini-api-key-here":
                return key
        except Exception:
            pass

    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            key = st.secrets["GEMINI_API_KEY"]
            if key and key != "your-gemini-api-key-here":
                return key
    except Exception:
        pass

    return None


def _get_client(api_key: Optional[str] = None) -> genai.Client:
    """Returns a configured GenAI client."""
    key = api_key or get_gemini_api_key()
    if not key:
        raise ValueError("Gemini API key not found. Set GEMINI_API_KEY in .streamlit/secrets.toml or .env")
    return genai.Client(api_key=key)


def _clean_and_parse_json(text: str) -> Dict[str, Any]:
    """Parses raw LLM response text into a valid JSON dictionary."""
    cleaned = text.strip()

    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    data = json.loads(cleaned)

    defaults = {
        "crop_identified": "Unknown",
        "damage_detected": False,
        "possible_damage_types": ["Unknown/uncertain"],
        "possible_cause": "Uncertain — image evidence is insufficient.",
        "severity": "None",
        "estimated_visible_damage_percentage": "Not estimated",
        "affected_regions": ["Entire frame"],
        "visible_symptoms": ["Insufficient visual indicators"],
        "confidence": "Low",
        "recommended_next_steps": [
            "Capture a clearer, well-lit close-up photograph.",
            "Inspect physical symptoms on the leaf undersides and stem.",
            "Consult with local agricultural extension officers (e.g., Krishi Bhavan)."
        ],
        "limitations": [
            "2D image assessment cannot analyze soil chemistry or microscopic pathogens."
        ]
    }

    for key, val in defaults.items():
        if key not in data or data[key] is None or (isinstance(data[key], list) and len(data[key]) == 0):
            data[key] = val

    return data


def _image_to_base64(image_input: Union[str, bytes, Image.Image]) -> str:
    """Converts any image input to a base64 encoded JPEG string."""
    if isinstance(image_input, str):
        if not os.path.exists(image_input):
            raise FileNotFoundError(f"Image not found: {image_input}")
        pil_img = Image.open(image_input)
    elif isinstance(image_input, bytes):
        pil_img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, Image.Image):
        pil_img = image_input
    else:
        raise ValueError("Invalid image input. Must be file path, bytes, or PIL.Image.")

    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    if max(pil_img.size) > 2048:
        pil_img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=85)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def analyze_crop_image(
    image_input: Union[str, bytes, Image.Image],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Analyzes a crop image using Gemini Vision. Returns structured damage data."""
    client = _get_client(api_key)
    b64_image = _image_to_base64(image_input)

    prompt_text = (
        AGRIVISION_SYSTEM_PROMPT + "\n\n" + IMAGE_ANALYSIS_PROMPT +
        "\n\nIMPORTANT: Respond ONLY with a valid JSON object. No markdown fences, no extra text."
    )

    response = client.interactions.create(
        model=MODEL,
        input=[
            {"type": "image", "data": b64_image, "mime_type": "image/jpeg"},
            {"type": "text", "text": prompt_text}
        ]
    )

    return _clean_and_parse_json(response.output_text)


def answer_follow_up(
    analysis_context: Dict[str, Any],
    user_question: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    api_key: Optional[str] = None
) -> str:
    """Answers a farmer's follow-up question based on previous crop analysis."""
    try:
        client = _get_client(api_key)
    except ValueError:
        return "⚠️ Gemini API key is missing. Please configure your GEMINI_API_KEY."

    system_prompt = FOLLOW_UP_SYSTEM_PROMPT.format(
        crop_identified=analysis_context.get("crop_identified", "Unknown"),
        damage_detected="Yes" if analysis_context.get("damage_detected") else "No",
        possible_cause=analysis_context.get("possible_cause", "Uncertain"),
        severity=analysis_context.get("severity", "None"),
        estimated_damage=analysis_context.get("estimated_visible_damage_percentage", "Not estimated"),
        symptoms=", ".join(analysis_context.get("visible_symptoms", [])),
        affected_regions=", ".join(analysis_context.get("affected_regions", [])),
        recommended_steps="; ".join(analysis_context.get("recommended_next_steps", [])),
        limitations="; ".join(analysis_context.get("limitations", []))
    )

    prompt = system_prompt + "\n\n"
    if chat_history:
        for msg in chat_history[-6:]:
            role = "Farmer" if msg["role"] == "user" else "AgriVision"
            prompt += f"{role}: {msg['content']}\n"

    prompt += f"Farmer Question: {user_question}\nAgriVision Answer:"

    try:
        response = client.interactions.create(
            model=MODEL,
            input=prompt
        )
        return response.output_text.strip()
    except Exception as e:
        return f"⚠️ Unable to answer at this moment: {str(e)}"
