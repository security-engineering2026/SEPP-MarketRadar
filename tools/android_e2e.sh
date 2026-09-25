#!/usr/bin/env bash
set -euo pipefail
APK="android-companion/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE="com.sepp.marketradar"
ACTIVITY="$PACKAGE/.MainActivity"
mkdir -p android-qualification
test -f "$APK"

adb install -r "$APK"

launched=0
for _ in $(seq 1 6); do
  adb shell am force-stop "$PACKAGE" || true
  if adb shell am start -W -n "$ACTIVITY" > android-qualification/launch.txt 2>&1; then
    if adb shell dumpsys activity activities | grep -q "$ACTIVITY"; then
      launched=1
      break
    fi
  fi
  sleep 5
done

if [ "$launched" -ne 1 ]; then
  adb shell dumpsys activity activities > android-qualification/activity-dump.txt || true
  adb logcat -d -t 500 > android-qualification/logcat.txt || true
  echo "ANDROID_E2E=FAIL: MainActivity did not become the resumed/active activity" >&2
  exit 1
fi

adb shell dumpsys package "$PACKAGE" | grep -E 'versionName=16\.1\.2|versionCode=16120'
printf '%s\n' 'ANDROID_E2E=PASS' | tee android-qualification/result.txt
