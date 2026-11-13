"""Convert the tearsgram logo into Icon Composer's 1024 px PNG input on macOS."""
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "branding/AppIcon-1024.png"
destination = root / "Telegram/Telegram-iOS/Swiftgram.icon/Assets/ModIcon.png"
if not source.exists():
    raise SystemExit(f"Missing {source}. Run: python tools/make_branding.py")
destination.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(
    ["sips", "-s", "format", "png", "--resampleHeightWidth", "1024", "1024", str(source), "--out", str(destination)],
    check=True,
)
print(f"Primary icon written from {source.name} to {destination.relative_to(root)}")