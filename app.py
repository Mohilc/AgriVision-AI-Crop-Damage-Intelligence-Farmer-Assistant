"""
AgriVision - Streamlit Web Dashboard & Evaluation Interface
Interactive prototype for field inspections, AI analytics, metrics, and report downloads.
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

# Custom CSS for polished agritech styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1B5E20;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4E6E58;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E0E8E0;
        border-radius: 10px;
        padding: 1.2rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        text-align: center;
    }
    .metric-val {
        font-size: 2rem;
        font-weight: 700;
        color: #2E7D32;
    }
    .metric-lbl {
        font-size: 0.9rem;
        color: #556B5D;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-none { background-color: #E8F5E9; color: #2E7D32; padding: 4px 10px; border-radius: 12px; font-weight: 600; }
    .badge-low { background-color: #FFFDE7; color: #F57F17; padding: 4px 10px; border-radius: 12px; font-weight: 600; }
    .badge-moderate { background-color: #FFF3E0; color: #E65100; padding: 4px 10px; border-radius: 12px; font-weight: 600; }
    .badge-high { background-color: #FFEBEE; color: #C62828; padding: 4px 10px; border-radius: 12px; font-weight: 600; }
    .badge-severe { background-color: #B71C1C; color: #FFFFFF; padding: 4px 10px; border-radius: 12px; font-weight: 600; }
    .stButton>button {
        background-color: #2E7D32;
        color: white;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #1B5E20;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
database.init_db()


def get_severity_badge(severity: str) -> str:
    """Returns an HTML badge for a given severity level."""
    s = str(severity).lower()
    if s == "none":
        return f'<span class="badge-none">🟢 Healthy / None</span>'
    elif s == "low":
        return f'<span class="badge-low">🟡 Low Severity</span>'
    elif s == "moderate":
        return f'<span class="badge-moderate">🟠 Moderate Severity</span>'
    elif s == "high":
        return f'<span class="badge-high">🔴 High Damage</span>'
    elif s == "severe":
        return f'<span class="badge-severe">🚨 Severe Devastation</span>'
    return f'<span>{severity}</span>'


# Sidebar navigation
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1592982537447-7440770cbfc9?w=500&auto=format&fit=crop&q=60", use_container_width=True)
    st.title("🌾 AgriVision AI")
    st.markdown("**AI-Based Crop Damage Detection & Quantification**")
    st.divider()
    
    app_mode = st.radio(
        "Navigation",
        ["🔍 Live Image Analysis", "📊 Analytics Dashboard", "📋 Inspection Audit Log", "ℹ️ About & System Specs"]
    )
    
    st.divider()
    
    # API Key Configuration status
    api_key = ai_analyzer.get_gemini_api_key()
    if api_key:
        st.success("✅ Gemini Vision API Connected")
    else:
        st.warning("⚠️ Gemini API Key not detected")
        custom_key = st.text_input("Enter Gemini API Key Override", type="password")
        if custom_key:
            os.environ["GEMINI_API_KEY"] = custom_key
            st.rerun()

    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if telegram_token and telegram_token != "your-telegram-bot-token-here":
        st.success("🤖 Telegram Bot Service Ready")
    else:
        st.info("ℹ️ Telegram Bot in Standby")


# View 1: Live Image Analysis
if app_mode == "🔍 Live Image Analysis":
    st.markdown('<div class="main-header">🌾 Crop Damage Visual Inspection</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload an on-field photograph of a damaged or healthy crop for instant AI damage detection, quantification, and farmer reporting.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("1. Provide Crop Photograph")
        input_type = st.radio("Input Source", ["File Upload", "Camera Snapshot"], horizontal=True)
        
        uploaded_file = None
        if input_type == "File Upload":
            uploaded_file = st.file_uploader(
                "Choose crop photo (JPG, PNG, WEBP)",
                type=["jpg", "jpeg", "png", "webp"],
                help="Ensure affected leaves or field damage is clearly visible"
            )
        else:
            uploaded_file = st.camera_input("Take a photo of the crop")

        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Crop Image", use_container_width=True)
            
            analyze_btn = st.button("🚀 Analyze Crop Damage", use_container_width=True)

    with col2:
        st.subheader("2. AI Damage Diagnostics & Report")
        
        if uploaded_file is not None and analyze_btn:
            with st.spinner("Analyzing visible damage symptoms with Gemini Vision..."):
                try:
                    # Save image to data/uploads
                    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    local_filename = f"web_{timestamp_str}.jpg"
                    local_filepath = os.path.join(database.UPLOADS_DIR, local_filename)
                    image.save(local_filepath)

                    # Analyze
                    analysis = ai_analyzer.analyze_crop_image(local_filepath)
                    
                    # Save to DB
                    analysis_id = database.save_analysis(
                        data=analysis,
                        image_path=local_filepath,
                        source="web_dashboard"
                    )
                    analysis["id"] = analysis_id
                    st.session_state["current_analysis"] = analysis
                    st.session_state["current_image_path"] = local_filepath
                    st.session_state["current_analysis_id"] = analysis_id

                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")

        if "current_analysis" in st.session_state:
            res = st.session_state["current_analysis"]
            
            # Severity header banner
            sev = res.get("severity", "None")
            st.markdown(f"### {get_severity_badge(sev)}", unsafe_allow_html=True)
            
            # Key Facts Table
            st.markdown(f"""
            - **Crop Identified:** `{res.get('crop_identified', 'Unknown')}`
            - **Damage Status:** `{'Detected' if res.get('damage_detected') else 'None / Healthy'}`
            - **Possible Cause:** **{res.get('possible_cause', 'Uncertain')}**
            - **Estimated Visible Damage:** `{res.get('estimated_visible_damage_percentage', 'N/A')}`
            - **Confidence Level:** `{res.get('confidence', 'Medium')}`
            """)
            
            # Symptoms and Regions in Expanders/Tabs
            t1, t2, t3 = st.tabs(["🩺 Symptoms & Regions", "📋 Action Plan", "⚠️ Limitations"])
            
            with t1:
                st.markdown("**Visible Symptoms:**")
                for s in res.get("visible_symptoms", []):
                    st.markdown(f"- {s}")
                    
                st.markdown("**Affected Image Regions:**")
                for r in res.get("affected_regions", []):
                    st.markdown(f"- 📍 {r}")

            with t2:
                st.markdown("**Recommended Next Steps for the Farmer:**")
                for i, step in enumerate(res.get("recommended_next_steps", []), 1):
                    st.markdown(f"{i}. {step}")

            with t3:
                st.markdown("**AI Screening Limitations:**")
                for lim in res.get("limitations", []):
                    st.markdown(f"- {lim}")

            # PDF Download
            st.divider()
            try:
                pdf_filename = f"AgriVision_Assessment_{res.get('id', 'temp')}.pdf"
                pdf_path = os.path.join(database.UPLOADS_DIR, pdf_filename)
                report_generator.generate_pdf_report(
                    data=res,
                    output_pdf_path=pdf_path,
                    image_path=st.session_state.get("current_image_path")
                )
                
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📄 Download Official PDF Report",
                        data=f,
                        file_name=pdf_filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
            except Exception as pdf_err:
                st.caption(f"PDF creation notice: {pdf_err}")

        elif uploaded_file is None:
            st.info("👈 Upload a crop photo on the left and click **Analyze Crop Damage** to generate a report.")


# View 2: Analytics Dashboard
elif app_mode == "📊 Analytics Dashboard":
    st.markdown('<div class="main-header">📊 Agricultural Health & Damage Metrics</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Aggregated field telemetry, severity breakdowns, and high-frequency crop risk patterns.</div>', unsafe_allow_html=True)

    metrics = database.get_dashboard_metrics()
    
    # 4 Key KPI Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{metrics['total_analyses']}</div>
            <div class="metric-lbl">Total Analyses</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val" style="color: #D32F2F;">{metrics['total_damaged']}</div>
            <div class="metric-lbl">Damage Cases</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{metrics['unique_crops']}</div>
            <div class="metric-lbl">Distinct Crops</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        pct = round((metrics['total_damaged'] / metrics['total_analyses'] * 100), 1) if metrics['total_analyses'] > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val" style="color: #E65100;">{pct}%</div>
            <div class="metric-lbl">Damage Rate</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    
    # Charts Row
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Severity Distribution")
        sev_data = metrics.get("severity_distribution", {})
        if sev_data:
            sev_df = pd.DataFrame(list(sev_data.items()), columns=["Severity", "Count"])
            st.bar_chart(sev_df.set_index("Severity"), color="#2E7D32")
        else:
            st.info("No severity records available yet.")

    with c2:
        st.subheader("Top Crops Inspected")
        top_crops = metrics.get("top_crops", [])
        if top_crops:
            crop_df = pd.DataFrame(top_crops)
            st.bar_chart(crop_df.set_index("crop"), color="#4E6E58")
        else:
            st.info("No crop records available yet.")


# View 3: Inspection Audit Log
elif app_mode == "📋 Inspection Audit Log":
    st.markdown('<div class="main-header">📋 Crop Inspection Records</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Full historical registry of all Telegram and Web analyses.</div>', unsafe_allow_html=True)

    all_records = database.get_all_analyses(limit=50)
    
    if all_records:
        df_display = []
        for r in all_records:
            df_display.append({
                "ID": r["id"],
                "Date": r["timestamp"],
                "Source": r["source"],
                "Crop": r["crop_identified"],
                "Damage": "Yes" if r["damage_detected"] else "No",
                "Severity": r["severity"],
                "Est. Damage %": r["estimated_visible_damage_percentage"],
                "Possible Cause": r["possible_cause"]
            })
        st.dataframe(pd.DataFrame(df_display), use_container_width=True)
        
        # Detail view selector
        st.divider()
        st.subheader("🔍 Inspect Single Record")
        record_ids = [r["id"] for r in all_records]
        selected_id = st.selectbox("Select Analysis Record ID", record_ids)
        
        if selected_id:
            record = database.get_analysis_by_id(selected_id)
            if record:
                rcol1, rcol2 = st.columns([1, 1])
                with rcol1:
                    if record.get("image_path") and os.path.exists(record["image_path"]):
                        st.image(record["image_path"], caption=f"Crop Photo (Record #{selected_id})", use_container_width=True)
                    else:
                        st.caption("No image file cached.")
                with rcol2:
                    st.markdown(f"### Record #{record['id']} — {record['crop_identified']}")
                    st.markdown(f"**Severity:** {record['severity']} | **Damage:** {record['estimated_visible_damage_percentage']}")
                    st.markdown(f"**Possible Cause:** {record['possible_cause']}")
                    st.markdown(f"**Timestamp:** {record['timestamp']} ({record['source']})")
                    
                    st.markdown("**Symptoms:**")
                    for s in record.get("visible_symptoms", []):
                        st.markdown(f"- {s}")
                    st.markdown("**Next Steps:**")
                    for stp in record.get("recommended_next_steps", []):
                        st.markdown(f"- {stp}")
    else:
        st.info("No records recorded in the database yet.")


# View 4: About & System Specs
elif app_mode == "ℹ️ About & System Specs":
    st.markdown('<div class="main-header">🌱 About AgriVision</div>', unsafe_allow_html=True)
    st.markdown("""
    ### AI-Driven Precision Agriculture
    **AgriVision** is an AI-powered agricultural damage detection, quantification, and farmer reporting system. 
    It bridges the gap between complex computer vision reasoning and rural farmers through simple messaging (Telegram) and web accessibility.

    #### The 8 Core Agricultural Challenges Addressed:
    1. **Crop Disease Damage Detection:** Identifies leaf spots, rusts, blights, and viral discolorations.
    2. **Pest Damage Assessment:** Detects defoliation, borers, leaf miners, and chewing injuries.
    3. **Wild Animal Intrusion Impact:** Assesses structural trampling, breakage, and grazing losses.
    4. **Weather-Induced Hazards:** Recognizes hail marks, frostburn, lodging, and sun-scald.
    5. **Flood & Waterlogging Stress:** Diagnoses asphyxiation yellowing, root rot signs, and sediment burial.
    6. **Visible Severity & Percentage Estimation:** Approximates damaged foliage ranges without claiming unproven physical metrics.
    7. **Localized Zone Identification:** Isolates damaged sectors (e.g. lower canopy, leaf tips, root base).
    8. **Farmer-Centric Actionable Reports:** Generates structured Telegram summaries and downloadable official PDF reports.

    #### System Architecture:
    - **Multimodal AI:** Google Gemini 3.8 Flash (Interactions API).
    - **Frontend:** Streamlit 1.35+.
    - **Messaging Engine:** Python Telegram Bot API (Async).
    - **Persistence:** SQLite with thread-safe connection pooling.
    - **Reporting:** ReportLab PDF Engine.
    """)
