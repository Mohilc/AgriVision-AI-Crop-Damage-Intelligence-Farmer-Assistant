"""
AgriVision - Verification & Test Script
Validates database operations, schema integrity, report generator, and PDF export.
"""

import os
import shutil
import database
import report_generator
import prompts

def test_pipeline():
    print("[1/4] Testing Database Initialization...")
    database.init_db()
    assert os.path.exists(database.DB_PATH), "Database file not created"
    print("      [OK] Database schema initialized.")

    print("[2/4] Testing Database CRUD & Metrics...")
    sample_data = {
        "crop_identified": "Tomato",
        "damage_detected": True,
        "possible_damage_types": ["Disease", "Weather"],
        "possible_cause": "Early blight (Alternaria solani) with secondary heat stress",
        "severity": "Moderate",
        "estimated_visible_damage_percentage": "20–30%",
        "affected_regions": ["Lower-left canopy", "Mid leaf tips"],
        "visible_symptoms": [
            "Concentric ring brown lesions",
            "Yellow halo chlorosis",
            "Leaf tip drying"
        ],
        "confidence": "High",
        "recommended_next_steps": [
            "Prune and safely discard heavily infected lower leaves.",
            "Avoid overhead irrigation to reduce foliage dampness.",
            "Inspect neighboring tomato rows for early spot emergence.",
            "Consult local Krishi Bhavan extension officer if lesions expand."
        ],
        "limitations": [
            "Visual inspection cannot analyze root pathogen presence.",
            "Exact square meter area calculation requires calibrated ground markers."
        ]
    }

    dummy_img_path = os.path.join(database.UPLOADS_DIR, "test_crop.jpg")
    # Create small dummy image if not exists
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (400, 400), color=(80, 160, 80))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 50, 150, 150], fill=(160, 80, 50))
    img.save(dummy_img_path)

    analysis_id = database.save_analysis(
        data=sample_data,
        image_path=dummy_img_path,
        telegram_user_id="12345678",
        telegram_chat_id="12345678",
        username="TestFarmer",
        source="test_runner"
    )
    print(f"      [OK] Sample analysis inserted with ID: #{analysis_id}")

    # Retrieve analysis
    retrieved = database.get_analysis_by_id(analysis_id)
    assert retrieved["crop_identified"] == "Tomato"
    assert retrieved["damage_detected"] == 1
    assert "Lower-left canopy" in retrieved["affected_regions"]
    print("      [OK] Data retrieval and JSON field deserialization verified.")

    # Save chat follow-up
    database.save_chat_message(analysis_id, "12345678", "user", "What is the possible problem?")
    database.save_chat_message(analysis_id, "12345678", "assistant", "The visible symptoms match early blight leaf spot.")
    history = database.get_chat_history_for_analysis(analysis_id)
    assert len(history) >= 2
    print("      [OK] Multi-turn chat persistence verified.")

    # Dashboard metrics
    metrics = database.get_dashboard_metrics()
    assert metrics["total_analyses"] >= 1
    print(f"      [OK] Analytics computed: {metrics['total_analyses']} total, {metrics['total_damaged']} damaged.")

    print("[3/4] Testing Telegram Text Formatter...")
    tg_text = report_generator.format_telegram_report(retrieved)
    assert "AGRIVISION REPORT" in tg_text
    assert "Tomato" in tg_text
    assert "20–30%" in tg_text
    print("      [OK] Telegram formatted response verified.")

    print("[4/4] Testing PDF Report Generation...")
    pdf_path = os.path.join(database.UPLOADS_DIR, f"Test_Report_{analysis_id}.pdf")
    generated_pdf = report_generator.generate_pdf_report(retrieved, pdf_path, dummy_img_path)
    assert os.path.exists(generated_pdf) and os.path.getsize(generated_pdf) > 0
    print(f"      [OK] PDF report generated successfully: {pdf_path} ({os.path.getsize(generated_pdf)} bytes)")

    print("\n[SUCCESS] ALL TESTS PASSED! AgriVision Core is fully operational.")

if __name__ == "__main__":
    test_pipeline()

