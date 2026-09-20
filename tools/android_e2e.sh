#!/usr/bin/env bash
set -euo pipefail
APK="android-companion/app/build/outputs/apk/debug/app-debug.apk"
mkdir -p android-qualification
test -f "$APK"

adb start-server >/dev/null
state=""
for i in $(seq 1 180); do
  state="$(adb get-state 2>/dev/null || true)"
  if [ "$state" = "device" ]; then break; fi
  if [ "$state" = "offline" ]; then
    adb reconnect offline >/dev/null 2>&1 || true
    if [ $((i % 10)) -eq 0 ]; then
      adb kill-server >/dev/null 2>&1 || true
      sleep 2
      adb start-server >/dev/null 2>&1 || true
    fi
  else
    adb start-server >/dev/null 2>&1 || true
  fi
  sleep 1
done
if [ "$state" != "device" ]; then
  adb devices -l > android-qualification/adb-devices-failure.txt || true
  adb logcat -d -t 500 > android-qualification/logcat-device-failure.txt || true
  echo "ANDROID_E2E_DEVICE_NOT_READY state=$state" >&2
  exit 1
fi

boot=""
for _ in $(seq 1 180); do
  boot="$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
  if [ "$boot" = "1" ]; then break; fi
  sleep 1
done
if [ "$boot" != "1" ]; then
  adb devices -l > android-qualification/adb-boot-failure.txt || true
  adb logcat -d -t 500 > android-qualification/logcat-boot-failure.txt || true
  echo "ANDROID_E2E_BOOT_NOT_COMPLETE value=$boot" >&2
  exit 1
fi

adb install -r "$APK"
adb shell am force-stop com.sepp.marketradar || true
adb shell am start -n com.sepp.marketradar/.MainActivity >/tmp/marketradar-android-start.txt 2>&1 || {
  adb logcat -d -t 500 > android-qualification/logcat-start-failure.txt || true
  cat /tmp/marketradar-android-start.txt
  exit 1
}
sleep 5
if ! adb shell pidof com.sepp.marketradar >/dev/null 2>&1; then
  adb logcat -d -t 500 > android-qualification/logcat-process-failure.txt || true
  exit 1
fi
adb shell dumpsys package com.sepp.marketradar | grep -E 'versionName=16\.1\.1|versionCode=16110'
printf '%s\n' 'ANDROID_E2E=PASS' | tee android-qualification/result.txt
