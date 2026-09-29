package pl.lozyska.kiosk

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

/**
 * Model i pobieranie danych. Wszystko na org.json i HttpURLConnection, bo jedno
 * i drugie jest w platformie od API 1 - zadnych bibliotek, ktore moglyby nie
 * wejsc na Androida 4.4.
 *
 * Apka jest TYLKO DO ODCZYTU. Nie zapisuje niczego na serwer, wiec nie ma tu
 * ani synchronizacji, ani dziennika ruchow, ani rozwiazywania konfliktow -
 * to celowo najprostszy mozliwy ksztalt.
 */

class Skrytka(
    val nazwa: String,
    val polka: Int,
    val dMin: Double?,
    val dMax: Double?,
) {
    /** "30-37", "160+", "0-30" - to samo, co stoi na naklejkach skrytek. */
    fun zakres(): String {
        if (dMin == null && dMax == null) return ""
        if (dMax == null) return "${liczba(dMin!!)}+"
        if (dMin == null || dMin == 0.0) return "0-${liczba(dMax)}"
        return "${liczba(dMin)}-${liczba(dMax)}"
    }

    /** Czy lozysko o tej srednicy pasuje do zakresu tej skrytki. */
    fun miesciSie(dZew: Double?): Boolean {
        if (dZew == null) return false
        if (dMin == null && dMax == null) return false
        val od = dMin ?: Double.NEGATIVE_INFINITY
        val doo = dMax ?: Double.POSITIVE_INFINITY
        return dZew >= od && dZew < doo
    }
}

class Lozysko(
    // id, regalId, recznyPrzydzial i zrodlo sa potrzebne WYLACZNIE do zapisu:
    // PUT /api/bearings/<id> podmienia CALY rekord, wiec trzeba odeslac wszystko
    // z powrotem. Pominiecie recznyPrzydzial przerzucilo by lozysko do innej
    // skrytki, a pominiecie uwag skasowalo by opis zastosowania.
    val id: String,
    val regalId: String?,
    val recznyPrzydzial: Boolean,
    val zrodlo: String,
    val symbol: String,
    val typ: String,
    // Nazwy dZew i b, a NIE D i B: na JVM "d" i "D" daja ta sama sygnature getD(),
    // wiec Kotlin odmawia kompilacji. Ten sam powod, dla ktorego kolumny w bazie
    // appki glownej nazywaja sie d / dZew / b.
    val d: Double?,
    val dZew: Double?,
    val b: Double?,
    val ilosc: Int,
    val skrytka: String,
    val uwagi: String,
) {
    fun wymiary(): String =
        if (d == null || dZew == null) "—" else "${liczba(d)}x${liczba(dZew)}x${liczba(b ?: 0.0)}"
}

class Ruch(val symbol: String, val delta: Int, val kiedy: String)

class Magazyn(
    val skrytki: List<Skrytka>,
    val lozyska: List<Lozysko>,
    val ruchy: List<Ruch>,
    val zeSchowka: Boolean,
    val pobrano: String,
)

/** Bez miejsc po przecinku, gdy liczba jest calkowita: 52.0 -> "52", 58.738 -> "58.7". */
fun liczba(v: Double): String =
    if (v == Math.floor(v) && !v.isInfinite()) v.toLong().toString()
    else String.format("%.1f", v)

object Serwer {

    private const val CZAS_POLACZENIA = 6000
    private const val CZAS_ODCZYTU = 8000

