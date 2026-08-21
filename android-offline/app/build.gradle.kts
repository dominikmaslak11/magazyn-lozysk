import groovy.json.JsonSlurper
// Import jawny: w skrypcie Gradle 'java' to rozszerzenie projektu, które przesłania
// pakiet java.*, więc zapis java.util.Properties() się nie kompiluje.
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.ksp)
    alias(libs.plugins.kotlin.compose)
}

// ---------------------------------------------------------------- wariant taty --
//
// Wersja dla telefonu, który NIE jest w tailnecie: adres serwera i token są wkompilowane,
// więc użytkownik nie konfiguruje niczego. Jedno i drugie czytamy z plików POZA
// repozytorium, żeby token nie trafił do gita - nawet gdy repo zostaje publiczne.
//
//   ~/.lozyska_data/tokeny.json             -> {"tata": "<token>"}   (python tokeny.py --dodaj tata)
//   ~/.lozyska_data/tata-build.properties   -> serverUrl=https://...
//
// Brak plików psuje TYLKO wariant 'tata'; wariant 'moje' buduje się normalnie.

val katalogDanych = File(System.getProperty("user.home"), ".lozyska_data")

fun tokenTaty(): String? {
    val plik = File(katalogDanych, "tokeny.json")
    if (!plik.exists()) return null
    @Suppress("UNCHECKED_CAST")
    val mapa = JsonSlurper().parse(plik) as? Map<String, Any?> ?: return null
    return (mapa["tata"] as? String)?.trim()?.takeIf { it.isNotEmpty() }
}

fun adresDlaTaty(): String? {
    val plik = File(katalogDanych, "tata-build.properties")
    if (!plik.exists()) return null
    val p = Properties().apply { plik.inputStream().use { load(it) } }
    return p.getProperty("serverUrl")?.trim()?.takeIf { it.isNotEmpty() }
}

android {
    namespace = "pl.lozyska.offline"
    compileSdk = 34

    defaultConfig {
        applicationId = "pl.lozyska.offline"
        minSdk = 24
        targetSdk = 34
        versionCode = 14
        versionName = "1.13.0"
    }

    flavorDimensions += "odbiorca"
    productFlavors {
        create("moje") {
            dimension = "odbiorca"
            isDefault = true
            // Zachowanie bez zmian: adres i token wpisuje się w ekranie Dane.
            buildConfigField("String", "ZASZYTY_ADRES", "\"\"")
            buildConfigField("String", "ZASZYTY_TOKEN", "\"\"")
            buildConfigField("boolean", "KONFIGURACJA_ZASZYTA", "false")
        }
        create("tata") {
            dimension = "odbiorca"
            // Osobny applicationId, żeby obie wersje dały się mieć na jednym telefonie
            // (przydaje się do sprawdzenia wariantu taty przed wgraniem mu go).
            applicationIdSuffix = ".tata"
            // Nazwa appki jest w app/src/tata/res/values/strings.xml - zestaw źródeł wariantu
            // przesłania main. resValue() by tu nie zadziałało: zderzyłoby się z app_name z main.

            val token = tokenTaty()
            val adres = adresDlaTaty()
            // Pusta wartość zamiast błędu: dzięki temu ./gradlew tasks i synchronizacja
            // w Android Studio działają bez tych plików. Brak wykrywamy przy pakowaniu.
            buildConfigField("String", "ZASZYTY_ADRES", "\"${adres ?: ""}\"")
            buildConfigField("String", "ZASZYTY_TOKEN", "\"${token ?: ""}\"")
            buildConfigField("boolean", "KONFIGURACJA_ZASZYTA", "true")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

// Wariant taty spakowany bez konfiguracji dałby APK, które po instalacji nie łączy się
// z niczym - i którego NIE DA SIĘ naprawić z telefonu, bo ekran ustawień jest tam ukryty.
// Lepiej zatrzymać budowanie z czytelnym komunikatem niż wydać taką paczkę.
tasks.matching { it.name.startsWith("assembleTata") || it.name.startsWith("bundleTata") }
    .configureEach {
        doFirst {
            val braki = buildList {
                if (tokenTaty() == null)
                    add("token 'tata' w ~/.lozyska_data/tokeny.json" +
                        "  ->  python tokeny.py --dodaj tata")
                if (adresDlaTaty() == null)
                    add("serverUrl w ~/.lozyska_data/tata-build.properties" +
                        "  ->  serverUrl=https://nazwa.ts.net")
            }
            if (braki.isNotEmpty())
                error("Brak konfiguracji wariantu 'tata':\n  - " + braki.joinToString("\n  - "))
        }
    }

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.material.icons.extended)
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0")

    implementation(libs.androidx.room.runtime)
    ksp(libs.androidx.room.compiler)
    implementation(libs.androidx.room.ktx)

    implementation("com.squareup.okhttp3:okhttp:4.11.0")
    implementation("com.google.code.gson:gson:2.10.1")
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("androidx.navigation:navigation-compose:2.7.7")
    implementation("androidx.datastore:datastore-preferences:1.0.0")
    implementation("androidx.work:work-runtime-ktx:2.9.0")

    // Skanowanie kodów QR/kreskowych (offline, on-device - bez wysyłania obrazu do internetu)
    implementation("androidx.camera:camera-core:1.3.4")
    implementation("androidx.camera:camera-camera2:1.3.4")
    implementation("androidx.camera:camera-lifecycle:1.3.4")
    implementation("androidx.camera:camera-view:1.3.4")
    implementation("com.google.mlkit:barcode-scanning:17.3.0")

    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
}
