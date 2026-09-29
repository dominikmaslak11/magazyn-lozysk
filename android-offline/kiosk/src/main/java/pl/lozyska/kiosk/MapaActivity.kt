package pl.lozyska.kiosk

import android.app.Activity
import android.content.SharedPreferences
import android.content.pm.ActivityInfo
import android.graphics.Typeface
import android.os.Bundle
import android.os.Handler
import android.text.Editable
import android.text.TextWatcher
import android.util.TypedValue
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TableLayout
import android.widget.TableRow
import android.widget.TextView
import android.widget.Toast

/**
 * Caly dashboard: mapa regalu, szukanie "gdzie lezy" i korekta ilosci.
 *
 * Naczelna zasada tego ekranu: DUZO, PROSTO, CZYTELNIE - ma go obsluzyc starsza
 * osoba bez okularow, stojac przy regale. Stad wielkie litery, trzy oczywiste
 * przyciski i zero ukrytych gestow poza jednym (dotkniecie paska stanu odswieza).
 *
 * Jedna Activity, bez fragmentow, bez androidx, bez bazy - najprostszy ksztalt,
 * jaki spelnia to zadanie na Androidzie 4.2.
 */
class MapaActivity : Activity() {

    private lateinit var korzen: LinearLayout
    private lateinit var poleSzukania: EditText
    private lateinit var przyciskRuchy: Button
    private lateinit var przyciskMotyw: Button
    private lateinit var przyciskObroc: Button
    private lateinit var stan: TextView
    private lateinit var mapa: TableLayout
    private lateinit var naglowekDolu: TextView
    private lateinit var pasDolny: View
    private lateinit var dol: LinearLayout

    private lateinit var ustawienia: SharedPreferences
    private var motyw: Motyw = Motyw.NORMALNY

    // Ikony przyciskow gornego rzedu - trzymane, zeby zmiana motywu je przemalowala.
    private lateinit var ikonaLupa: Ikona
    private lateinit var ikonaRuchy: Ikona
    private lateinit var ikonaMotyw: Ikona
    private lateinit var ikonaObroc: Ikona

    private var magazyn: Magazyn? = null
    private var pokazujRuchy = false
    private val watek = Handler()

    /** Co ile odswiezac dane. Regal nie zmienia sie co sekunde, a tablet jest stary. */
    private val ODSWIEZANIE_MS = 60_000L

    private val odswiezaczCykliczny = object : Runnable {
        override fun run() {
            pobierzWTle()
            watek.postDelayed(this, ODSWIEZANIE_MS)
        }
    }