    /**
     * Zmienia ilosc o `delta`. Serwer zamienia to na wpis w dzienniku ruchow -
     * ilosc NIGDY nie jest nadpisywana wartoscia bezwzgledna, wiec historia
     * zostaje kompletna niezaleznie od tego, czy zmiana przyszla z tabletu,
     * telefonu czy przegladarki.
     *
     * Odsylamy WSZYSTKIE pola, bo PUT podmienia caly rekord.
     */
    fun zmienIlosc(l: Lozysko, delta: Int) {
        val nowa = l.ilosc + delta
        if (nowa < 0) return
        val tresc = JSONObject()
        tresc.put("symbol", l.symbol)
        tresc.put("typ", l.typ)
        if (l.d != null) tresc.put("d", l.d) else tresc.put("d", JSONObject.NULL)
        if (l.dZew != null) tresc.put("D", l.dZew) else tresc.put("D", JSONObject.NULL)
        if (l.b != null) tresc.put("B", l.b) else tresc.put("B", JSONObject.NULL)
        tresc.put("ilosc", nowa)
        tresc.put("zrodlo", l.zrodlo)
        tresc.put("uwagi", l.uwagi)
        tresc.put("regal_id", l.regalId ?: JSONObject.NULL)
        tresc.put("reczny_przydzial", l.recznyPrzydzial)
        wyslij("/api/bearings/" + l.id, tresc.toString())
    }

    private fun wyslij(sciezka: String, tresc: String) {
        val polaczenie = URL(BuildConfig.ADRES + sciezka).openConnection() as HttpURLConnection
        polaczenie.connectTimeout = CZAS_POLACZENIA
        polaczenie.readTimeout = CZAS_ODCZYTU
        polaczenie.requestMethod = "PUT"
        polaczenie.doOutput = true
        polaczenie.setRequestProperty("X-Auth-Token", BuildConfig.TOKEN)
        polaczenie.setRequestProperty("Content-Type", "application/json; charset=utf-8")
        try {
            polaczenie.outputStream.use { it.write(tresc.toByteArray(Charsets.UTF_8)) }
            val kod = polaczenie.responseCode
            if (kod != 200) throw RuntimeException("Serwer odpowiedzial $kod")
        } finally {
            polaczenie.disconnect()
        }
    }

    private fun pobierz(sciezka: String): String {
        val polaczenie = URL(BuildConfig.ADRES + sciezka).openConnection() as HttpURLConnection
        polaczenie.connectTimeout = CZAS_POLACZENIA
        polaczenie.readTimeout = CZAS_ODCZYTU
        // Naglowek X-Auth-Token, a nie Authorization: oba dziala, ale ten jest
        // krotszy i serwer sprawdza go pierwszy (patrz _token_from_request).
        polaczenie.setRequestProperty("X-Auth-Token", BuildConfig.TOKEN)
        try {
            val kod = polaczenie.responseCode
            if (kod == 401) throw RuntimeException("Serwer odrzucil token tabletu (401)")
            if (kod != 200) throw RuntimeException("Serwer odpowiedzial $kod")
            return BufferedReader(InputStreamReader(polaczenie.inputStream, "UTF-8")).use {
                it.readText()
            }
        } finally {
            polaczenie.disconnect()
        }
    }

    private fun liczbaLubNull(o: JSONObject, klucz: String): Double? =
        if (o.isNull(klucz)) null else o.optDouble(klucz)

    // Skrytki wisza bezposrednio pod regalem (od 30.09 bez wezlow "Polka N"),
    // wiec rzad wynika z liczby na poczatku nazwy: "9L" -> 9.
    private fun numerZNazwy(nazwa: String): Int =
        nazwa.takeWhile { it.isDigit() }.toIntOrNull() ?: 0

