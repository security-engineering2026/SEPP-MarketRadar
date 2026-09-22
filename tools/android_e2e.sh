#!/usr/bin/env bash
set -euo pipefail
APK="android-companion/app/build/outputs/apk/debug/app-debug.apk"
mkdir -p android-qualification
test -f "$APK"
adb install -r "$APK"
adb shell am force-stop com.sepp.marketradar || true
adb shell monkey -p com.sepp.marketradar 1 >/dev/null
sleep 3
adb shell dumpsys package com.sepp.marketradar | grep -E 'versionName=16\.1\.2|versionCode=16120'
adb shell pidof com.sepp.marketradar >/dev/null
printf '%s\n' 'ANDROID_E2E=PASS' | tee android-qualification/result.txt
