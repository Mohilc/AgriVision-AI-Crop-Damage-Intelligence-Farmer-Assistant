"""
AgriVision - Streamlit Web Dashboard & Evaluation Interface
Interactive agritech control center for crop damage detection, AI analytics, metrics, and farmer reporting.
"""

import os
import io
import time
from datetime import datetime
from PIL import Image
import pandas as pd
import streamlit as st

import database
import ai_analyzer
import report_generator

# Page Configuration
st.set_page_config(
    page_title="AgriVision — AI Crop Damage Assessment",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database & seed demo data if empty
database.init_db()
database.seed_sample_data()

# Modern AgriTech Styling
st.markdown("""
<style>
    .hero-banner {
        background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 50%, #43A047 100%);
        color: white;
        padding: 1.8rem 2rem;
        border-radius: 14px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(27, 94, 32, 0.15);
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        color: #FFFFFF;
        letter-spacing: -0.5px;
    }
    .hero-sub {
        font-size: 1.05rem;
        color: #E8F5E9;
        margin-top: 0.4rem;
        font-weight: 400;
    }
    .status-pills {
        display: flex;
        gap: 0.8rem;
        margin-top: 1rem;
        flex-wrap: wrap;
    }
    .status-pill {
        background: rgba(255, 255, 255, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: transform 0.15s ease-in-out;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }
    .metric-val {
        font-size: 2.1rem;
        font-weight: 800;
        color: #1B5E20;
    }
    .metric-lbl {
        font-size: 0.85rem;
        color: #4A5568;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.2rem;
        font-weight: 600;
    }
    .badge-none { background-color: #E8F5E9; color: #2E7D32; padding: 5px 12px; border-radius: 14px; font-weight: 700; font-size: 1rem; display: inline-block; }
    .badge-low { background-color: #FFFDE7; color: #F57F17; padding: 5px 12px; border-radius: 14px; font-weight: 700; font-size: 1rem; display: inline-block; }
    .badge-moderate { background-color: #FFF3E0; color: #E65100; padding: 5px 12px; border-radius: 14px; font-weight: 700; font-size: 1rem; display: inline-block; }
    .badge-high { background-color: #FFEBEE; color: #C62828; padding: 5px 12px; border-radius: 14px; font-weight: 700; font-size: 1rem; display: inline-block; }
    .badge-severe { background-color: #B71C1C; color: #FFFFFF; padding: 5px 12px; border-radius: 14px; font-weight: 700; font-size: 1rem; display: inline-block; }
    .sample-box {
        background: #F8FAFC;
        border: 1px dashed #CBD5E1;
        border-radius: 10px;
        padding: 0.8rem;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def get_severity_badge(severity: str) -> str:
    """Returns an HTML badge for a given severity level."""
    s = str(severity).lower()
    if s == "none":
        return '<span class="badge-none">🟢 Healthy / No Damage</span>'
    elif s == "low":
        return '<span class="badge-low">🟡 Low Severity (<15%)</span>'
    elif s == "moderate":
        return '<span class="badge-moderate">🟠 Moderate Severity (15–40%)</span>'
    elif s == "high":
        return '<span class="badge-high">🔴 High Damage (40–70%)</span>'
    elif s == "severe":
        return '<span class="badge-severe">🚨 Severe Devastation (>70%)</span>'
    return f'<span>{severity}</span>'


# Sidebar controls & credentials
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1592982537447-7440770cbfc9?w=500&auto=format&fit=crop&q=60")
    st.title("🌾 AgriVision AI")
    st.markdown("**AI Crop Damage Detection & Intelligence**")
    st.divider()

    st.subheader("⚡ System Telemetry")
    nv_key = ai_analyzer.get_nvidia_api_key()
    if nv_key:
        st.success("✅ NVIDIA Nemotron Engine: Active")
    else:
        st.warning("⚠️ NVIDIA API Key Missing")

    gem_key = ai_analyzer.get_gemini_api_key()
    if gem_key:
        st.info("✅ Gemini Fallback: Ready")

    tg_token = database.os.environ.get("TELEGRAM_BOT_TOKEN")
    if tg_token and tg_token != "your-telegram-bot-token-here":
        st.success("🤖 Telegram Bot Service: Active")
    else:
        st.info("ℹ️ Telegram Bot in Standby")

    st.divider()
    st.markdown("### 💡 Quick Actions")
    if st.button("🔄 Refresh Data & Charts", use_container_width=True):
        st.rerun()

    if st.button("🌱 Re-Seed Demo Inspections", use_container_width=True):
        database.seed_sample_data()
        st.success("Sample field analyses loaded!")
        time.sleep(0.5)
        st.rerun()


# Top Hero Banner
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">🌾 AgriVision Intelligence Control Center</div>
    <div class="hero-sub">AI-Powered Agricultural Damage Detection, Quantification, and Farmer Assistance</div>
    <div class="status-pills">
        <span class="status-pill">🔬 AI: NVIDIA Nemotron-3 Reasoning + Gemini</span>
        <span class="status-pill">📱 Telegram Bot 24/7 Available</span>
        <span class="status-pill">📄 Automated PDF Reports</span>
        <span class="status-pill">⚡ Multimodal Vision & Text Q&A</span>
    </div>
</div>
""", unsafe_allow_html=True)


# 4 Real-time Metric Cards
metrics = database.get_dashboard_metrics()
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">{metrics['total_analyses']}</div>
        <div class="metric-lbl">Total Inspections</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-val" style="color: #D32F2F;">{metrics['total_damaged']}</div>
        <div class="metric-lbl">Damage Cases Detected</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-val" style="color: #0288D1;">{metrics['unique_crops']}</div>
        <div class="metric-lbl">Crop Varieties Screened</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    healthy_cnt = max(0, metrics['total_analyses'] - metrics['total_damaged'])
    healthy_rate = round((healthy_cnt / metrics['total_analyses'] * 100), 1) if metrics['total_analyses'] > 0 else 100
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-val" style="color: #2E7D32;">{healthy_rate}%</div>
        <div class="metric-lbl">Canopy Health Rate</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)