    override fun onCreate(zapisanyStan: Bundle?) {
        super.onCreate(zapisanyStan)
        ustawienia = getSharedPreferences("kiosk", MODE_PRIVATE)
        // Orientacja PRZED setContentView, zeby ekran nie mrugnal przy starcie.
        zastosujOrientacje(ustawienia.getBoolean("poziomo", false))
        setContentView(R.layout.mapa)

        // Tablet wisi na regale i ma byc gotowy bez podchodzenia: ekran nie gasnie,
        // apka pokazuje sie takze na zablokowanym urzadzeniu i sama je budzi.
        window.addFlags(
            WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON or
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD or
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
        )

        korzen = findViewById(R.id.korzen)
        poleSzukania = findViewById(R.id.szukaj)
        przyciskRuchy = findViewById(R.id.ruchy)
        przyciskMotyw = findViewById(R.id.motyw)
        przyciskObroc = findViewById(R.id.obroc)
        stan = findViewById(R.id.stan)
        mapa = findViewById(R.id.mapa)
        naglowekDolu = findViewById(R.id.naglowek_dolu)
        pasDolny = findViewById(R.id.pas_dolny)
        dol = findViewById(R.id.dol)

        motyw = Motyw.wg(ustawienia.getInt("motyw", 0))
        ikonaLupa = ikona(Ikona.Rodzaj.LUPA, 30)
        ikonaRuchy = ikona(Ikona.Rodzaj.ZEGAR, 34)
        ikonaMotyw = ikona(Ikona.Rodzaj.MOTYW, 34)
        ikonaObroc = ikona(Ikona.Rodzaj.OBROT, 34)
        poleSzukania.setCompoundDrawables(ikonaLupa, null, null, null)
        poleSzukania.compoundDrawablePadding = 12
        // Ikona nad podpisem: rozpoznaje sie ja od razu, a napis tylko potwierdza.
        przyciskRuchy.setCompoundDrawables(null, ikonaRuchy, null, null)
        przyciskMotyw.setCompoundDrawables(null, ikonaMotyw, null, null)
        przyciskObroc.setCompoundDrawables(null, ikonaObroc, null, null)
        zastosujMotyw()

        poleSzukania.addTextChangedListener(object : TextWatcher {
            override fun afterTextChanged(s: Editable?) = przerysuj()
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
        })

        przyciskRuchy.setOnClickListener {
            pokazujRuchy = !pokazujRuchy
            przerysuj()
        }
        przyciskMotyw.setOnClickListener {
            val numer = (ustawienia.getInt("motyw", 0) + 1) % Motyw.ile()
            ustawienia.edit().putInt("motyw", numer).commit()
            motyw = Motyw.wg(numer)
            zastosujMotyw()
            przerysuj()
            pokaz("Motyw: " + Motyw.nazwa(numer))
        }
        przyciskObroc.setOnClickListener {
            val poziomo = !ustawienia.getBoolean("poziomo", false)
            ustawienia.edit().putBoolean("poziomo", poziomo).commit()
            zastosujOrientacje(poziomo)
        }
        // Dotkniecie paska stanu = odswiez teraz. Jedyny ukryty gest w calej apce
        // i jedyny, ktory da sie zgadnac - pasek pokazuje przeciez wiek danych.
        stan.setOnClickListener { pobierzWTle() }

        stan.text = "Laczenie z serwerem..."
        pobierzWTle()
    }

    override fun onResume() {
        super.onResume()
        watek.postDelayed(odswiezaczCykliczny, ODSWIEZANIE_MS)
    }

    override fun onPause() {
        super.onPause()
        watek.removeCallbacks(odswiezaczCykliczny)
    }

    /**
     * Wstecz NIE zamyka mapy. Tablet ma jedno zadanie i przypadkowe wyjscie na
     * pulpit oznaczaloby, ze przy regale stoi cos innego niz mapa - a nikt tego
     * nie zauwazy, dopoki nie przyjdzie szukac lozyska.
     *
     * Zamiast tego Wstecz czysci pole szukania, czyli robi to, czego czlowiek
     * najczesciej w tym momencie chce: "wroc do mapy".
     */
    override fun onBackPressed() {
        if (poleSzukania.text.isNotEmpty()) {
            poleSzukania.setText("")
            korzen.requestFocus()
        }
        // Gdy pole i tak jest puste - nie robimy nic. Mapa zostaje.
    }

    /** Wymusza orientacje na sztywno - tablet wisi na scianie i ma sie NIE obracac sam. */
    private fun zastosujOrientacje(poziomo: Boolean) {
        requestedOrientation =
            if (poziomo) ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
            else ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
    }

    private fun zastosujMotyw() {
        korzen.setBackgroundColor(motyw.tlo)
        poleSzukania.setBackgroundColor(motyw.pole)
        poleSzukania.setTextColor(motyw.tekst)
        poleSzukania.setHintTextColor(motyw.tekstSlaby)
        stan.setTextColor(motyw.tekstSlaby)
        naglowekDolu.setTextColor(motyw.tekstSlaby)
        pasDolny.setBackgroundColor(motyw.pasDolny)
        for (p in listOf(przyciskRuchy, przyciskMotyw, przyciskObroc)) {
            p.setTextColor(motyw.tekst)
        }
        for (i in listOf(ikonaRuchy, ikonaMotyw, ikonaObroc)) i.ustawKolor(motyw.tekst)
        ikonaLupa.ustawKolor(motyw.tekstSlaby)
    }

    private fun pismo(id: Int): Float = resources.getDimension(id)

    /** Ikona o boku [dp] gestosciowo niezaleznych pikseli, w kolorze biezacego motywu. */
    private fun ikona(rodzaj: Ikona.Rodzaj, dp: Int, kolor: Int = motyw.tekst): Ikona =
        Ikona(rodzaj, kolor, (dp * resources.displayMetrics.density).toInt())

