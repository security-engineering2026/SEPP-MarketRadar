plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }

android { namespace="com.sepp.marketradar"; compileSdk=35
 compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
 kotlinOptions { jvmTarget = "17" }
 defaultConfig { applicationId="com.sepp.marketradar"; minSdk=29; targetSdk=35; versionCode=16120; versionName="16.1.2" }
}
