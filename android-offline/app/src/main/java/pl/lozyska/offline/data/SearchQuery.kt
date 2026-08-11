package pl.lozyska.offline.data

/**
 * Rozpoznawanie intencji w JEDNYM polu wyszukiwania.
 *
 * W warsztacie pytanie brzmi zwykle "potrzebuję czegoś 25x52, mam coś takiego?", a nie
 * "czy mam 6205" - a do tej pory magazynu dało się szukać wyłącznie po symbolu.
 * Zamiast dokładać drugie pole albo przełącznik, rozpoznajemy sam zapis:
 *
 *     6205        -> szukanie po symbolu (jak dotąd)
 *     25x52       -> wymiary: d=25, D=52, szerokość dowolna
 *     25x52x15    -> wymiary: d=25, D=52, B=15
 *     x52         -> tylko średnica zewnętrzna 52
 *     25x         -> tylko średnica wewnętrzna 25
 *     25 52 15    -> to samo co 25x52x15 (spacje zamiast "x")
 *
 * Pojedyncza liczba ("6205") celowo NIE uruchamia szukania po wymiarach - byłoby nie do
 * odróżnienia od symbolu. Żeby szukać po jednym wymiarze, użyj "x52" albo "25x".
 *
 * Ten sam format obsługuje wersja webowa (patrz search_query.py na serwerze) - opis w UI
 * jest wspólny, więc rozjazd między nimi od razu byłby mylący dla użytkownika.
 */
data class DimensionQuery(val d: Double?, val dZew: Double?, val b: Double?) {
    /** Pusty zapis ("x", "x x") nie jest sensownym pytaniem - nie filtrujmy wtedy niczego. */
    val isEmpty: Boolean get() = d == null && dZew == null && b == null
}

object SearchQuery {

    /** Tolerancja dopasowania [mm] - taka sama jak przy wyszukiwaniu w katalogu. */
    const val TOLERANCE = 0.6

    private val SEPARATORS = Regex("[x×*]", RegexOption.IGNORE_CASE)
    private val NUMBER = Regex("^\\d+([.,]\\d+)?$")

    /**
     * Zwraca wymiary, jeśli tekst wygląda na zapytanie wymiarowe, albo null,
     * gdy należy szukać po symbolu.
     */
    fun parseDimensions(raw: String): DimensionQuery? {
        val text = raw.trim()
        if (text.isEmpty()) return null

        val parts: List<String> = when {
            SEPARATORS.containsMatchIn(text) -> text.split(SEPARATORS)
            // Zapis ze spacjami/przecinkami wymaga min. 2 liczb, żeby nie mylić z symbolem.
            else -> {
                val chunks = text.split(Regex("[\\s,;]+")).filter { it.isNotBlank() }
                if (chunks.size < 2) return null else chunks
            }
        }
        if (parts.size > 3) return null

        val values = parts.map { part ->
            val p = part.trim()
            when {
                p.isEmpty() -> null                                  // puste miejsce = dowolny wymiar
                NUMBER.matches(p) -> p.replace(',', '.').toDoubleOrNull()
                else -> return null                                  // cokolwiek innego -> to nie wymiary
            }
        }

        val query = DimensionQuery(
            d = values.getOrNull(0),
            dZew = values.getOrNull(1),
            b = values.getOrNull(2),
        )
        return if (query.isEmpty) null else query
    }
}
