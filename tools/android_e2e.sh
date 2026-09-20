#!/usr/bin/env bash
set -euo pipefail
APK="android-companion/app/build/outputs/apk/debug/app-debug.apk"
mkdir -p android-qualification
test -f "$APK"

adb start-server >/dev/null
adb wait-for-device
for _ in $(seq 1 60); do
  state="$(adb get-state 2>/dev/null || true)"
  if [ "$state" = "device" ]; then break; fi
  sleep 1
done
test "$(adb get-state)" = "device"

adb install -r "$APK"
adb shell am force-stop com.sepp.marketradar || true
adb shell am start -n com.sepp.marketradar/.MainActivity >/tmp/marketradar-android-start.txt 2>&1 || {
  adb logcat -d -t 300 > android-qualification/logcat-start-failure.txt || true
  cat /tmp/marketradar-android-start.txt
  exit 1
}
sleep 5
if ! adb shell pidof com.sepp.marketradar >/dev/null 2>&1; then
  adb logcat -d -t 300 > android-qualification/logcat-process-failure.txt || true
  exit 1
fi
adb shell dumpsys package com.sepp.marketradar | grep -E 'versionName=16.1.1|versionCode=16110'
printf '%s
' 'ANDROID_E2E=PASS' | tee android-qualification/result.txt
