# Würfelspiel 10000

Kivy-basiertes Würfelspiel für Android.

## Dateien im Repository
- `main.py` – Spielcode
- `buildozer.spec` – Build-Konfiguration für Android
- `.github/workflows/build_apk_robust.yml` – GitHub Actions Workflow zum Erzeugen der APK
- `requirements.txt` – Python-Pakete für den Build

## Lokaler Build (Linux / WSL2)
1. Ubuntu/WSL2 oder Linux verwenden.
2. Systemabhängigkeiten installieren:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip git zip unzip openjdk-17-jdk build-essential libgl1