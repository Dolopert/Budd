#!/bin/bash
# Install Pixel Pet as a macOS LaunchAgent so it auto-runs at login.
# Uninstall with:  ./install_autostart.sh --uninstall
set -e
cd "$(dirname "$0")"

LABEL="com.pixelpet.pet"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
RUN_SH="$(pwd)/run.sh"

if [ "$1" = "--uninstall" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Removed auto-start ($PLIST)."
  exit 0
fi

chmod +x run.sh

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$RUN_SH</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "Installed auto-start: Pixel Pet will launch at login."
echo "Plist: $PLIST"
