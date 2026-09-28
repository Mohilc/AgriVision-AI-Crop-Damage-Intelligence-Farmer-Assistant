# 🌱 AgriVision — AI-Based Crop Damage Detection, Quantification & Farmer Reporting System

> **Practical, accessible, and farmer-centric AI technology addressing agricultural crop loss, early damage detection, and structured reporting.**

---

## 📌 Problem Statement

Farmers frequently encounter devastating crop losses from plant diseases, pest outbreaks, wild animal intrusions, extreme weather events, and flood waterlogging. 

However, smallholder farmers often lack immediate access to agricultural experts to assess:
1. What the visible damage actually is.
2. How severe the loss is across their field.
3. What immediate cultural or field-inspection steps should be taken.

Furthermore, farmers need a simple, zero-friction interface (such as **Telegram**) to send a field photo and receive an understandable assessment report without complex software installations.

---

## 🌾 The 8 Core Agricultural Challenges Addressed

1. **Crop Disease Damage Detection:** Identifies fungal leaf spots, blights, rusts, and viral chlorosis.
2. **Pest-Related Damage Detection:** Identifies chewing holes, defoliation, leaf-miner trails, and insect presence.
3. **Wild Animal Intrusion Assessment:** Recognizes physical trampling, stem snapping, and crop grazing.
4. **Weather Damage Assessment:** Identifies hail tears, frost scorch, wind lodging, and heat stress.
5. **Flood & Waterlogging Assessment:** Flags submersion symptoms, root asphyxiation chlorosis, and silt accumulation.
6. **Damage Severity & Percentage Estimation:** Provides cautious, visual percentage ranges (e.g., *20–30%*) without false scientific certainty.
7. **Localized Damage Zone Identification:** Highlights specific image sectors (e.g., *lower-left canopy*, *stem base*).
8. **Farmer-Friendly Structured Reporting:** Generates clean Telegram summaries and downloadable **PDF Assessment Reports**.

---

## 🏛️ System Architecture

```
                                  ┌─────────────────────────────┐
                                  │   Farmer (Telegram App)     │
                                  └──────────────┬──────────────┘
                                                 │ 📸 Sends Crop Photo / Follow-up Qs
                                                 ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│ Streamlit Web Dashboard     │   │ telegram_bot.py             │
│ (Desktop / Evaluator Bench) │   │ (Async Telegram Bot Engine) │
└──────────────┬──────────────┘   └──────────────┬──────────────┘
               │                                 │
               └────────────────┬────────────────┘
                                │
                                ▼
                  ┌───────────────────────────┐
                  │ ai_analyzer.py            │
                  │ (Google Gemini Vision API)│
                  └─────────────┬─────────────┘
                                │ Structured JSON Assessment
                                ▼
         ┌──────────────────────┴──────────────────────┐
         ▼                                             ▼
┌─────────────────────────────┐               ┌─────────────────────────────┐
│ database.py                 │               │ report_generator.py         │
│ (SQLite Persistence Layer)  │               │ (Telegram Text & PDF Engine)│
└─────────────────────────────┘               └─────────────────────────────┘
```

---

## 🛠️ Technology Stack

- **AI Vision Engine:** Google Gemini 2.5 Flash / 1.5 Flash Vision Multimodal API
- **Messaging Interface:** Python Telegram Bot API (`python-telegram-bot` async)
- **Web Dashboard:** Streamlit 1.35+
- **Database:** SQLite with thread-safe queries
- **Image Processing:** Pillow (PIL), OpenCV
- **Reporting Engine:** ReportLab PDF Builder

---

## 📁 Project Structure

```
agrivision/
│
├── app.py                      # Streamlit admin & evaluator web dashboard
├── telegram_bot.py             # Telegram Bot engine with conversational follow-up
├── ai_analyzer.py              # Gemini Vision multimodal parser & chat reasoning
├── prompts.py                  # Structured prompts, system instructions & JSON schema
├── database.py                 # SQLite CRUD, schema migration, and analytics queries
├── report_generator.py         # Formats farmer-friendly Telegram reports & PDF exports
├── requirements.txt            # Python dependencies
├── README.md                   # Full documentation & setup guide
├── .gitignore                  # Git ignore file
│
├── .streamlit/
│   ├── config.toml             # Streamlit visual theme styling
│   └── secrets.toml.example    # Configuration template for API keys
│
└── data/
    ├── agrivision.db           # SQLite database (created automatically)
    └── uploads/                # Cached crop photos (created automatically)
```

---

## 🔑 Setup & Installation

### 1. Clone & Activate Virtual Environment

```bash
cd agrivision
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Secrets

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` or create a `.env` file with your credentials:

```toml
GEMINI_API_KEY = "AIzaSy..."
TELEGRAM_BOT_TOKEN = "123456789:ABCdef..."
```

> **How to get keys:**
> - **Gemini API Key:** Get free from [Google AI Studio](https://aistudio.google.com/).
> - **Telegram Bot Token:** Message `@BotFather` on Telegram, send `/newbot`, and copy the token.

---

## 🚀 Running AgriVision

### 1. Run the Telegram Bot (For Farmers)

```bash
python telegram_bot.py
```

Open Telegram, search for your bot, and send `/start` or upload any crop photo.

### 2. Run the Streamlit Dashboard (For Evaluators & Field Admins)

```bash
streamlit run app.py
```

The web dashboard opens at `http://localhost:8501`.

---

## 📱 Telegram Commands & Usage

| Command | Action |
|---|---|
| `/start` | Introduces AgriVision and its visual screening capabilities |
| `/help` | Photography best practices and guide on follow-up questions |
| `/analyze` | Prompts user to upload a crop photograph |
| `/history` | Displays recent inspection records |
| `/report` | Delivers the detailed assessment and official PDF report |
| `[Photo Upload]` | Automatically runs vision analysis and returns structured damage screening |
| `[Text Message]` | Follow-up conversational reasoning (e.g. *"What is the possible problem?"*, *"Will this spread?"*) |

---

## 📊 Database Schema (SQLite)

- **`analyses`**: Stores `id`, `telegram_user_id`, `crop_identified`, `damage_detected`, `possible_damage_types`, `possible_cause`, `severity`, `estimated_visible_damage_percentage`, `affected_regions`, `visible_symptoms`, `confidence`, `recommended_next_steps`, `limitations`, `image_path`, `timestamp`, `source`.
- **`chat_messages`**: Stores multi-turn conversational follow-up memory linked to each analysis.

---

## ⚠️ Limitations & Responsible AI Guidelines

1. **Initial Screening Tool:** AgriVision is designed as an accessible screening tool, not a replacement for an agronomist.
2. **Visual Estimates Only:** Percentages are visual approximations (e.g. 20–30%) from 2D photos, not calibrated sensor measurements.
3. **No Unsafe Prescriptions:** The system strictly advises safe cultural inspections and official extension officer consultations rather than unverified chemical mixes.

---

## 🔮 Future Roadmap

- 🚁 **Drone-Based Aerial Surveys:** Ingesting stitched orthomosaic farm field maps.
- 📍 **GPS Geo-tagging & Heatmaps:** Mapping cluster outbreaks across panchayats.
- 🔬 **Edge Vision (YOLO/TFLite):** Offline on-device pest localization for remote rural zones.
- 🗣️ **Regional Language Support:** Native Malayalam and regional language voice interactions.
- 📡 **IoT Soil Sensor Fusion:** Correlating visual leaf stress with live soil NPK and moisture telemetry.

---

## 📜 License
Developed for open agritech innovation, agricultural education, and research.