    private fun skrytkiZJson(tekst: String): List<Skrytka> {
        val tablica = JSONArray(tekst)
        // Najpierw mapa id -> poziom polki, zeby wiedziec, w ktorym rzedzie
        // narysowac skrytke. Skrytka zna tylko swojego rodzica.
        val poziomPolki = HashMap<String, Int>()
        for (i in 0 until tablica.length()) {
            val o = tablica.getJSONObject(i)
            if (o.optString("poziom_typ") == "półka") {
                poziomPolki[o.optString("id")] = o.optInt("poziom")
            }
        }
        val wynik = ArrayList<Skrytka>()
        for (i in 0 until tablica.length()) {
            val o = tablica.getJSONObject(i)
            if (o.optString("poziom_typ") != "skrytka") continue
            wynik.add(
                Skrytka(
                    nazwa = o.optString("nazwa"),
                    polka = poziomPolki[o.optString("parent_id")]
                        ?: numerZNazwy(o.optString("nazwa")),
                    dMin = liczbaLubNull(o, "d_min"),
                    dMax = liczbaLubNull(o, "d_max"),
                )
            )
        }
        // Polka 9 na gorze, polka 1 na dole - tak jak stoi regal. W obrebie polki
        // najpierw L, potem P (alfabetycznie sie zgadza).
        wynik.sortWith(compareByDescending<Skrytka> { it.polka }.thenBy { it.nazwa })
        return wynik
    }

    private fun lozyskaZJson(tekst: String): List<Lozysko> {
        val tablica = JSONArray(tekst)
        val wynik = ArrayList<Lozysko>()
        for (i in 0 until tablica.length()) {
            val o = tablica.getJSONObject(i)
            wynik.add(
                Lozysko(
                    id = o.optString("id"),
                    regalId = if (o.isNull("regal_id")) null else o.optString("regal_id"),
                    recznyPrzydzial = o.optBoolean("reczny_przydzial"),
                    zrodlo = o.optString("zrodlo"),
                    symbol = o.optString("symbol"),
                    typ = o.optString("typ"),
                    d = liczbaLubNull(o, "d"),
                    dZew = liczbaLubNull(o, "D"),
                    b = liczbaLubNull(o, "B"),
                    ilosc = o.optInt("ilosc"),
                    skrytka = o.optString("regal_nazwa"),
                    uwagi = o.optString("uwagi"),
                )
            )
        }
        wynik.sortWith(compareBy { it.symbol.lowercase() })
        return wynik
    }

    private fun ruchyZJson(tekst: String): List<Ruch> {
        val tablica = JSONArray(tekst)
        val wynik = ArrayList<Ruch>()
        for (i in 0 until tablica.length()) {
            val o = tablica.getJSONObject(i)
            val kiedy = o.optString("applied_at")
            wynik.add(
                Ruch(
                    symbol = o.optString("symbol"),
                    delta = o.optInt("delta"),
                    // "2026-09-07T13:45:53.812+00:00" -> "09-07 13:45"
                    kiedy = if (kiedy.length >= 16) kiedy.substring(5, 10) + " " + kiedy.substring(11, 16) else kiedy,
                )
            )
        }
        // Najnowsze u gory. Serwer zwraca posortowane malejaco, ale nie polegamy na tym.
        wynik.sortWith(compareByDescending { it.kiedy })
        return wynik
    }

    /**
     * Pobiera komplet z serwera i odklada kopie na dysk. Gdy serwer jest
     * nieosiagalny, zwraca ostatnia kopie z oznaczeniem `zeSchowka = true`.
     * Tablet na regale ma pokazywac mape takze wtedy, gdy padnie wi-fi -
     * nieaktualna mapa jest duzo lepsza niz pusty ekran.
     */
    fun wczytaj(kontekst: Context): Magazyn {
        return try {
            val skrytki = pobierz("/api/shelves")
            val lozyska = pobierz("/api/bearings")
            val ruchy = pobierz("/api/stock-moves")
            Schowek.zapisz(kontekst, skrytki, lozyska, ruchy)
            Magazyn(
                skrytkiZJson(skrytki), lozyskaZJson(lozyska), ruchyZJson(ruchy),
                zeSchowka = false, pobrano = Schowek.teraz(),
            )
        } catch (blad: Exception) {
            val kopia = Schowek.odczytaj(kontekst) ?: throw blad
            Magazyn(
                skrytkiZJson(kopia.skrytki), lozyskaZJson(kopia.lozyska), ruchyZJson(kopia.ruchy),
                zeSchowka = true, pobrano = kopia.kiedy,
            )
        }
    }
}
