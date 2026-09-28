# 🌱 AgriVision — AI-Powered Crop Damage Detection, Quantification & Farmer Intelligence Assistant

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit 1.40+](https://img.shields.io/badge/Streamlit-1.40%2B-red.svg)](https://streamlit.io/)
[![Meta Llama 3.2 Vision](https://img.shields.io/badge/Vision%20Model-Meta%20Llama%203.2%2011B-purple.svg)](https://build.nvidia.com/meta/llama-3.2-11b-vision-instruct)
[![NVIDIA NIM](https://img.shields.io/badge/Inference-NVIDIA%20NIM%20Catalog-green.svg)](https://integrate.api.nvidia.com)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Practical, accessible, and farmer-centric AI technology addressing agricultural crop loss, early damage diagnosis, environmental causation analysis, and tailored actionable reporting.**

---

## 📌 Problem Statement

Farmers and agronomists frequently encounter devastating crop losses caused by **plant diseases, insect pests, wild animal intrusions, extreme weather events, and waterlogging/flooding**. 

However, smallholder farmers often face critical barriers:
1. **Lack of Immediate Diagnostic Expertise:** Identifying whether leaf spots stem from fungal pathogens, bacterial blights, nutrient stress, or pest activity requires specialized knowledge that is unavailable during early outbreak windows.
2. **Missing Causation & Remedies:** Knowing a crop has damage is insufficient—farmers need to know **what environmental conditions triggered it** (e.g., prolonged leaf wetness, high humidity, improper irrigation) and **practical, safe organic & cultural remedies** to halt the spread without hazardous chemicals.
3. **High Technology Friction:** Farmers cannot navigate complex software dashboards or install heavy apps. They need a zero-friction channel—such as **Telegram**—to simply snap a picture, receive an immediate screening, and ask follow-up questions in natural language.

---

## 🌾 The 8 Core Agricultural Challenges Addressed

1. **Crop Disease Damage Detection:** Identifies fungal leaf spots, anthracnose, blights, rusts, mildews, and viral chlorosis.
2. **Pest Damage Detection:** Identifies leaf-chewing, defoliation, stem-borer entry holes, leaf-miner trails, and insect presence.
3. **Wild Animal Intrusion Assessment:** Recognizes physical trampling, canopy crushing, stem snapping, and crop grazing.
4. **Extreme Weather Damage Assessment:** Identifies hail shredding, frost scorching, wind lodging, and heat stress.
5. **Flood & Waterlogging Assessment:** Flags submergence damage, silt deposition, and root-asphyxiation chlorosis.
6. **Damage Severity & Percentage Estimation:** Computes conservative, visual damage ranges (e.g., *20–30%*, *40–50%*) avoiding false scientific precision.
7. **Localized Damage Zone Identification:** Detects affected canopy zones (e.g., *central canopy*, *lower foliage*, *stem base*).
8. **Farmer-Friendly Structured Reporting:** Generates instant Telegram assessments and downloadable, printable **Official PDF Reports**.

---

## 🏛️ System Architecture

```
                                  ┌─────────────────────────────┐
                                  │   Farmer (Telegram App)     │
                                  └──────────────┬──────────────┘
                                                 │ 📸 Sends Crop Photo / Follow-up Qs
                                                 ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│ Streamlit Web Control Center│   │ telegram_bot.py             │
│ (Evaluator / Admin Desktop) │   │ (Async Telegram Bot Engine) │
└──────────────┬──────────────┘   └──────────────┬──────────────┘
               │                                 │
               └────────────────┬────────────────┘
                                │
                                ▼
                  ┌───────────────────────────┐
                  │ ai_analyzer.py            │
                  │ Multi-Engine AI Pipeline: │
                  │ 1. Meta Llama 3.2 Vision  │
                  │ 2. NVIDIA Nemotron-3      │
                  │ 3. Moonshot AI Kimi-k3    │
                  │ 4. Google Gemini Fallback │
                  └─────────────┬─────────────┘
                                │ Structured JSON / Markdown Diagnostic
                                ▼
         ┌──────────────────────┴──────────────────────┐
         ▼                                             ▼
┌─────────────────────────────┐               ┌─────────────────────────────┐
│ database.py                 │               │ report_generator.py         │
│ (SQLite Persistence Layer)  │               │ (Telegram Text & PDF Engine)│
└─────────────────────────────┘               └─────────────────────────────┘
```

---

## 🌟 Key Features & Innovations

### 1. Multi-Engine Multimodal Vision Cascade
- **Primary Vision Engine:** [`meta/llama-3.2-11b-vision-instruct`](https://build.nvidia.com/meta/llama-3.2-11b-vision-instruct) hosted on NVIDIA NIM API (`https://integrate.api.nvidia.com/v1/chat/completions`) delivers ultra-fast (~6–8s), highly accurate plant pathology identification.
- **Secondary Reasoning Engines:** NVIDIA Nemotron-3 Nano Omni Reasoning (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`) and Moonshot AI Kimi (`moonshotai/kimi-k3`).
- **High-Availability Fallback:** Google Gemini (`gemini-3.5-flash-lite` / `gemini-3.8-flash`) ensures 100% uptime if NVIDIA rate limits or network issues occur.

### 2. Environmental Conditions & Practical Remedies Pipeline
Every analysis reports:
- **🌧️ Conditions Favoring Damage:** Details the environmental drivers (e.g., *Relative humidity >80%, extended leaf wetness, warm temperatures 20°C–28°C, stagnant air circulation, overhead watering*).
- **🛠️ Solutions & Practical Remedies:** Outlines immediate cultural sanitation, pruning guidelines, biological treatments (e.g., *Neem oil spray 0.5%, Trichoderma, Bacillus subtilis*), and aeration practices.

### 3. Interactive Unknown Crop Clarification Workflow
When an uploaded photograph has an obscured angle or unidentifiable crop:
1. The bot automatically prompts the farmer:
   > ❓ **Crop Unidentified:** AI detected visible symptoms, but the crop name could not be confirmed with certainty.  
   > 👉 **Please reply with your crop name** (e.g., *Rose, Tomato, Cotton, Wheat, Rice, Chilli*).
2. When the user replies with their crop name (e.g. *"Rose"* or *"My crop is Tomato"*), the bot recognizes the name, updates the database, and immediately outputs the exact **damage conditions and tailored remedies** for that specific plant.

### 4. Text Agronomy Q&A (No Photo Required)
Farmers can type **any farming question directly** (e.g., *"How to control aphids without chemicals?"*, *"Best fertilizer schedule for paddy"*). The bot answers conversationally in plain language.

### 5. Automated Official PDF Reports
Type `/report` in Telegram or click **Download PDF** on the Streamlit dashboard to generate an official printable ReportLab PDF assessment report with severity badges, diagnostic tables, and farmer action checklists.

---

## 📁 Project Directory Structure

```
agrivision/
├── app.py                      # Streamlit Admin & Evaluator Control Center
├── telegram_bot.py             # 24/7 Telegram Bot Daemon (Photo & Text Q&A)
├── ai_analyzer.py              # Multi-engine vision & agronomy reasoning engine
├── prompts.py                  # Structured prompts, system instructions & JSON schemas
├── database.py                 # SQLite persistence layer with schema migrations
├── report_generator.py         # Telegram message formatter & ReportLab PDF generator
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container definition for cloud deployment
├── docker-compose.yml          # Multi-container orchestration (Web + Bot)
├── README.md                   # Full documentation & deployment guide
├── .gitignore                  # Git ignore rules (protects .env and secrets)
│
├── .streamlit/
│   ├── config.toml             # Custom green AgriTech visual theme
│   ├── secrets.toml.example    # Secrets template for cloud and local deployment
│   └── secrets.toml            # (Local only - git ignored)
│
├── data/
│   ├── agrivision.db           # SQLite database (auto-created on first run)
│   └── uploads/                # Cached crop photos & generated PDF reports
│
└── tests/
    └── test_end_to_end.py      # Automated vision & diagnostic pipeline test
```

---

## 🔑 Secrets & Configuration Matrix

AgriVision supports credentials via **`.env`** or **`.streamlit/secrets.toml`**. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` or create `.env`:

```toml
# Meta Llama 3.2 11B Vision Key (Primary Vision & Diagnostic Engine)
META_LLAMA_API_KEY = "nvapi-..."

# Moonshot AI Kimi Key (Secondary / Agronomy Q&A Engine)
KIMI_API_KEY = "nvapi-..."

# NVIDIA Nemotron Key (Reasoning Engine)
NEMOTRON_API_KEY = "nvapi-..."

# General NVIDIA Key (Default Fallback for NVIDIA NIM API)
NVIDIA_API_KEY = "nvapi-..."
NVIDIA_BACKUP_API_KEY = "nvapi-..."

# Google Gemini Fallback Key
GEMINI_API_KEY = "AQ...."

# Telegram Bot Token (from Telegram @BotFather)
TELEGRAM_BOT_TOKEN = "123456789:ABCdef..."
```

### Where to Obtain Keys:
| Key | Provider | Where to Get |
|---|---|---|
| `META_LLAMA_API_KEY` | NVIDIA NIM | [build.nvidia.com/meta/llama-3.2-11b-vision-instruct](https://build.nvidia.com/meta/llama-3.2-11b-vision-instruct) |
| `KIMI_API_KEY` | NVIDIA NIM | [build.nvidia.com/moonshotai/kimi-k3](https://build.nvidia.com/moonshotai/kimi-k3) |
| `NEMOTRON_API_KEY` | NVIDIA NIM | [build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning](https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning) |
| `GEMINI_API_KEY` | Google AI Studio | [aistudio.google.com](https://aistudio.google.com/) |
| `TELEGRAM_BOT_TOKEN` | Telegram | Search for **`@BotFather`** in Telegram, send `/newbot` |

> 🔒 **Security Note:** `.env` and `.streamlit/secrets.toml` are excluded in `.gitignore`. They are never committed or pushed to GitHub.

---

## 🌐 Full Hosting & Deployment Guide

Choose the deployment method that fits your infrastructure:

### Option 1: Streamlit Community Cloud (Free & Fastest Web Hosting)
Ideal for hosting the **Web Control Center & Analytics Dashboard**:

1. **Push your code to GitHub** (Ensure repo is public or accessible by Streamlit Cloud).
2. Go to **[share.streamlit.io](https://share.streamlit.io/)** and log in with GitHub.
3. Click **"New App"**:
   - **Repository:** `YourUsername/AgriVision-AI-Crop-Damage-Intelligence-Farmer-Assistant`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Click **"Advanced settings..."** ➔ **Secrets**:
   Paste the contents of your `secrets.toml`:
   ```toml
   META_LLAMA_API_KEY = "nvapi-..."
   KIMI_API_KEY = "nvapi-..."
   NVIDIA_API_KEY = "nvapi-..."
   GEMINI_API_KEY = "AQ...."
   TELEGRAM_BOT_TOKEN = "123456789:ABCdef..."
   ```
5. Click **"Deploy"**. Your web dashboard is live on the internet with a public URL!

---

### Option 2: Docker & Docker Compose (Any VPS / Server in 1 Command)
Run both the **Streamlit Web Dashboard** and the **24/7 Telegram Bot** in isolated containers:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YourUsername/AgriVision-AI-Crop-Damage-Intelligence-Farmer-Assistant.git
   cd AgriVision-AI-Crop-Damage-Intelligence-Farmer-Assistant
   ```

2. **Create your `.env` file:**
   ```bash
   cp .streamlit/secrets.toml.example .env
   # Edit .env and enter your valid API keys
   nano .env
   ```

3. **Build and launch with Docker Compose:**
   ```bash
   docker compose up -d --build
   ```

4. **Verify container status:**
   ```bash
   docker compose ps
   # View live logs:
   docker compose logs -f
   ```

The Streamlit dashboard is available at `http://your-server-ip:8501`, and the Telegram bot will poll and respond 24/7!

---

### Option 3: Linux Cloud VPS (AWS EC2 / DigitalOcean / Linode / Ubuntu 22.04 / 24.04)
Run both services as robust background `systemd` daemons that auto-restart on crashes or system reboot:

#### 1. System Setup
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git curl libjpeg-dev zlib1g-dev nginx
```

#### 2. Clone & Setup Virtual Environment
```bash
cd /var/www
sudo git clone https://github.com/YourUsername/AgriVision-AI-Crop-Damage-Intelligence-Farmer-Assistant.git agrivision
sudo chown -R $USER:$USER /var/www/agrivision
cd agrivision

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Setup Secrets
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
nano .streamlit/secrets.toml
# Also copy to .env:
cp .streamlit/secrets.toml .env
```

#### 4. Configure `systemd` for Streamlit Dashboard (`agrivision-web.service`)
```bash
sudo nano /etc/systemd/system/agrivision-web.service
```
Paste:
```ini
[Unit]
Description=AgriVision Streamlit Web Dashboard
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/var/www/agrivision
ExecStart=/var/www/agrivision/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=5
EnvironmentFile=/var/www/agrivision/.env

[Install]
WantedBy=multi-user.target
```

#### 5. Configure `systemd` for Telegram Bot (`agrivision-bot.service`)
```bash
sudo nano /etc/systemd/system/agrivision-bot.service
```
Paste:
```ini
[Unit]
Description=AgriVision Telegram Bot Daemon
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/var/www/agrivision
ExecStart=/var/www/agrivision/venv/bin/python telegram_bot.py
Restart=always
RestartSec=5
EnvironmentFile=/var/www/agrivision/.env

[Install]
WantedBy=multi-user.target
```

#### 6. Enable and Start Both Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now agrivision-web
sudo systemctl enable --now agrivision-bot

# Check status:
sudo systemctl status agrivision-web
sudo systemctl status agrivision-bot
```

#### 7. (Optional) Configure Nginx Reverse Proxy & Free SSL
Point your domain (e.g., `agrivision.example.com`) to port `8501`:
```bash
sudo nano /etc/nginx/sites-available/agrivision
```
Paste:
```nginx
server {
    server_name agrivision.example.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }
}
```
Enable and get SSL via Let's Encrypt:
```bash
sudo ln -s /etc/nginx/sites-available/agrivision /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d agrivision.example.com
```

---

### Option 4: Render / Railway (Free PaaS Deployment)

#### Deploying Telegram Bot on Render (Background Worker):
1. Create a **New Background Worker** on [render.com](https://render.com).
2. Connect your GitHub repository.
3. Set:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python telegram_bot.py`
4. Add Environment Variables under **Settings ➔ Environment Variables**:
   - `META_LLAMA_API_KEY`, `KIMI_API_KEY`, `NVIDIA_API_KEY`, `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`.
5. Deploy. The bot runs continuously in the cloud.

#### Deploying Streamlit on Render (Web Service):
1. Create a **New Web Service**.
2. Connect repository.
3. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. Add the same Environment Variables.
5. Deploy.

---

### Option 5: Local Development (Windows / macOS / Linux)

#### 1. Setup Environment
```bash
git clone https://github.com/YourUsername/AgriVision-AI-Crop-Damage-Intelligence-Farmer-Assistant.git
cd AgriVision-AI-Crop-Damage-Intelligence-Farmer-Assistant

# Create virtual environment:
python -m venv venv

# Windows activate:
venv\Scripts\activate

# Linux / macOS activate:
source venv/bin/activate

# Install requirements:
pip install -r requirements.txt
```

#### 2. Configure Credentials
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your keys
```

#### 3. Run Services
- **Run Telegram Bot:**
  ```bash
  python telegram_bot.py
  ```
- **Run Streamlit Dashboard (in another terminal):**
  ```bash
  streamlit run app.py
  ```
- **Run Automated Verification Test:**
  ```bash
  python tests/test_end_to_end.py
  ```

---

## 📱 Telegram Commands & Usage

| Command | Action |
|---|---|
| `/start` | Introduces AgriVision and its agricultural screening features |
| `/help` | Photography tips (lighting, close-up) and guide on follow-up questions |
| `/analyze` | Instructions on how to send plant photos for evaluation |
| `/history` | Displays your recent crop inspection history with dates & damage % |
| `/report` | Delivers the latest structured report and **downloads the official PDF** |
| `[Photo Upload]` | AI vision identifies crop, damage status, causes, conditions, and remedies |
| `[Text Message]` | Clarifies crop names OR answers direct agronomy questions (fertilizer, pests, soil) |

---

## 📊 Database Schema (SQLite)

The database file `data/agrivision.db` is initialized automatically on first run:

- **`analyses` table:**
  - `id`: Unique record ID
  - `telegram_user_id`, `telegram_chat_id`, `username`: User identity
  - `timestamp`: Analysis creation time
  - `image_path`: Stored photo location in `data/uploads/`
  - `crop_identified`: Crop name (e.g. *Rose*, *Tomato*, *Wheat*)
  - `damage_detected`: Boolean flag (True/False)
  - `possible_damage_types`: JSON array of observed damage categories
  - `possible_cause`: Diagnostic cause (e.g. *Black Spot fungal infection*)
  - `severity`: Classification (*None*, *Low*, *Moderate*, *High*, *Severe*)
  - `estimated_visible_damage_percentage`: Percentage range (e.g. *20–30%*)
  - `affected_regions`: Image zones where damage is concentrated
  - `visible_symptoms`: Observed diagnostic markers
  - `confidence`: Visual assessment confidence (*Low*, *Medium*, *High*)
  - `recommended_next_steps`: Numbered actionable next steps
  - `limitations`: 2D image screening disclaimers
  - `raw_json_response`: Full structured response payload
  - `source`: Platform origin (`telegram` or `web_dashboard`)

- **`chat_messages` table:**
  - `id`: Message ID
  - `analysis_id`: Linked analysis record
  - `telegram_user_id`: Telegram user ID
  - `role`: Message author (`user` or `assistant`)
  - `message_text`: Content of inquiry or response
  - `timestamp`: Chat timestamp

---

## ⚠️ Limitations & Responsible AI Guidelines

1. **Initial Screening Tool:** AgriVision is an artificial intelligence decision-support tool. It is designed for early warning, triage, and educational assistance. It is **not a replacement for certified on-site agronomists**.
2. **2D Photographic Limits:** Visual screening cannot evaluate sub-surface root nematodes, soil pH imbalances, or microscopic viral strains.
3. **Safe Interventions:** The platform strictly prioritizes physical hygiene, cultural practices, and biological controls (e.g., neem oil, sanitation) over dangerous chemical cocktails. Always consult local extension offices (e.g., Krishi Vigyan Kendra / Krishi Bhavan) before applying restricted chemicals.

---

## 🔮 Future Roadmap

- 🚁 **Drone-Based Aerial Surveys:** Ingesting stitched orthomosaic farm field maps for field-scale damage quantification.
- 📍 **GPS Geo-tagging & Outbreak Heatmaps:** Mapping cluster outbreaks across districts and panchayats.
- 🔬 **Edge Vision (YOLO/TFLite):** Offline on-device pest localization for remote rural zones without connectivity.
- 🗣️ **Multilingual Voice Support:** Native voice notes in regional Indian and global languages.
- 📡 **IoT Soil Sensor Fusion:** Correlating visual foliar stress with live soil NPK, moisture, and temperature telemetry.

---

## 📜 License & Acknowledgments

This project is licensed under the **MIT License** — free for academic, non-commercial, and open-source agricultural development.

Special thanks to:
- **Meta AI** for the Llama 3.2 Vision architecture.
- **NVIDIA Developer Program** for the NVIDIA NIM Inference API catalog.
- **Google DeepMind** for the Gemini multimodal API.
