import java.util.Properties

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// 업로드 키 설정. 실제 값이 든 `android/key.properties` 와 `.jks` 는 커밋하지
// 않는다(key.properties.example 참고). 워크플로가 secret 으로 만들어 준다.
val keystoreProperties =
    Properties().apply {
        val file = rootProject.file("key.properties")
        if (file.exists()) {
            file.inputStream().use { load(it) }
        }
    }

android {
    namespace = "com.dosaem.chosung"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        // flutter_local_notifications 10+ 는 **알림 예약을 안 쓰더라도** 소비하는
        // 앱이 core library desugaring 을 켜두기를 요구한다. 없으면 Dart 테스트는
        // 다 통과한 채 `checkDebugAarMetadata` 가 "requires core library
        // desugaring to be enabled for :app" 으로 Android 빌드를 막는다.
        // 아래 sourceCompatibility 17 은 Java 언어 수준일 뿐, 이 플래그와는 별개다.
        isCoreLibraryDesugaringEnabled = true
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

    signingConfigs {
        if (keystoreProperties.isNotEmpty()) {
            create("release") {
                // storeFile 은 이 모듈(app/) 기준 경로다 — 워크플로가 받아쓰는
                // `android/app/upload-keystore.jks` 와 같은 자리.
                storeFile = file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            // key.properties 가 없으면 디버그 키로 서명한다. 그래야 keystore 가
            // 없는 로컬·새 클론에서도 `flutter run --release` 와 `build apk
            // --release` 가 돈다. 스토어로 가는 빌드는 워크플로가 secret 으로
            // key.properties 를 만들어 주므로 반드시 release 설정을 탄다
            // (secret 이 없으면 워크플로가 빌드 전에 멈춘다).
            signingConfig = signingConfigs.findByName("release") ?: signingConfigs.getByName("debug")

            ndk {
                // 네이티브 심볼을 AAB 에 담아 Play 콘솔이 크래시를 주소가 아니라
                // 함수 이름으로 보여주게 한다. flutter tool 이 이때 스트립 오탐으로
                // exit 1 을 주는 것은 워크플로의 AAB 스텝에서 처리한다.
                debugSymbolLevel = "FULL"
            }
        }
    }
}

dependencies {
    // 위 isCoreLibraryDesugaringEnabled 와 한 쌍이다 — 플래그만 켜면 빌드가 깨진다.
    // 버전은 flutter_local_notifications 22.3.2 의 android/build.gradle 이 요구하는
    // 값과 맞춘다(test/config/android_desugaring_test.dart 가 지킨다).
    // minSdk 24 라서 multidex 는 AGP 가 기본으로 켜준다 — 따로 선언하지 않는다.
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
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
