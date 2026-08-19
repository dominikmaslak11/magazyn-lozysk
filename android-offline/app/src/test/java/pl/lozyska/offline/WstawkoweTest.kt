package pl.lozyska.offline

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test
import pl.lozyska.offline.data.normalizeSymbol

/**
 * UC208 i ES208 mają ten sam otwór (40 mm) i tę samą średnicę zewnętrzną (80 mm),
 * ale to DWIE RÓŻNE konstrukcje - jedna nie zastąpi drugiej w maszynie. Program
 * musi je rozróżniać, inaczej podpowiada część, która wygląda na właściwą i nie jest.
 *
 * Reguły muszą dawać ten sam wynik co bearing_types.py na serwerze.
 */
class WstawkoweTest {

    @Test
    fun `UC i ES to rozne typy`() {
        for (s in listOf("UC208", "UC209", "UCP208", "SB208", "UK209")) {
            assertEquals(s, TypLozyska.WSTAWKOWE, BearingTypeClassifier.classify(s))
        }
        for (s in listOf("ES208", "ES209", "ES210", "ESP208")) {
            assertEquals(s, TypLozyska.WSTAWKOWE_ES, BearingTypeClassifier.classify(s))
        }
        assertNotEquals(BearingTypeClassifier.classify("UC208"), BearingTypeClassifier.classify("ES208"))
    }

    @Test
    fun `kod otworu obowiazuje w obu seriach`() {
        assertEquals(40.0, BearingTypeClassifier.boreFromSymbol("ES208")!!, 0.001)
        assertEquals(50.0, BearingTypeClassifier.boreFromSymbol("ES210")!!, 0.001)
    }

    /**
     * Regresja: "ES208" -> "208" kazałoby szukać wymiarów zwykłego łożyska kulkowego
     * 40x80x18. Ta sama pułapka, przez którą kiedyś NU205 stawało się 205.
     */
    @Test
    fun `ES nie redukuje sie do golych cyfr`() {
        for (s in listOf("ES208", "ES209", "ES210", "ESP208")) {
            assertEquals("$s nie może zredukować się do samych cyfr", s, normalizeSymbol(s))
        }
        assertEquals("UC208", normalizeSymbol("UC208"))
    }
}
