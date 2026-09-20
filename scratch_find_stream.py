with open("apps/web/src/app/page.tsx", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "MATERIAL CORPORATE EVENT STREAM" in line or "WHY FLAGGED BY MATERIALITY ENGINE" in line:
        print(f"Line {idx+1}: {line.strip()[:100]}")