    /** Ikona z lewej strony paska stanu: odswiez, gdy wszystko gra; trojkat, gdy nie. */
    private fun ikonaStanu(ostrzezenie: Boolean) {
        val kolor = if (ostrzezenie) motyw.ostrzezenie else motyw.tekstSlaby
        stan.setCompoundDrawables(
            ikona(if (ostrzezenie) Ikona.Rodzaj.OSTRZEZENIE else Ikona.Rodzaj.ODSWIEZ, 22, kolor),
            null, null, null,
        )
        stan.compoundDrawablePadding = 10
    }

    private fun pokaz(tekst: String) = Toast.makeText(this, tekst, Toast.LENGTH_SHORT).show()

    // ----------------------------------------------------------- pobieranie --

    private fun pobierzWTle() {
        Thread {
            var wynik: Magazyn? = null
            var blad: String? = null
            try {
                wynik = Serwer.wczytaj(this)
            } catch (e: Exception) {
                blad = e.message ?: e.javaClass.simpleName
            }
            val pobrany = wynik
            runOnUiThread {
                if (pobrany != null) {
                    magazyn = pobrany
                    przerysuj()
                } else {
                    // Nie ma ani serwera, ani kopii na dysku - pierwsze uruchomienie
                    // poza zasiegiem. Mowimy wprost, co jest nie tak.
                    stan.setTextColor(motyw.ostrzezenie)
                    ikonaStanu(true)
                    stan.text = "Brak polaczenia i brak kopii.\n$blad\n${BuildConfig.ADRES}"
                }
            }
        }.start()
    }

    /**
     * Korekta ilosci. Serwer zamienia to na wpis w dzienniku ruchow, wiec historia
     * zostaje kompletna niezaleznie od tego, skad przyszla zmiana.
     */
    private fun zmienIlosc(l: Lozysko, delta: Int) {
        if (l.ilosc + delta < 0) {
            pokaz("Nie moze byc mniej niz zero")
            return
        }
        Thread {
            var blad: String? = null
            try {
                Serwer.zmienIlosc(l, delta)
            } catch (e: Exception) {
                blad = e.message ?: e.javaClass.simpleName
            }
            val b = blad
            runOnUiThread {
                if (b == null) {
                    pokaz("${l.symbol}: ${l.ilosc} -> ${l.ilosc + delta} szt.")
                    pobierzWTle()
                } else {
                    pokaz("Nie udalo sie zapisac: $b")
                }
            }
        }.start()
    }

    // ------------------------------------------------------------ rysowanie --

    private fun przerysuj() {
        val dane = magazyn ?: return
        val pytanie = poleSzukania.text.toString().trim()
        val trafione = szukaj(dane, pytanie)

        stan.setTextColor(if (dane.zeSchowka) motyw.ostrzezenie else motyw.tekstSlaby)
        ikonaStanu(dane.zeSchowka)
        stan.text = if (dane.zeSchowka)
            "BRAK POLACZENIA - dane z kopii z ${dane.pobrano}\ndotknij, aby sprobowac ponownie"
        else
            "${dane.lozyska.size} pozycji, ${dane.lozyska.sumOf { it.ilosc }} szt.  ${dane.pobrano}"

        rysujMape(dane, trafione)

        // Dolny pas ma trzy stany i tylko jeden z nich cos zaslania:
        //   szukanie wpisane -> odpowiedz "gdzie lezy" (wygrywa zawsze),
        //   wcisniete RUCHY  -> ostatnie ruchy,
        //   nic z tego       -> pas schowany, mapa na caly ekran.
        val cosDoPokazania = pytanie.isNotEmpty() || pokazujRuchy
        pasDolny.visibility = if (cosDoPokazania) View.VISIBLE else View.GONE
        naglowekDolu.visibility = if (cosDoPokazania) View.VISIBLE else View.GONE

        if (pytanie.isNotEmpty()) {
            naglowekDolu.text = getString(R.string.naglowek_wyniki)
            rysujWyniki(dane, trafione)
        } else if (pokazujRuchy) {
            naglowekDolu.text = getString(R.string.naglowek_ruchy)
            rysujRuchy(dane)
        }
    }