# Navigation Tabs on the Main Page
tab_inspect, tab_chat, tab_analytics, tab_logs, tab_about = st.tabs([
    "🔍 Crop Visual Inspection",
    "💬 AI Agronomist Chat (Text Q&A)",
    "📊 Analytics & Risk Charts",
    "📋 Inspection Audit Log",
    "ℹ️ System Specifications"
])


# ==========================================
# TAB 1: CROP VISUAL INSPECTION
# ==========================================
with tab_inspect:
    st.subheader("Field Crop Photograph Analysis")
    st.markdown("Upload a crop photo, take a camera snapshot, or select one of the pre-loaded agricultural demo scenarios below.")

    # 1-Click Demo Scenarios
    st.markdown("##### ⚡ Quick 1-Click Demo Cases")
    demo_c1, demo_c2, demo_c3, demo_c4 = st.columns(4)
    
    with demo_c1:
        if st.button("🍅 Test Tomato Blight", use_container_width=True):
            st.session_state["demo_selection"] = {
                "crop": "Tomato",
                "color": (139, 69, 19),
                "name": "sample_tomato.jpg"
            }
    with demo_c2:
        if st.button("🌽 Test Maize Armyworm", use_container_width=True):
            st.session_state["demo_selection"] = {
                "crop": "Maize (Corn)",
                "color": (160, 82, 45),
                "name": "sample_maize__corn_.jpg"
            }
    with demo_c3:
        if st.button("🌾 Test Wheat Rust", use_container_width=True):
            st.session_state["demo_selection"] = {
                "crop": "Wheat",
                "color": (218, 165, 32),
                "name": "sample_wheat.jpg"
            }
    with demo_c4:
        if st.button("🌱 Test Healthy Paddy", use_container_width=True):
            st.session_state["demo_selection"] = {
                "crop": "Paddy / Rice",
                "color": (34, 139, 34),
                "name": "sample_paddy___rice.jpg"
            }


    st.divider()

    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        st.markdown("#### 1. Provide Crop Photograph")
        input_method = st.radio("Photo Input Method", ["File Upload", "Camera Snapshot"], horizontal=True)

        uploaded_img = None
        if input_method == "File Upload":
            uploaded_file = st.file_uploader(
                "Select a plant or field photo",
                type=["jpg", "jpeg", "png", "webp"],
                help="Ensure affected leaves, stem, or damage zones are clearly visible"
            )
            if uploaded_file is not None:
                uploaded_img = Image.open(uploaded_file)
        else:
            cam_file = st.camera_input("Take a photo of the crop")
            if cam_file is not None:
                uploaded_img = Image.open(cam_file)

        # Handle demo click
        if uploaded_img is None and "demo_selection" in st.session_state:
            demo_info = st.session_state["demo_selection"]
            demo_path = os.path.join(database.UPLOADS_DIR, demo_info["name"])
            if os.path.exists(demo_path):
                uploaded_img = Image.open(demo_path)
            else:
                uploaded_img = Image.new("RGB", (300, 300), color=demo_info["color"])
                uploaded_img.save(demo_path)
            st.info(f"Loaded Demo Case: **{demo_info['crop']}**")

        if uploaded_img is not None:
            st.image(uploaded_img, caption="Crop Photograph for AI Assessment", use_container_width=True)
            analyze_action = st.button("🚀 Analyze Crop Damage with AI", use_container_width=True, type="primary")
        else:
            analyze_action = False
            st.info("👈 Upload an image, capture with camera, or click one of the 1-Click Demo buttons above!")

    with right_col:
        st.markdown("#### 2. Diagnostic Assessment & Farmer Report")

        if uploaded_img is not None and analyze_action:
            with st.spinner("Analyzing plant symptoms, severity, and damage patterns with AI..."):
                try:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_path = os.path.join(database.UPLOADS_DIR, f"web_scan_{ts}.jpg")
                    uploaded_img.save(save_path)

                    # Run multimodal analysis
                    analysis = ai_analyzer.analyze_crop_image(save_path)

                    # Save record to database
                    rec_id = database.save_analysis(
                        data=analysis,
                        image_path=save_path,
                        source="web_dashboard",
                        username="Web Evaluator"
                    )
                    analysis["id"] = rec_id

                    st.session_state["latest_web_analysis"] = analysis
                    st.session_state["latest_web_image"] = save_path
                    st.success("✅ Analysis Complete!")

                except Exception as err:
                    st.error(f"Analysis notice: {err}")

        # Display result if available
        if "latest_web_analysis" in st.session_state:
            res = st.session_state["latest_web_analysis"]
            sev = res.get("severity", "None")

            st.markdown(f"### {get_severity_badge(sev)}", unsafe_allow_html=True)
            
            st.markdown(f"""
            - **Crop Identified:** `{res.get('crop_identified', 'Unknown')}`
            - **Damage Status:** `{'Detected' if res.get('damage_detected') else 'None / Healthy'}`
            - **Likely Cause:** **{res.get('possible_cause', 'Inconclusive')}**
            - **Estimated Visible Damage:** `{res.get('estimated_visible_damage_percentage', 'N/A')}`
            - **Confidence Level:** `{res.get('confidence', 'Medium')}`
            """)

            sub_t1, sub_t2, sub_t3 = st.tabs(["🩺 Symptoms & Regions", "📋 Action Plan", "⚠️ Limitations"])
            with sub_t1:
                st.markdown("**Visible Diagnostic Symptoms:**")
                for s in res.get("visible_symptoms", []):
                    st.markdown(f"- {s}")
                st.markdown("**Localized Damage Zones:**")
                for r in res.get("affected_regions", []):
                    st.markdown(f"- 📍 {r}")

            with sub_t2:
                st.markdown("**Recommended Next Steps for the Farmer:**")
                for i, stp in enumerate(res.get("recommended_next_steps", []), 1):
                    st.markdown(f"**{i}.** {stp}")

            with sub_t3:
                st.markdown("**Evaluation Limitations:**")
                for lim in res.get("limitations", []):
                    st.markdown(f"- ⚠️ {lim}")

            st.divider()
            try:
                pdf_name = f"AgriVision_Report_{res.get('id', 'temp')}.pdf"
                pdf_file_path = os.path.join(database.UPLOADS_DIR, pdf_name)
                report_generator.generate_pdf_report(
                    data=res,
                    output_pdf_path=pdf_file_path,
                    image_path=st.session_state.get("latest_web_image")
                )
                with open(pdf_file_path, "rb") as f:
                    st.download_button(
                        label="📄 Download Official PDF Assessment Report",
                        data=f,
                        file_name=pdf_name,
                        mime="application/pdf",
                        use_container_width=True
                    )
            except Exception as pdf_err:
                st.caption(f"PDF creation status: {pdf_err}")

        elif uploaded_img is None:
            st.markdown("""
            <div style="background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 12px; padding: 2.5rem; text-align: center; color: #64748B;">
                <h3>🌾 Awaiting Crop Image</h3>
                <p>Provide a crop photograph on the left to receive an instant visual diagnostic report, symptom quantification, and farmer recommendations.</p>
            </div>
            """, unsafe_allow_html=True)


