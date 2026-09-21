#!/usr/bin/env bash
set -euo pipefail
APK="android-companion/app/build/outputs/apk/debug/app-debug.apk"
mkdir -p android-qualification
test -f "$APK"

adb_cmd() {
  local limit="$1"; shift
  timeout "$limit" adb "$@"
}

adb_cmd 30 start-server >/dev/null
state=""
for i in $(seq 1 180); do
  state="$(adb_cmd 10 get-state 2>/dev/null || true)"
  if [ "$state" = "device" ]; then break; fi
  if [ "$state" = "offline" ]; then
    adb_cmd 15 reconnect offline >/dev/null 2>&1 || true
    if [ $((i % 10)) -eq 0 ]; then
      adb_cmd 30 kill-server >/dev/null 2>&1 || true
      sleep 2
      adb_cmd 30 start-server >/dev/null 2>&1 || true
    fi
  else
    adb_cmd 30 start-server >/dev/null 2>&1 || true
  fi
  sleep 1
done
if [ "$state" != "device" ]; then
  adb_cmd 15 devices -l > android-qualification/adb-devices-failure.txt || true
  adb_cmd 30 logcat -d -t 500 > android-qualification/logcat-device-failure.txt || true
  echo "ANDROID_E2E_DEVICE_NOT_READY state=$state" >&2
  exit 1
fi

boot=""
for _ in $(seq 1 180); do
  boot="$(adb_cmd 15 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
  if [ "$boot" = "1" ]; then break; fi
  sleep 1
done
if [ "$boot" != "1" ]; then
  adb_cmd 15 devices -l > android-qualification/adb-boot-failure.txt || true
  adb_cmd 30 logcat -d -t 500 > android-qualification/logcat-boot-failure.txt || true
  echo "ANDROID_E2E_BOOT_NOT_COMPLETE value=$boot" >&2
  exit 1
fi

install_ok=""
for attempt in 1 2; do
  if timeout 180s adb install -r "$APK"; then
    install_ok=1
    break
  fi
  adb_cmd 15 reconnect >/dev/null 2>&1 || true
  sleep 2
done
if [ "$install_ok" != "1" ]; then
  adb_cmd 30 logcat -d -t 500 > android-qualification/logcat-install-failure.txt || true
  echo "ANDROID_E2E_INSTALL_FAILED" >&2
  exit 1
fi

adb_cmd 20 shell am force-stop com.sepp.marketradar || true
start_output="$(mktemp)"
if ! timeout 60s adb shell am start -n com.sepp.marketradar/.MainActivity >"$start_output" 2>&1; then
  adb_cmd 30 logcat -d -t 500 > android-qualification/logcat-start-failure.txt || true
  cat "$start_output"
  rm -f "$start_output"
  exit 1
fi
rm -f "$start_output"
process_ready=""
for _ in $(seq 1 60); do
  if timeout 15s adb shell pidof com.sepp.marketradar >/dev/null 2>&1; then
    process_ready="1"
    break
  fi
  sleep 1
done
if [ "$process_ready" != "1" ]; then
  adb_cmd 30 shell dumpsys activity activities > android-qualification/activity-process-failure.txt || true
  adb_cmd 30 logcat -d -t 500 > android-qualification/logcat-process-failure.txt || true
  echo "ANDROID_E2E_PROCESS_NOT_READY" >&2
  exit 1
fi
timeout 60s adb shell dumpsys package com.sepp.marketradar | grep -E 'versionName=16\.1\.1|versionCode=16110'
printf '%s\n' 'ANDROID_E2E=PASS' | tee android-qualification/result.txt
