"""
AgriVision - AI Analyzer Module
Multi-engine agricultural damage detection and conversational farmer assistant.
Primary Engine: NVIDIA Nemotron-3 Nano Omni Reasoning Vision (via integrate.api.nvidia.com)
Secondary Engine: Moonshot AI Kimi-k3
Fallback Engine: Google Gemini (gemini-3.5-flash-lite / gemini-3.8-flash)
"""

import os
import io
import json
import re
import base64
from typing import Dict, Any, List, Optional, Union
from PIL import Image
import requests
from dotenv import load_dotenv

from prompts import (
    AGRIVISION_SYSTEM_PROMPT,
    IMAGE_ANALYSIS_PROMPT,
    FOLLOW_UP_SYSTEM_PROMPT,
    GENERAL_AGRONOMY_SYSTEM_PROMPT
)

load_dotenv()

NVIDIA_INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_PRIMARY_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
NVIDIA_BACKUP_MODEL = "moonshotai/kimi-k3"


def get_nvidia_api_key() -> Optional[str]:
    """Retrieves the NVIDIA API key from env or Streamlit secrets."""
    key = os.environ.get("NVIDIA_API_KEY")
    if key and key != "your-nvidia-api-key-here":
        return key

    secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            import toml
            secrets = toml.load(secrets_path)
            tok = secrets.get("NVIDIA_API_KEY")
            if tok and tok != "your-nvidia-api-key-here":
                return tok
        except Exception:
            pass

    return None


def get_nvidia_backup_key() -> Optional[str]:
    """Retrieves backup NVIDIA API key."""
    key = os.environ.get("NVIDIA_BACKUP_API_KEY")
    if key and key != "your-nvidia-api-key-here":
        return key
    secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            import toml
            secrets = toml.load(secrets_path)
            tok = secrets.get("NVIDIA_BACKUP_API_KEY")
            if tok and tok != "your-nvidia-api-key-here":
                return tok
        except Exception:
            pass
    return None


def get_gemini_api_key() -> Optional[str]:
    """Retrieves the Gemini API key from env or Streamlit secrets."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key and key != "your-gemini-api-key-here":
        return key

    secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            import toml
            secrets = toml.load(secrets_path)
            tok = secrets.get("GEMINI_API_KEY") or secrets.get("GOOGLE_API_KEY")
            if tok and tok != "your-gemini-api-key-here":
                return tok
        except Exception:
            pass
    return None


def _clean_and_parse_json(text: str) -> Dict[str, Any]:
    """Parses raw LLM response text into a valid JSON dictionary with safe defaults."""
    cleaned = text.strip()

    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    try:
        data = json.loads(cleaned)
    except Exception:
        data = {}

    defaults = {
        "crop_identified": "Unknown",
        "damage_detected": False,
        "possible_damage_types": ["Unknown/uncertain"],
        "possible_cause": "Visual evidence is inconclusive.",
        "severity": "None",
        "estimated_visible_damage_percentage": "Not estimated",
        "affected_regions": ["General foliage"],
        "visible_symptoms": ["No prominent damage detected"],
        "confidence": "Medium",
        "recommended_next_steps": [
            "Inspect physical symptoms on the leaf undersides and stem.",
            "Maintain regular watering and avoid excessive moisture on leaves.",
            "Consult with local agricultural extension officers (e.g., Krishi Bhavan / KVK)."
        ],
        "limitations": [
            "2D photographic screening cannot test root/soil chemistry or microscopic pathogens."
        ]
    }

    for key, val in defaults.items():
        if key not in data or data[key] is None or (isinstance(data[key], list) and len(data[key]) == 0):
            data[key] = val

    return data


def _prepare_base64_data_url(image_input: Union[str, bytes, Image.Image]) -> str:
    """Converts image input to a base64 data URL string."""
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

    if max(pil_img.size) > 1600:
        pil_img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def _call_nvidia_api(
    messages: List[Dict[str, Any]],
    model: str = NVIDIA_PRIMARY_MODEL,
    api_key: Optional[str] = None,
    timeout: int = 35,
    max_tokens: int = 2048
) -> str:
    """Calls NVIDIA chat completion endpoint."""
    key = api_key or get_nvidia_api_key()
    if not key:
        raise ValueError("NVIDIA API Key not configured.")

    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens
    }

    response = requests.post(NVIDIA_INVOKE_URL, headers=headers, json=payload, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"NVIDIA API Error {response.status_code}: {response.text}")

    data = response.json()
    return data["choices"][0]["message"]["content"]


def analyze_crop_image(
    image_input: Union[str, bytes, Image.Image],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyzes a crop image for damage, symptoms, and severity.
    Uses NVIDIA Nemotron Vision as primary engine with automatic Gemini fallback.
    """
    data_url = _prepare_base64_data_url(image_input)

    prompt_text = (
        AGRIVISION_SYSTEM_PROMPT + "\n\n" + IMAGE_ANALYSIS_PROMPT +
        "\n\nIMPORTANT: Respond ONLY with a valid JSON object matching the requested schema. No other text or markdown fences."
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]
        }
    ]

    # 1. Try NVIDIA Nemotron Reasoning Vision
    nv_key = api_key or get_nvidia_api_key()
    if nv_key:
        try:
            content = _call_nvidia_api(messages, model=NVIDIA_PRIMARY_MODEL, api_key=nv_key, timeout=30)
            if content:
                return _clean_and_parse_json(content)
        except Exception as e:
            # Try backup key if available
            backup_key = get_nvidia_backup_key()
            if backup_key:
                try:
                    content = _call_nvidia_api(messages, model=NVIDIA_BACKUP_MODEL, api_key=backup_key, timeout=30)
                    if content:
                        return _clean_and_parse_json(content)
                except Exception:
                    pass

    # 2. Fallback to Gemini if NVIDIA fails
    gemini_key = get_gemini_api_key()
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            if isinstance(image_input, (str, bytes)):
                pil_img = Image.open(image_input if isinstance(image_input, str) else io.BytesIO(image_input))
            else:
                pil_img = image_input

            for model_name in ["gemini-3.5-flash-lite", "gemini-3.8-flash"]:
                try:
                    res = client.models.generate_content(
                        model=model_name,
                        contents=[pil_img, prompt_text]
                    )
                    if res and res.text:
                        return _clean_and_parse_json(res.text)
                except Exception:
                    continue
        except Exception:
            pass

    raise RuntimeError("Crop damage vision analysis failed across all AI services. Please verify your internet connection or API keys.")


