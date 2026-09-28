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
    GENERAL_AGRONOMY_SYSTEM_PROMPT,
    CROP_DAMAGE_SOLUTION_AND_CONDITIONS_PROMPT
)

load_dotenv()

NVIDIA_INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_PRIMARY_MODEL = "meta/llama-3.2-11b-vision-instruct"
NVIDIA_SECONDARY_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
NVIDIA_BACKUP_MODEL = "moonshotai/kimi-k3"


def _get_secret_value(key_name: str) -> Optional[str]:
    """Retrieves secret value from os.environ, st.secrets, or local secrets.toml."""
    load_dotenv()
    val = os.environ.get(key_name)
    if val and len(val) > 15 and not val.startswith("your-"):
        return val

    # Try Streamlit runtime secrets if available in memory
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key_name in st.secrets:
            s_val = str(st.secrets[key_name])
            if s_val and len(s_val) > 15 and not s_val.startswith("your-"):
                return s_val
    except Exception:
        pass

    # Try .streamlit/secrets.toml
    secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            import toml
            secrets = toml.load(secrets_path)
            tok = secrets.get(key_name)
            if tok and len(str(tok)) > 15 and not str(tok).startswith("your-"):
                return str(tok)
        except Exception:
            pass

    return None


def get_nvidia_api_key() -> Optional[str]:
    """Retrieves the NVIDIA API key from env, Streamlit secrets, or secrets.toml."""
    return _get_secret_value("NVIDIA_API_KEY")


def get_nvidia_backup_key() -> Optional[str]:
    """Retrieves backup NVIDIA API key."""
    return _get_secret_value("NVIDIA_BACKUP_API_KEY")


def get_meta_llama_api_key() -> Optional[str]:
    """Retrieves dedicated Meta Llama API key, falling back to NVIDIA_API_KEY."""
    return _get_secret_value("META_LLAMA_API_KEY") or get_nvidia_api_key()


def get_kimi_api_key() -> Optional[str]:
    """Retrieves dedicated Kimi (Moonshot AI) API key, falling back to backup or primary key."""
    return _get_secret_value("KIMI_API_KEY") or get_nvidia_backup_key() or get_nvidia_api_key()


def get_nemotron_api_key() -> Optional[str]:
    """Retrieves dedicated Nemotron API key, falling back to NVIDIA_API_KEY."""
    return _get_secret_value("NEMOTRON_API_KEY") or get_nvidia_api_key()


def get_key_for_model(model: str) -> Optional[str]:
    """Resolves the appropriate API key for a given model."""
    if "llama" in model.lower():
        return get_meta_llama_api_key()
    elif "kimi" in model.lower():
        return get_kimi_api_key()
    elif "nemotron" in model.lower():
        return get_nemotron_api_key()
    return get_nvidia_api_key()


def get_gemini_api_key() -> Optional[str]:
    """Retrieves the Gemini API key from env, Streamlit secrets, or secrets.toml."""
    return _get_secret_value("GEMINI_API_KEY") or _get_secret_value("GOOGLE_API_KEY")



COMMON_CROPS_REGEX = re.compile(
    r'\b(rose|roses|tomato|tomatoes|potato|potatoes|maize|corn|rice|paddy|wheat|cotton|chili|chilli|chillies|chilis|pepper|peppers|soybean|soybeans|sugarcane|banana|bananas|apple|apples|mango|mangoes|citrus|lemon|lemons|onion|onions|garlic|grape|grapes|grapevine|cucumber|cucumbers|brinjal|eggplant|cabbage|cauliflower|mustard|peanut|peanuts|groundnut|groundnuts|coffee|tea|papaya|guava|watermelon|pomegranate|ginger|turmeric|pea|peas|bean|beans|ladyfinger|okra|marigold)\b',
    re.IGNORECASE
)


