import groovy.json.JsonSlurper
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

// --------------------------------------------------------------------------
// Konfiguracja zaszywana przy budowaniu, tak samo jak w wariancie "tata".
// Oba pliki leza POZA repozytorium (~/.lozyska_data), wiec token nie trafia
// do gita, mimo ze jest w APK.
//
// Po co zaszywac zamiast ekranu ustawien: to tablet na regale z Androidem 4.4.
// Wpisywanie 32-znakowego tokenu palcem na takim ekranie jest karą, a apka ma
// byc "maksymalnie prosta" - wlaczasz i dziala.
// --------------------------------------------------------------------------
val katalogDanych = File(System.getProperty("user.home"), ".lozyska_data")

fun brakKonfiguracji(co: String, gdzie: File): Nothing = throw GradleException(
    "Brak konfiguracji tabletu: $co.\n" +
        "Oczekiwano w: ${gdzie.absolutePath}\n" +
        "APK bez tego nie polaczy sie z niczym, a ekranu ustawien w nim nie ma - " +
        "dlatego budowa zatrzymuje sie tutaj, a nie na tablecie."
)

fun tokenTabletu(): String {
    val plik = File(katalogDanych, "tokeny.json")
    if (!plik.exists()) brakKonfiguracji("plik tokenow nie istnieje", plik)
    @Suppress("UNCHECKED_CAST")
    val mapa = JsonSlurper().parse(plik) as Map<String, Any?>
    val token = mapa["tablet"]?.toString()?.trim().orEmpty()
    if (token.isEmpty()) brakKonfiguracji("brak klucza \"tablet\" w tokeny.json", plik)
    return token
}

fun adresSerwera(): String {
    val plik = File(katalogDanych, "tablet-build.properties")
    if (!plik.exists()) brakKonfiguracji("brak tablet-build.properties", plik)
    val props = Properties()
    plik.inputStream().use { props.load(it) }
    val adres = props.getProperty("serverUrl")?.trim().orEmpty()
    if (adres.isEmpty()) brakKonfiguracji("brak wpisu serverUrl", plik)
    return adres.trimEnd('/')
}

android {
    namespace = "pl.lozyska.kiosk"
    compileSdk = 34

    defaultConfig {
        applicationId = "pl.lozyska.kiosk"
        // Lenovo A3000-H na regale: Android 4.2.2, czyli API 17. Nie 19 - tablet
        // okazal sie starszy, niz wynikalo z opisu, a INSTALL_FAILED_OLDER_SDK
        // przy 19 to potwierdzil.
        minSdk = 17
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

        buildConfigField("String", "ADRES", "\"${adresSerwera()}\"")
        buildConfigField("String", "TOKEN", "\"${tokenTabletu()}\"")
    }

    buildFeatures { buildConfig = true }

    buildTypes {
        release { isMinifyEnabled = false }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    kotlinOptions { jvmTarget = "1.8" }
    lint { disable += "OldTargetApi" }
}

// ZADNYCH zaleznosci androidx i zadnego Compose. Compose wymaga minSdk 21, a nowsze
// androidx - 19 albo 21 zaleznie od biblioteki; mieszanie ich z API 19 wychodzi
// dopiero przy scalaniu manifestu. Wszystko, czego ta apka potrzebuje - Activity,
// uklady XML, HttpURLConnection i org.json - jest w samej platformie Androida.
dependencies { }