def answer_follow_up(
    analysis_context: Dict[str, Any],
    user_question: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    api_key: Optional[str] = None
) -> str:
    """Answers a farmer's follow-up question regarding their recent crop analysis."""
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

    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_question})

    # 1. Try NVIDIA Nemotron
    nv_key = api_key or get_nvidia_api_key()
    if nv_key:
        try:
            return _call_nvidia_api(messages, model=NVIDIA_PRIMARY_MODEL, api_key=nv_key, timeout=20)
        except Exception:
            backup_key = get_nvidia_backup_key()
            if backup_key:
                try:
                    return _call_nvidia_api(messages, model=NVIDIA_BACKUP_MODEL, api_key=backup_key, timeout=20)
                except Exception:
                    pass

    # 2. Fallback to Gemini
    gemini_key = get_gemini_api_key()
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            full_prompt = system_prompt + "\n\n"
            if chat_history:
                for msg in chat_history[-6:]:
                    full_prompt += f"{msg['role']}: {msg['content']}\n"
            full_prompt += f"User: {user_question}\nAssistant:"
            res = client.models.generate_content(model="gemini-3.5-flash-lite", contents=full_prompt)
            if res and res.text:
                return res.text.strip()
        except Exception:
            pass

    return "⚠️ AgriVision Assistant is currently unable to answer. Please try again shortly."


def answer_general_question(
    user_question: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    api_key: Optional[str] = None
) -> str:
    """Answers general agricultural and agronomy questions from farmers directly via text."""
    messages = [{"role": "system", "content": GENERAL_AGRONOMY_SYSTEM_PROMPT}]
    if chat_history:
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_question})

    # 1. Try NVIDIA Nemotron
    nv_key = api_key or get_nvidia_api_key()
    if nv_key:
        try:
            return _call_nvidia_api(messages, model=NVIDIA_PRIMARY_MODEL, api_key=nv_key, timeout=20)
        except Exception:
            backup_key = get_nvidia_backup_key()
            if backup_key:
                try:
                    return _call_nvidia_api(messages, model=NVIDIA_BACKUP_MODEL, api_key=backup_key, timeout=20)
                except Exception:
                    pass

    # 2. Fallback to Gemini
    gemini_key = get_gemini_api_key()
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            full_prompt = GENERAL_AGRONOMY_SYSTEM_PROMPT + "\n\n"
            if chat_history:
                for msg in chat_history[-6:]:
                    full_prompt += f"{msg['role']}: {msg['content']}\n"
            full_prompt += f"User: {user_question}\nAssistant:"
            res = client.models.generate_content(model="gemini-3.5-flash-lite", contents=full_prompt)
            if res and res.text:
                return res.text.strip()
        except Exception:
            pass

    return "⚠️ AgriVision Assistant is currently unable to answer. Please check your network connection or try again shortly."