def _clean_and_parse_json(text: str) -> Dict[str, Any]:
    """Parses raw LLM response text into a valid JSON dictionary with safe defaults and robust key mapping."""
    raw_text = text.strip()
    cleaned = raw_text

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

    # If JSON parsing yielded an empty dict or failed, attempt Markdown key-value extraction
    if not data or not any(k in data for k in ["crop_identified", "damage_detected", "severity", "possible_cause"]):
        md_data = {}
        for line in raw_text.splitlines():
            line = line.strip()
            m = re.match(r'^(?:[*•\-\d.]+\s*)?\*?\*?([A-Za-z\s_-]+?)\*?\*?\s*:\s*(.+)$', line)
            if m:
                raw_k = m.group(1).strip().lower().replace(" ", "_").replace("-", "_")
                val = m.group(2).strip().strip("*_`")
                md_data[raw_k] = val
        if md_data:
            for mk, mv in md_data.items():
                if mk not in data or not data[mk]:
                    data[mk] = mv

    # Handle comma/semicolon-separated string lists
    for list_key in ["solutions_and_remedies", "recommended_next_steps", "visible_symptoms", "affected_regions", "possible_damage_types"]:
        if isinstance(data.get(list_key), str):
            val = data[list_key].strip()
            if "," in val or ";" in val:
                data[list_key] = [s.strip() for s in re.split(r'[,;]\s*', val) if s.strip()]
            else:
                data[list_key] = [val]

    # --- Robust Key Normalization & Mapping ---
    # 1. Severity
    sev = data.get("severity") or data.get("severity_classification") or data.get("severity_level")
    if not sev and isinstance(data.get("damage_categories"), list) and len(data["damage_categories"]) > 0:
        first_cat = data["damage_categories"][0]
        if isinstance(first_cat, dict) and first_cat.get("severity"):
            sev = first_cat.get("severity")
    if sev and isinstance(sev, str):
        sev_clean = sev.strip().capitalize()
        if any(s in sev_clean for s in ["Severe", "Critical"]):
            data["severity"] = "Severe"
        elif any(s in sev_clean for s in ["High"]):
            data["severity"] = "High"
        elif any(s in sev_clean for s in ["Moderate", "Medium"]):
            data["severity"] = "Moderate"
        elif any(s in sev_clean for s in ["Low", "Minor"]):
            data["severity"] = "Low"
        elif any(s in sev_clean for s in ["None", "Healthy"]):
            data["severity"] = "None"
        else:
            data["severity"] = sev_clean

    # 2. Estimated damage percentage
    est_dmg = (
        data.get("estimated_visible_damage_percentage") or
        data.get("estimated_damage_percentage") or
        data.get("damage_percentage") or
        data.get("visible_damage_percentage")
    )
    if est_dmg:
        data["estimated_visible_damage_percentage"] = str(est_dmg).strip()

    # 3. Affected regions
    regions = (
        data.get("affected_regions") or
        data.get("high_damage_zones") or
        data.get("affected_zones") or
        data.get("damage_zones")
    )
    if isinstance(regions, list) and regions:
        data["affected_regions"] = [str(r).strip() for r in regions]
    elif isinstance(regions, str) and regions.strip():
        data["affected_regions"] = [regions.strip()]

    # 4. Visible symptoms
    symptoms = (
        data.get("visible_symptoms") or
        data.get("visual_symptoms") or
        data.get("symptoms")
    )
    if isinstance(symptoms, list) and symptoms:
        data["visible_symptoms"] = [str(s).strip() for s in symptoms]
    elif isinstance(symptoms, str) and symptoms.strip():
        data["visible_symptoms"] = [symptoms.strip()]
    elif isinstance(data.get("damage_categories"), list):
        extracted_sym = []
        for cat in data["damage_categories"]:
            if isinstance(cat, dict) and cat.get("visual_evidence"):
                extracted_sym.append(cat["visual_evidence"])
        if extracted_sym:
            data["visible_symptoms"] = extracted_sym

    # 5. Possible cause / description
    cause = (
        data.get("possible_cause") or
        data.get("likely_cause") or
        data.get("cause")
    )
    if not cause or cause in ["Visual evidence is inconclusive.", "Uncertain — image evidence is insufficient."]:
        farmer_rep = data.get("farmer_friendly_report")
        if isinstance(farmer_rep, dict) and farmer_rep.get("summary"):
            cause = farmer_rep.get("summary")
        elif data.get("primary_observation"):
            cause = data.get("primary_observation")
    if cause:
        data["possible_cause"] = str(cause).strip()

    # 6. Recommended next steps
    steps = (
        data.get("recommended_next_steps") or
        data.get("next_steps") or
        data.get("actionable_next_steps")
    )
    if not steps:
        farmer_rep = data.get("farmer_friendly_report")
        if isinstance(farmer_rep, dict) and farmer_rep.get("immediate_actions"):
            steps = farmer_rep.get("immediate_actions")
    if isinstance(steps, list) and steps:
        data["recommended_next_steps"] = [str(st).strip() for st in steps]

    # 7. Crop identified
    crop = (
        data.get("crop_identified") or
        data.get("crop_name") or
        data.get("crop") or
        data.get("plant_name") or
        data.get("plant")
    )
    # Check if crop is unspecified or "Unknown"
    is_unknown_crop = not crop or str(crop).strip().lower() in ["unknown", "none", "unidentified", "uncertain", "not identified"]
    if is_unknown_crop:
        # Search the text, primary_observation, possible_cause for known crop names
        search_blob = f"{raw_text} {data.get('possible_cause', '')} {data.get('primary_observation', '')}"
        crop_match = COMMON_CROPS_REGEX.search(search_blob)
        if crop_match:
            detected_crop = crop_match.group(1).title()
            if detected_crop.endswith("es") and detected_crop not in ["Roses"]:
                detected_crop = detected_crop[:-2]
            elif detected_crop.endswith("s") and detected_crop not in ["Citrus"]:
                detected_crop = detected_crop[:-1]
            data["crop_identified"] = detected_crop
        else:
            data["crop_identified"] = "Unknown"
    else:
        data["crop_identified"] = str(crop).strip().title()

    # 8. Damage detected flag
    if "damage_detected" not in data or data["damage_detected"] is None:
        if data.get("severity") in ["Low", "Moderate", "High", "Severe"]:
            data["damage_detected"] = True
        elif data.get("possible_cause") and data["possible_cause"] not in ["Visual evidence is inconclusive.", "Uncertain — image evidence is insufficient."]:
            data["damage_detected"] = True
        else:
            data["damage_detected"] = False
    elif isinstance(data["damage_detected"], str):
        val_lower = data["damage_detected"].lower()
        if any(w in val_lower for w in ["yes", "true", "disease", "pest", "spot", "fungal", "damage", "blight", "rot", "detected"]):
            data["damage_detected"] = True
        elif any(w in val_lower for w in ["no", "false", "none", "healthy"]):
            data["damage_detected"] = False
        else:
            data["damage_detected"] = True

    # 9. Conditions favoring damage
    cond = (
        data.get("conditions_favoring_damage") or
        data.get("favorable_conditions") or
        data.get("damage_conditions") or
        data.get("conditions")
    )
    if cond:
        data["conditions_favoring_damage"] = str(cond).strip()

    # 10. Solutions and remedies
    sol = (
        data.get("solutions_and_remedies") or
        data.get("remedies") or
        data.get("solutions") or
        data.get("practical_remedies")
    )
    if isinstance(sol, list) and sol:
        data["solutions_and_remedies"] = [str(s).strip() for s in sol]
    elif isinstance(sol, str) and sol.strip():
        data["solutions_and_remedies"] = [sol.strip()]

    defaults = {
        "crop_identified": "Unknown",
        "damage_detected": False,
        "possible_damage_types": ["Unknown/uncertain"],
        "possible_cause": "Visual evidence is inconclusive.",
        "conditions_favoring_damage": "Foliage moisture, prolonged humidity, and moderate-to-warm temperatures.",
        "solutions_and_remedies": [
            "Prune and discard infected leaves immediately.",
            "Water at the root zone; avoid wetting foliage.",
            "Apply safe organic bio-fungicide or neem oil spray."
        ],
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
    timeout: int = 45,
    max_tokens: int = 2048
) -> str:
    """Calls NVIDIA chat completion endpoint."""
    key = api_key or get_key_for_model(model)
    if not key:
        raise ValueError(f"API Key for model '{model}' not configured.")

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

    prompt_text = """You are AgriVision, an expert agricultural plant pathologist and agronomist. Analyze this crop photograph for visible damage, disease, pests, environmental stress, and symptoms.

Strictly return a JSON object with:
{
  "crop_identified": "Common name of crop or plant (e.g. Rose, Tomato, Wheat, Cotton, Rice, Chilli, or 'Unknown')",
  "damage_detected": true or false,
  "possible_damage_types": ["Disease", "Pest", "Weather", "Flood/waterlogging", or "Unknown/uncertain"],
  "possible_cause": "Specific disease or pest name and cause (e.g. Black Spot / Diplocarpon rosae fungal infection)",
  "conditions_favoring_damage": "Favorable environmental conditions causing this damage (e.g. High humidity >80%, extended leaf wetness, warm temperatures, poor aeration)",
  "solutions_and_remedies": [
    "Prune and safely destroy infected foliage to prevent spore spread",
    "Water at the root base in morning; avoid wetting leaves",
    "Apply safe organic bio-fungicide (e.g. neem oil spray 0.5% or Trichoderma) or copper-based spray"
  ],
  "severity": "None, Low, Moderate, High, or Severe",
  "estimated_visible_damage_percentage": "approximate percentage range (e.g. 20-30%)",
  "affected_regions": ["localized area (e.g. Central canopy leaves, Lower foliage)"],
  "visible_symptoms": ["symptom 1", "symptom 2"],
  "confidence": "Low, Medium, or High",
  "recommended_next_steps": ["step 1", "step 2", "step 3"],
  "limitations": ["2D photograph screening cannot inspect root/soil chemistry"]
}
IMPORTANT: Only output the JSON object, nothing else."""

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]
        }
    ]

    # 1. Try NVIDIA Models: Primary (Llama 3.2 11B Vision), Secondary (Nemotron), Backup (Moonshot Kimi)
    nv_key = api_key or get_nvidia_api_key()
    if nv_key:
        for model in [NVIDIA_PRIMARY_MODEL, NVIDIA_SECONDARY_MODEL, NVIDIA_BACKUP_MODEL]:
            try:
                content = _call_nvidia_api(messages, model=model, api_key=nv_key, timeout=45)
                if content:
                    return _clean_and_parse_json(content)
            except Exception:
                continue

        backup_key = get_nvidia_backup_key()
        if backup_key:
            for model in [NVIDIA_PRIMARY_MODEL, NVIDIA_SECONDARY_MODEL, NVIDIA_BACKUP_MODEL]:
                try:
                    content = _call_nvidia_api(messages, model=model, api_key=backup_key, timeout=45)
                    if content:
                        return _clean_and_parse_json(content)
                except Exception:
                    continue

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


