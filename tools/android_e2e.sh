#!/usr/bin/env bash
set -euo pipefail
APK="android-companion/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE="com.sepp.marketradar"
mkdir -p android-qualification
test -f "$APK"

adb install -r "$APK"
adb shell am force-stop "$PACKAGE" || true
adb shell monkey -p "$PACKAGE" 1 >/dev/null

for _ in $(seq 1 30); do
  if adb shell pidof "$PACKAGE" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! adb shell pidof "$PACKAGE" >/dev/null 2>&1; then
  adb shell dumpsys activity activities > android-qualification/activity-dump.txt || true
  adb logcat -d -t 500 > android-qualification/logcat.txt || true
  echo "ANDROID_E2E=FAIL: package process did not become ready" >&2
  exit 1
fi

adb shell dumpsys package "$PACKAGE" | grep -E 'versionName=16\.1\.2|versionCode=16120'
printf '%s\n' 'ANDROID_E2E=PASS' | tee android-qualification/result.txt
