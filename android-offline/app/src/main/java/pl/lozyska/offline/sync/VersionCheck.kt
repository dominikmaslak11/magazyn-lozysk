package pl.lozyska.offline.sync

/** Adres, pod którym użytkownik znajdzie najnowszy build appki (repo jest open source). */
const val RELEASES_URL = "https://github.com/dominikmaslak11/magazyn-lozysk/releases/latest"

/**
 * Porównuje dwie wersje w formacie "1.2.3" (dowolna liczba segmentów, brakujące = 0).
 * Zwraca <0 gdy a < b, 0 gdy równe, >0 gdy a > b.
 */
fun compareVersions(a: String, b: String): Int {
    val partsA = a.trim().split(".").map { it.toIntOrNull() ?: 0 }
    val partsB = b.trim().split(".").map { it.toIntOrNull() ?: 0 }
    val len = maxOf(partsA.size, partsB.size)
    for (i in 0 until len) {
        val x = partsA.getOrElse(i) { 0 }
        val y = partsB.getOrElse(i) { 0 }
        if (x != y) return x - y
    }
    return 0
}

/** Appka jest za stara, żeby bezpiecznie synchronizować się z tym serwerem. */
fun isClientOutdated(clientVersion: String, minClientVersion: String?): Boolean {
    if (minClientVersion.isNullOrBlank()) return false
    return compareVersions(clientVersion, minClientVersion) < 0
}

/** Serwer zgłasza nowszą appkę niż ta zainstalowana - warto zaktualizować, ale nie jest to wymagane. */
fun isUpdateAvailable(clientVersion: String, serverVersion: String?): Boolean {
    if (serverVersion.isNullOrBlank()) return false
    return compareVersions(clientVersion, serverVersion) < 0
}