    /** Dopasowanie po symbolu, uwagach albo wymiarach ("25x52", "x52", "25x"). */
    private fun szukaj(dane: Magazyn, pytanie: String): Set<String> {
        if (pytanie.isEmpty()) return emptySet()
        val male = pytanie.lowercase()
        val wymiary = rozbijWymiary(male)
        val trafione = HashSet<String>()
        for (l in dane.lozyska) {
            val pasuje = if (wymiary != null) pasujeWymiarem(l, wymiary)
            else l.symbol.lowercase().contains(male) || l.uwagi.lowercase().contains(male)
            if (pasuje) trafione.add(l.symbol)
        }
        return trafione
    }

    /** "25x52" -> [25, 52]; "x52" -> [null, 52]; zwykly tekst -> null. */
    private fun rozbijWymiary(tekst: String): List<Double?>? {
        if (!tekst.contains('x')) return null
        val czesci = tekst.split('x')
        if (czesci.size > 3) return null
        val wynik = ArrayList<Double?>()
        for (c in czesci) {
            val p = c.trim().replace(',', '.')
            if (p.isEmpty()) wynik.add(null) else wynik.add(p.toDoubleOrNull() ?: return null)
        }
        return if (wynik.all { it == null }) null else wynik
    }

    private fun pasujeWymiarem(l: Lozysko, wymiary: List<Double?>): Boolean {
        val wartosci = listOf(l.d, l.dZew, l.b)
        for (i in wymiary.indices) {
            val szukane = wymiary[i] ?: continue
            val ma = wartosci.getOrNull(i) ?: return false
            if (Math.abs(ma - szukane) > 0.6) return false
        }
        return true
    }

    private fun rysujMape(dane: Magazyn, trafione: Set<String>) {
        mapa.removeAllViews()
        val wgSkrytki = dane.lozyska.groupBy { it.skrytka }
        var i = 0
        while (i < dane.skrytki.size) {
            val rzad = TableRow(this)
            var k = 0
            while (k < 2 && i + k < dane.skrytki.size) {
                val s = dane.skrytki[i + k]
                rzad.addView(kafelek(s, wgSkrytki[s.nazwa].orEmpty(), trafione))
                k++
            }
            mapa.addView(rzad)
            i += 2
        }
    }

    private fun kafelek(skrytka: Skrytka, zawartosc: List<Lozysko>, trafione: Set<String>): View {
        val maTrafienie = zawartosc.any { trafione.contains(it.symbol) }
        val tloKafelka = when {
            maTrafienie -> motyw.skrytkaTrafiona
            zawartosc.isEmpty() -> motyw.skrytkaPusta
            else -> motyw.skrytka
        }
        val kolorPisma = if (maTrafienie) motyw.tekstNaTrafionej else motyw.tekst
        val kolorSlaby = if (maTrafienie) motyw.tekstNaTrafionej else motyw.tekstSlaby

        val pudelko = LinearLayout(this)
        pudelko.orientation = LinearLayout.VERTICAL
        pudelko.setBackgroundColor(tloKafelka)
        pudelko.setPadding(16, 14, 16, 14)
        val parametry = TableRow.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        parametry.setMargins(3, 3, 3, 3)
        pudelko.layoutParams = parametry

        pudelko.addView(tekst(skrytka.nazwa, kolorPisma, pismo(R.dimen.pismo_skrytka), pogrubiony = true))
        pudelko.addView(tekst(skrytka.zakres(), kolorSlaby, pismo(R.dimen.pismo_zakres)))

        if (zawartosc.isEmpty()) {
            pudelko.addView(tekst("—", kolorSlaby, pismo(R.dimen.pismo_lozysko)))
        } else {
            for (l in zawartosc) {
                val wyroznione = trafione.contains(l.symbol)
                pudelko.addView(
                    tekst(
                        "${l.symbol}  x${l.ilosc}",
                        if (wyroznione) kolorPisma else kolorSlaby,
                        pismo(R.dimen.pismo_lozysko),
                        pogrubiony = wyroznione,
                    )
                )
            }
        }
        return pudelko
    }

