package pl.lozyska.kiosk

import android.content.Context
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Kopia ostatniej udanej odpowiedzi serwera, trzymana jako trzy pliki JSON
 * w pamieci wewnetrznej apki.
 *
 * Dlaczego pliki, a nie baza: apka tylko CZYTA. Nie ma wlasnych zmian do
 * pogodzenia z serwerem, wiec cala warstwa bazy (schemat, migracje, znaczniki
 * czasu) nie mialaby czego pilnowac. Trzy pliki i data - tyle wystarczy, zeby
 * mapa byla widoczna przy padnietym wi-fi.
 */
object Schowek {

    class Kopia(val skrytki: String, val lozyska: String, val ruchy: String, val kiedy: String)

    private const val PLIK_SKRYTKI = "skrytki.json"
    private const val PLIK_LOZYSKA = "lozyska.json"
    private const val PLIK_RUCHY = "ruchy.json"
    private const val PLIK_DATA = "pobrano.txt"

    fun teraz(): String =
        SimpleDateFormat("dd.MM HH:mm", Locale.getDefault()).format(Date())

    fun zapisz(kontekst: Context, skrytki: String, lozyska: String, ruchy: String) {
        zapiszPlik(kontekst, PLIK_SKRYTKI, skrytki)
        zapiszPlik(kontekst, PLIK_LOZYSKA, lozyska)
        zapiszPlik(kontekst, PLIK_RUCHY, ruchy)
        zapiszPlik(kontekst, PLIK_DATA, teraz())
    }

    fun odczytaj(kontekst: Context): Kopia? {
        val skrytki = odczytajPlik(kontekst, PLIK_SKRYTKI) ?: return null
        val lozyska = odczytajPlik(kontekst, PLIK_LOZYSKA) ?: return null
        val ruchy = odczytajPlik(kontekst, PLIK_RUCHY) ?: "[]"
        val kiedy = odczytajPlik(kontekst, PLIK_DATA) ?: "?"
        return Kopia(skrytki, lozyska, ruchy, kiedy)
    }

    private fun zapiszPlik(kontekst: Context, nazwa: String, tresc: String) {
        // Zapis przez plik tymczasowy i podmiane nazwy: gdyby tablet stracil
        // zasilanie w polowie zapisu, stara kopia zostaje cala zamiast zamienic
        // sie w obciety JSON, ktorego i tak nie dalo by sie odczytac.
        val docelowy = File(kontekst.filesDir, nazwa)
        val tymczasowy = File(kontekst.filesDir, "$nazwa.tmp")
        tymczasowy.writeText(tresc, Charsets.UTF_8)
        if (docelowy.exists()) docelowy.delete()
        tymczasowy.renameTo(docelowy)
    }

    private fun odczytajPlik(kontekst: Context, nazwa: String): String? {
        val plik = File(kontekst.filesDir, nazwa)
        return if (plik.exists()) plik.readText(Charsets.UTF_8) else null
    }
}
