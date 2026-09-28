import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ai_analyzer
import report_generator

image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "uploads", "crop_7735841586_20260928_152919.jpg")

print("[*] Running analyze_crop_image on user image with meta/llama-3.2-11b-vision-instruct...")
res = ai_analyzer.analyze_crop_image(image_path)

print("\n--- STRUCTURED OUTPUT ---")
print("Crop Identified:", res.get("crop_identified"))
print("Damage Detected:", res.get("damage_detected"))
print("Possible Cause:", res.get("possible_cause"))
print("Severity:", res.get("severity"))
print("Est. Damage %:", res.get("estimated_visible_damage_percentage"))
print("Conditions Favoring Damage:", res.get("conditions_favoring_damage"))
print("Solutions & Remedies:", res.get("solutions_and_remedies"))
print("Visible Symptoms:", res.get("visible_symptoms"))
print("Affected Regions:", res.get("affected_regions"))
print("Next Steps:", res.get("recommended_next_steps"))

print("\n--- FORMATTED TELEGRAM REPORT ---")
report = report_generator.format_telegram_report(res)
# Write to utf-8 file to avoid cp1252 print encoding errors
with open("tests/sample_report_output.txt", "w", encoding="utf-8") as f:
    f.write(report)

print("Report saved to tests/sample_report_output.txt (length:", len(report), ")")