def extract_crop_name(user_text: str) -> Optional[str]:
    """
    Extracts a crop or plant name if the user's text indicates they are specifying or clarifying a crop.
    Examples:
      - 'Rose' -> 'Rose'
      - 'It is a rose plant' -> 'Rose'
      - 'My crop is tomato' -> 'Tomato'
      - 'Cotton' -> 'Cotton'
      - 'The plant is chilli' -> 'Chilli'
    """
    cleaned = user_text.strip().strip(".!?,")
    if not cleaned:
        return None

    # Check for direct regex match of common crops first
    match = COMMON_CROPS_REGEX.search(cleaned)
    if match:
        crop_word = match.group(1).title()
        if crop_word.endswith("es") and crop_word not in ["Roses"]:
            crop_word = crop_word[:-2]
        elif crop_word.endswith("s") and crop_word not in ["Citrus"]:
            crop_word = crop_word[:-1]
        return crop_word

    # Check for phrases like "crop is X", "plant is X", "it is X", "it's X", "this is X"
    phrase_match = re.search(
        r'^(?:my\s+)?(?:crop|plant|flower|tree|vegetable)?\s*(?:is|name\s+is|it\s+is|it\'s|this\s+is)\s+([a-zA-Z\s]{2,25})$',
        cleaned,
        re.IGNORECASE
    )
    if phrase_match:
        cand = phrase_match.group(1).strip().title()
        if cand.lower() not in ["hello", "help", "hi", "yes", "no", "thanks", "thank you", "why", "what"]:
            return cand

    STOPWORDS_AND_QUESTIONS = {
        "what", "why", "how", "when", "who", "where", "which", "is", "are", "was", "were",
        "this", "that", "these", "those", "can", "could", "would", "should", "tell", "please",
        "help", "advice", "photo", "image", "pic", "scan", "check", "inspect", "disease",
        "problem", "damage", "symptom", "remedy", "cure", "spray", "medicine", "chemical",
        "fertilizer", "water", "irrigation", "soil", "leaf", "leaves", "stem", "root",
        "hello", "hi", "hey", "yes", "no", "thanks", "thank", "you", "ok", "okay",
        "report", "start", "stop", "guide", "menu"
    }

    # If the user input is very short (1 to 3 words) and letters only, likely a crop name
    words = cleaned.lower().split()
    if 1 <= len(words) <= 3 and all(w.isalpha() for w in words):
        if not any(w in STOPWORDS_AND_QUESTIONS for w in words):
            return cleaned.title()

    return None