    /**
     * Wynik szukania: wielkimi literami "SYMBOL -> SKRYTKA", pod spodem wymiary,
     * a obok wielkie przyciski minus i plus do korekty ilosci.
     */
    private fun rysujWyniki(dane: Magazyn, trafione: Set<String>) {
        dol.removeAllViews()
        val znalezione = dane.lozyska.filter { trafione.contains(it.symbol) }
        if (znalezione.isEmpty()) {
            dol.addView(tekst("Nie ma takiego lozyska.", motyw.ostrzezenie, pismo(R.dimen.pismo_odpowiedz)))
            return
        }
        for (l in znalezione) {
            val wiersz = LinearLayout(this)
            wiersz.orientation = LinearLayout.HORIZONTAL
            wiersz.setPadding(10, 14, 10, 14)

            val opis = LinearLayout(this)
            opis.orientation = LinearLayout.VERTICAL
            opis.layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
            opis.addView(
                tekst(
                    "${l.symbol}  ->  ${if (l.skrytka.isEmpty()) "bez skrytki" else l.skrytka}",
                    motyw.tekst, pismo(R.dimen.pismo_odpowiedz), pogrubiony = true,
                )
            )
            opis.addView(
                tekst("${l.wymiary()} mm   ${l.typ}", motyw.tekstSlaby, pismo(R.dimen.pismo_szczegoly))
            )
            wiersz.addView(opis)

            wiersz.addView(przyciskIlosci(Ikona.Rodzaj.MINUS, "Zmniejsz o jeden") { zmienIlosc(l, -1) })
            val ile = tekst("${l.ilosc}", motyw.tekst, pismo(R.dimen.pismo_ilosc), pogrubiony = true)
            ile.setPadding(18, 0, 18, 0)
            wiersz.addView(ile)
            wiersz.addView(przyciskIlosci(Ikona.Rodzaj.PLUS, "Zwieksz o jeden") { zmienIlosc(l, +1) })

            dol.addView(wiersz)
        }
    }

    /** Duzy przycisk, ktory da sie trafic palcem bez celowania. */
    private fun przyciskIlosci(rodzaj: Ikona.Rodzaj, opis: String, akcja: () -> Unit): Button {
        val b = Button(this)
        // Rysowany plus/minus zamiast znaku "+"/"-": ten sam rozmiar i grubosc
        // niezaleznie od czcionki, a przy slabym wzroku ksztalt czyta sie latwiej.
        b.setCompoundDrawables(ikona(rodzaj, 44), null, null, null)
        b.contentDescription = opis
        b.minimumWidth = 110
        b.minimumHeight = 110
        b.setOnClickListener { akcja() }
        return b
    }

    private fun rysujRuchy(dane: Magazyn) {
        dol.removeAllViews()
        if (dane.ruchy.isEmpty()) {
            dol.addView(tekst("Brak ruchow.", motyw.tekstSlaby, pismo(R.dimen.pismo_ruch)))
            return
        }
        for (r in dane.ruchy.take(12)) {
            val znak = if (r.delta > 0) "+${r.delta}" else "${r.delta}"
            val t = tekst(
                "${r.kiedy}   ${r.symbol}   $znak",
                if (r.delta > 0) motyw.przybylo else motyw.ubylo,
                pismo(R.dimen.pismo_ruch),
            )
            t.setPadding(10, 10, 10, 10)
            // Zielona strzalka w gore = przybylo, czerwona w dol = ubylo. Kolor sam
            // nie wystarczy (daltonizm), wiec kierunek niesie ten sam sens.
            t.setCompoundDrawables(
                ikona(
                    if (r.delta > 0) Ikona.Rodzaj.STRZALKA_GORA else Ikona.Rodzaj.STRZALKA_DOL,
                    18, if (r.delta > 0) motyw.przybylo else motyw.ubylo,
                ),
                null, null, null,
            )
            t.compoundDrawablePadding = 12
            dol.addView(t)
        }
    }

    private fun tekst(tresc: String, kolor: Int, rozmiarPx: Float, pogrubiony: Boolean = false): TextView {
        val t = TextView(this)
        t.text = tresc
        t.setTextSize(TypedValue.COMPLEX_UNIT_PX, rozmiarPx)
        t.setTextColor(kolor)
        if (pogrubiony) t.setTypeface(null, Typeface.BOLD)
        return t
    }
}