# ==========================================
# TAB 2: AI AGRONOMIST CHAT (TEXT Q&A)
# ==========================================
with tab_chat:
    st.subheader("💬 Ask AgriVision AI Agronomist (Text Q&A)")
    st.markdown("Farmers and field staff can ask *any* agricultural question by text—pest control, disease remedies, soil nutrition, irrigation, or organic practices.")

    if "web_chat_history" not in st.session_state:
        st.session_state["web_chat_history"] = [
            {"role": "assistant", "content": "🌱 Hello! I am your AgriVision Agronomist. How can I help with your crops or field today? You can ask about pest control, disease symptoms, fertilizer timing, or crop management."}
        ]

    # Suggestion chips
    st.markdown("**Quick Inquiries:**")
    q_c1, q_c2, q_c3 = st.columns(3)
    preset_query = None
    with q_c1:
        if st.button("🐛 Natural aphid & pest control", use_container_width=True):
            preset_query = "What are the most effective organic and natural ways to control aphids and chewing pests without dangerous chemicals?"
    with q_c2:
        if st.button("🍂 Yellow leaves remedy", use_container_width=True):
            preset_query = "My crop leaves are turning yellow with dry tips. What are the common causes and how do I fix it?"
    with q_c3:
        if st.button("💧 Irrigation & fungus prevention", use_container_width=True):
            preset_query = "How can proper watering practices prevent fungal leaf spot and root rot in vegetable crops?"

    # Display chat messages
    for msg in st.session_state["web_chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("Type your farming or crop question here...") or preset_query

    if user_input:
        # Add user message
        st.session_state["web_chat_history"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Generate AI answer
        with st.chat_message("assistant"):
            with st.spinner("AgriVision AI is consulting agronomic guidelines..."):
                answer = ai_analyzer.answer_general_question(
                    user_question=user_input,
                    chat_history=st.session_state["web_chat_history"][-6:]
                )
                st.markdown(answer)
                st.session_state["web_chat_history"].append({"role": "assistant", "content": answer})


# ==========================================
# TAB 3: VISUAL ANALYTICS & TELEMETRY
# ==========================================
with tab_analytics:
    st.subheader("📊 Agricultural Telemetry & Risk Patterns")
    st.markdown("Aggregated telemetry from all field inspections across Telegram and Web channels.")

    chart_c1, chart_c2 = st.columns(2)

    with chart_c1:
        st.markdown("##### Damage Severity Distribution")
        sev_counts = metrics.get("severity_distribution", {})
        if sev_counts:
            sev_df = pd.DataFrame(list(sev_counts.items()), columns=["Severity", "Count"])
            st.bar_chart(sev_df.set_index("Severity"), color="#2E7D32")
        else:
            st.info("No severity records logged yet.")

    with chart_c2:
        st.markdown("##### Top Crops Screened")
        top_crops = metrics.get("top_crops", [])
        if top_crops:
            crop_df = pd.DataFrame(top_crops)
            st.bar_chart(crop_df.set_index("crop"), color="#0288D1")
        else:
            st.info("No crop records logged yet.")


# ==========================================
# TAB 4: INSPECTION AUDIT LOG
# ==========================================
with tab_logs:
    st.subheader("📋 Historical Crop Inspection Registry")
    all_records = database.get_all_analyses(limit=50)

    if all_records:
        records_table = []
        for r in all_records:
            records_table.append({
                "ID": r["id"],
                "Timestamp": r["timestamp"],
                "Channel": r["source"],
                "Crop": r["crop_identified"],
                "Damage": "Yes" if r["damage_detected"] else "No",
                "Severity": r["severity"],
                "Est. Damage %": r["estimated_visible_damage_percentage"],
                "Likely Cause": r["possible_cause"]
            })
        st.dataframe(pd.DataFrame(records_table), use_container_width=True)

        st.divider()
        st.markdown("##### 🔍 Deep Record Inspection")
        rec_ids = [r["id"] for r in all_records]
        chosen_id = st.selectbox("Select Record ID to inspect", rec_ids)

        if chosen_id:
            record_item = database.get_analysis_by_id(chosen_id)
            if record_item:
                det_c1, det_c2 = st.columns([1, 1])
                with det_c1:
                    if record_item.get("image_path") and os.path.exists(record_item["image_path"]):
                        st.image(record_item["image_path"], caption=f"Field Photo (Record #{chosen_id})", use_container_width=True)
                    else:
                        st.caption("No image file cached on server.")
                with det_c2:
                    st.markdown(f"### Record #{record_item['id']} — {record_item['crop_identified']}")
                    st.markdown(f"**Severity:** {record_item['severity']} | **Damage:** {record_item['estimated_visible_damage_percentage']}")
                    st.markdown(f"**Likely Cause:** {record_item['possible_cause']}")
                    st.markdown(f"**Logged:** {record_item['timestamp']} via `{record_item['source']}`")
                    st.markdown("**Diagnostic Symptoms:**")
                    for s in record_item.get("visible_symptoms", []):
                        st.markdown(f"- {s}")
                    st.markdown("**Recommended Next Steps:**")
                    for stp in record_item.get("recommended_next_steps", []):
                        st.markdown(f"- {stp}")
    else:
        st.info("No records recorded in the database yet.")


# ==========================================
# TAB 5: SYSTEM SPECIFICATIONS
# ==========================================
with tab_about:
    st.subheader("ℹ️ System Architecture & Problem Scope")
    st.markdown("""
    ### AI-Driven Precision Agriculture
    **AgriVision** is an AI-powered agricultural intelligence system designed to detect, quantify, and report crop damage directly to farmers via Telegram and Web interfaces.

    #### The 8 Agricultural Challenges Addressed:
    1. **Crop Disease Damage Detection:** Identifies fungal, bacterial, and viral visual symptoms.
    2. **Pest Damage Assessment:** Quantifies chewing, defoliation, borer holes, and insect injury.
    3. **Wild Animal Intrusion Impact:** Assesses structural trampling, lodging, and grazing losses.
    4. **Weather-Induced Hazards:** Diagnoses hail pockmarks, frost burns, wind snapping, and sun-scald.
    5. **Flood & Waterlogging Stress:** Identifies root asphyxiation, silt burial, and chlorotic yellowing.
    6. **Visible Severity Quantification:** Computes approximate visible damage percentages without unrealistic physical precision claims.
    7. **Localized Zone Identification:** Pinpoints affected leaf clusters, lower canopy, or apical foliage.
    8. **Farmer-Centric Actionable Reports:** Generates structured Telegram summaries, interactive web guidance, and downloadable official PDF reports.

    #### Integrated AI Engine Stack:
    - **Primary Vision & Reasoning:** NVIDIA Nemotron-3 Nano Omni Reasoning Vision (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`) via `integrate.api.nvidia.com`.
    - **Backup AI Engine:** Moonshot AI `moonshotai/kimi-k3` & Google Gemini `gemini-3.5-flash-lite`.
    - **Messaging Interface:** Async Python Telegram Bot API.
    - **Web Control Interface:** Streamlit 1.64+.
    - **Persistence:** SQLite with thread-safe connection pooling.
    - **Reporting:** ReportLab PDF Engine.
    """)