def generate_crop_damage_solution_and_conditions(
    crop_name: str,
    analysis_context: Dict[str, Any],
    api_key: Optional[str] = None
) -> str:
    """
    Generates a structured agronomic report detailing:
    1. Problem and confirmed crop
    2. Conditions under which the damage occurs (environmental, watering, humidity, soil, vectors)
    3. Tailored remedies and practical solutions (cultural, organic, biological, agronomic)
    """
    symptoms = analysis_context.get("visible_symptoms", [])
    symptoms_str = ", ".join(symptoms) if isinstance(symptoms, list) else str(symptoms)

    regions = analysis_context.get("affected_regions", [])
    regions_str = ", ".join(regions) if isinstance(regions, list) else str(regions)

    prompt = CROP_DAMAGE_SOLUTION_AND_CONDITIONS_PROMPT.format(
        crop_name=crop_name,
        symptoms=symptoms_str or "Visible foliar lesions, spots, or discoloration",
        affected_regions=regions_str or "Canopy foliage",
        severity=analysis_context.get("severity", "Moderate"),
        estimated_damage=analysis_context.get("estimated_visible_damage_percentage", "Not estimated"),
        possible_cause=analysis_context.get("possible_cause", "Observed leaf damage and stress symptoms")
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"The crop has been confirmed as {crop_name}. Please provide the specific conditions causing this damage and actionable remedies."}
    ]

    # 1. Try NVIDIA Nemotron
    nv_key = api_key or get_nvidia_api_key()
    if nv_key:
        try:
            return _call_nvidia_api(messages, model=NVIDIA_PRIMARY_MODEL, api_key=nv_key, timeout=30)
        except Exception:
            backup_key = get_nvidia_backup_key()
            if backup_key:
                try:
                    return _call_nvidia_api(messages, model=NVIDIA_BACKUP_MODEL, api_key=backup_key, timeout=30)
                except Exception:
                    pass

    # 2. Fallback to Gemini
    gemini_key = get_gemini_api_key()
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            full_prompt = prompt + f"\n\nThe crop has been confirmed as {crop_name}. Please provide the specific conditions causing this damage and actionable remedies."
            res = client.models.generate_content(model="gemini-3.5-flash-lite", contents=full_prompt)
            if res and res.text:
                return res.text.strip()
        except Exception:
            pass

    return (
        f"🌿 **Confirmed Crop: {crop_name}**\n\n"
        f"🌧️ **Conditions Favoring Damage:**\n"
        f"• Extended leaf moisture and high ambient humidity (>80%).\n"
        f"• Moderate to warm temperatures (20°C–30°C).\n"
        f"• Dense canopy with limited sunlight penetration and stagnant airflow.\n\n"
        f"🛠️ **Recommended Remedies for {crop_name}:**\n"
        f"• Prune and safely destroy infected foliage to prevent spore spread.\n"
        f"• Irrigate at root base in early morning; avoid wetting foliage.\n"
        f"• Apply organic bio-fungicide (e.g. Neem oil spray 0.5% or Trichoderma) or copper-based protectant.\n"
        f"• Consult local agricultural officer (Krishi Bhavan / KVK) for regional guidance."
    )
