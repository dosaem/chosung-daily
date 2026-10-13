plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.dosaem.chosung"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        applicationId = "com.dosaem.chosung"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // 출시 서명(keystore·match)은 티켓 32 가 넣는다. 그때까지는 디버그 키로
            // 서명해 `flutter run --release` 가 돌게만 해둔다.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

flutter {
    source = "../.."
}

// Firebase 설정 파일은 커밋하지 않는다(google-services.json.example 참고).
// 파일이 없으면 google-services 플러그인을 적용하지 않는다 — 적용하면
// "File google-services.json is missing" 으로 빌드가 멈춰서, 새로 클론한
// 로컬과 CI 에서 디버그 빌드조차 못 하게 된다. 런타임에서도 Firebase
// 초기화를 건너뛴다(lib/config/firebase_bootstrap.dart).
if (file("google-services.json").exists()) {
    apply(plugin = "com.google.gms.google-services")
} else {
    logger.lifecycle("google-services.json 이 없어 Firebase 플러그인을 건너뜁니다.")
}
