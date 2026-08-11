package pl.lozyska.offline

/**
 * Rozpoznawanie TYPU łożyska z samego oznaczenia (ISO 15 / ISO 355).
 *
 * Port 1:1 z `bearing_types.py` na serwerze - obie strony MUSZĄ dawać ten sam wynik,
 * inaczej to samo łożysko dostałoby inny typ w zależności od tego, gdzie je dodano.
 * Zmieniając cokolwiek tutaj, zmień tak samo tam (i odwrotnie).
 *
 * Po co: wbudowany katalog ma ~250 rozmiarów. Dla oznaczeń spoza katalogu wymiarów
 * trzeba szukać w sieci, ale TYP wynika wprost z oznaczenia - bez katalogu i bez sieci.
 *
 * NAJWAŻNIEJSZA PUŁAPKA: o typie decyduje nie tylko przedrostek, ale i LICZBA CYFR:
 *     3204  (4 cyfry) -> skośne dwurzędowe     30204 (5 cyfr) -> STOŻKOWE
 *     2205  (4 cyfry) -> wahliwe kulkowe       22205 (5 cyfr) -> wahliwe BARYŁKOWE
 *
 * Świadome ograniczenie: klasyfikujemy wyłącznie z oznaczenia. Z samych wymiarów typu
 * wyznaczyć się nie da (różne konstrukcje dzielą te same gabaryty), więc nawet nie
 * próbujemy - pewnie brzmiąca, ale błędna kategoria jest gorsza niż jej brak.
 */
object BearingTypeClassifier {

    /** Kolejność MA ZNACZENIE: igiełkowe (NA/NK/NKI) przed walcowymi (N/NU/NJ). */
    private val PREFIX_RULES: List<Pair<Regex, TypLozyska>> = listOf(
        Regex("^(UCFL|UCFC|UCPH|UCP|UCF|UCT|UCX|UC|UK|SB|SA|CSA)\\d") to TypLozyska.WSTAWKOWE,
        Regex("^(RNAO|RNA|NKIA|NKIB|NKI|NKX|NKS|NAO|NA|NK|HK|BK|IR|TA)\\d") to TypLozyska.IGIELKOWE,
        Regex("^(NNU|NNCF|NCF|NUP|NUB|NJP|NN|NU|NJ|NF|NP|N)\\d") to TypLozyska.WALCOWE,
        Regex("^QJ\\d") to TypLozyska.SKOSNE,
        Regex("^(AXK|AX|81|89)\\d") to TypLozyska.OPOROWE,
        Regex("^C\\d{4}") to TypLozyska.WAHLIWE_BARYLKOWE,
    )

    /** (liczba cyfr, przedrostki cyfrowe) -> typ. Sprawdzane przed regułą na pierwszej cyfrze. */
    private val DIGIT_RULES: List<Triple<Int, List<String>, TypLozyska>> = listOf(
        Triple(5, listOf("302", "303", "313", "320", "322", "323", "329", "330", "331", "332"),
            TypLozyska.STOZKOWE),
        Triple(5, listOf("213", "222", "223", "230", "231", "232", "238", "239", "240", "241", "248", "249"),
            TypLozyska.WAHLIWE_BARYLKOWE),
        Triple(5, listOf("511", "512", "513", "514", "522", "523", "524", "292", "293", "294"),
            TypLozyska.OPOROWE),
        Triple(5, listOf("160", "161", "162", "163"), TypLozyska.KULKOWE),
        Triple(4, listOf("32", "33"), TypLozyska.SKOSNE),
        Triple(4, listOf("12", "13", "22", "23"), TypLozyska.WAHLIWE_KULKOWE),
        Triple(4, listOf("51", "52", "53", "54"), TypLozyska.OPOROWE),
    )

    private val FIRST_DIGIT_RULES: List<Pair<String, TypLozyska>> = listOf(
        "6" to TypLozyska.KULKOWE,
        "7" to TypLozyska.SKOSNE,
        "1" to TypLozyska.WAHLIWE_KULKOWE,
    )

    /** Krótsze ciągi cyfr nie są oznaczeniem łożyska - bez tego "12" dostawałoby typ. */
    private const val MIN_DIGITS = 3

    /** Marki wpisywane przed oznaczeniem ("SKF 6205"). Lista jawna, nie "utnij litery". */
    private val BRANDS = listOf(
        "SKF", "FAG", "INA", "NSK", "NTN", "KOYO", "TIMKEN", "NACHI", "IKO", "THK",
        "ZVL", "ZKL", "CX", "NKE", "SNR", "URB", "FLT", "KINEX", "STEYR", "RHP",
        "MCGILL", "TORRINGTON", "BARDEN", "SCHAEFFLER", "LOYAL", "CRAFT", "ASAHI",
    )

    private val SEPARATORS = Regex("[\\s\\-_/]")
    private val LEADING_DIGITS = Regex("^(\\d+)")

    /**
     * Typ rozpoznany z oznaczenia albo null, gdy nie da się ustalić.
     * null to uczciwe "nie wiem" - lepsze niż zgadywanie.
     */
    fun classify(raw: String?): TypLozyska? {
        if (raw.isNullOrBlank()) return null

        var text = SEPARATORS.replace(raw.trim().uppercase(), "")
        for (brand in BRANDS) {
            if (text.startsWith(brand) && text.length > brand.length) {
                text = text.substring(brand.length)
                break
            }
        }
        if (text.isEmpty()) return null

        for ((pattern, typ) in PREFIX_RULES) {
            if (pattern.containsMatchIn(text)) return typ
        }

        val digits = LEADING_DIGITS.find(text)?.groupValues?.get(1) ?: return null
        if (digits.length < MIN_DIGITS) return null

        for ((length, prefixes, typ) in DIGIT_RULES) {
            if (digits.length == length && prefixes.any { digits.startsWith(it) }) return typ
        }
        for ((first, typ) in FIRST_DIGIT_RULES) {
            if (digits.startsWith(first)) return typ
        }
        return null
    }
}
