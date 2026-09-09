package pl.lozyska.kiosk

import android.graphics.Color

/**
 * Trzy zestawy kolorow, przelaczane po kolei przyciskiem MOTYW i zapamietywane
 * miedzy uruchomieniami: CIEMNY -> JASNY -> KONTRAST -> CIEMNY.
 *
 * Kolory sa tu LICZBAMI, a nie zasobami @color, celowo: motyw zmienia sie w locie,
 * bez restartu ekranu, a wiekszosc widokow (kafelki mapy, wyniki, ruchy) i tak
 * powstaje w kodzie. Podmiana zasobow wymagalaby atrybutow motywu i recreate() -
 * wiecej zachodu bez zysku dla dwoch zestawow.
 *
 * "Wysoki kontrast" to nie jest przyciemniony wariant zwyklego: tam, gdzie normalny
 * motyw rozroznia tekst wazny od pobocznego szaroscia, kontrastowy daje OBA na bialo.
 * Slaby wzrok gubi wlasnie te szarosci, wiec rezygnujemy z nich zupelnie.
 */
class Motyw(
    val tlo: Int,
    val pasDolny: Int,
    val pole: Int,
    val tekst: Int,
    val tekstSlaby: Int,
    val skrytka: Int,
    val skrytkaPusta: Int,
    val skrytkaTrafiona: Int,
    val tekstNaTrafionej: Int,
    val przybylo: Int,
    val ubylo: Int,
    val ostrzezenie: Int,
) {
    companion object {

        val NORMALNY = Motyw(
            tlo = Color.parseColor("#12171C"),
            pasDolny = Color.parseColor("#0C1015"),
            pole = Color.parseColor("#1E262E"),
            tekst = Color.parseColor("#E8EDF2"),
            tekstSlaby = Color.parseColor("#8A99A8"),
            skrytka = Color.parseColor("#1B2430"),
            skrytkaPusta = Color.parseColor("#151A20"),
            skrytkaTrafiona = Color.parseColor("#2E5B32"),
            tekstNaTrafionej = Color.parseColor("#FFFFFF"),
            przybylo = Color.parseColor("#6FCF77"),
            ubylo = Color.parseColor("#E2756B"),
            ostrzezenie = Color.parseColor("#E0B25C"),
        )

        val KONTRAST = Motyw(
            tlo = Color.BLACK,
            pasDolny = Color.BLACK,
            pole = Color.BLACK,
            tekst = Color.WHITE,
            // Bez szarosci - w tym motywie wszystko jest biale albo zolte.
            tekstSlaby = Color.WHITE,
            skrytka = Color.BLACK,
            skrytkaPusta = Color.BLACK,
            // Zolte tlo i CZARNE litery: najmocniejszy kontrast, jaki da sie zrobic.
            skrytkaTrafiona = Color.parseColor("#FFE000"),
            tekstNaTrafionej = Color.BLACK,
            przybylo = Color.parseColor("#00FF00"),
            ubylo = Color.parseColor("#FF6060"),
            ostrzezenie = Color.parseColor("#FFE000"),
        )

        val JASNY = Motyw(
            tlo = Color.parseColor("#F2F4F7"),
            pasDolny = Color.parseColor("#E4E8ED"),
            pole = Color.parseColor("#FFFFFF"),
            tekst = Color.parseColor("#12171C"),
            tekstSlaby = Color.parseColor("#5A6672"),
            skrytka = Color.parseColor("#FFFFFF"),
            skrytkaPusta = Color.parseColor("#E8ECF0"),
            skrytkaTrafiona = Color.parseColor("#9BE29F"),
            tekstNaTrafionej = Color.parseColor("#0B2410"),
            przybylo = Color.parseColor("#1E7A28"),
            ubylo = Color.parseColor("#B32D22"),
            ostrzezenie = Color.parseColor("#8A5A00"),
        )

        /** Kolejnosc przelaczania przyciskiem MOTYW. */
        private val KOLEJNOSC = listOf(NORMALNY, JASNY, KONTRAST)
        val NAZWY = listOf("CIEMNY", "JASNY", "KONTRAST")

        fun wg(numer: Int): Motyw = KOLEJNOSC[((numer % KOLEJNOSC.size) + KOLEJNOSC.size) % KOLEJNOSC.size]
        fun nazwa(numer: Int): String = NAZWY[((numer % NAZWY.size) + NAZWY.size) % NAZWY.size]
        fun ile(): Int = KOLEJNOSC.size
    }
}
