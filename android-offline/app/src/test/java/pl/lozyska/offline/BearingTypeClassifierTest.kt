package pl.lozyska.offline

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * Te przypadki są celowo IDENTYCZNE z tests/test_bearing_types.py na serwerze.
 * Obie implementacje muszą dawać ten sam wynik - inaczej to samo łożysko dostałoby
 * inny typ w zależności od tego, czy dodano je w appce, czy w wersji webowej.
 */
class BearingTypeClassifierTest {

    private fun typ(symbol: String) = BearingTypeClassifier.classify(symbol)?.etykieta

    @Test
    fun `zgodnosc z wbudowanym katalogiem`() {
        // Dla każdego wpisu katalogu znamy typ na pewno - klasyfikator musi się zgadzać.
        val bledy = BearingCatalog.ENTRIES.mapNotNull { wpis ->
            val rozpoznany = BearingTypeClassifier.classify(wpis.symbol)
            if (rozpoznany != wpis.typ) "${wpis.symbol}: oczekiwano ${wpis.typ}, dostano $rozpoznany" else null
        }
        assertEquals("Rozbieżności z katalogiem: $bledy", emptyList<String>(), bledy)
    }

    @Test
    fun `pulapka liczby cyfr`() {
        assertEquals("skośne (kulkowe)", typ("3204"))
        assertEquals("stożkowe", typ("30204"))
        assertEquals("wahliwe kulkowe", typ("2205"))
        assertEquals("wahliwe baryłkowe", typ("22205"))
        assertEquals("skośne (kulkowe)", typ("3306"))
        assertEquals("stożkowe", typ("33006"))
    }

    @Test
    fun `igielkowe maja pierwszenstwo przed walcowymi`() {
        assertEquals("igiełkowe", typ("NA4900"))
        assertEquals("igiełkowe", typ("NKI25/20"))
        assertEquals("igiełkowe", typ("NK1010"))
        assertEquals("walcowe", typ("NU205"))
        assertEquals("walcowe", typ("NJ2308"))
        assertEquals("walcowe", typ("NNU4920"))
    }

    @Test
    fun `typy spoza katalogu`() {
        assertEquals("skośne (kulkowe)", typ("7205"))
        assertEquals("skośne (kulkowe)", typ("QJ308"))
        assertEquals("oporowe", typ("51105"))
        assertEquals("oporowe", typ("29412"))
        assertEquals("igiełkowe", typ("HK1010"))
        assertEquals("walcowe", typ("NUP310"))
    }

    @Test
    fun `zapis jaki wpisuje uzytkownik`() {
        assertEquals("kulkowe zwykłe", typ("SKF 6205-2RS1"))
        assertEquals("walcowe", typ("FAG NU205"))
        assertEquals("kulkowe zwykłe", typ("nsk-6008 zz"))
        assertEquals("walcowe", typ("nu 205 ecp"))
        assertEquals("stożkowe", typ("30204 A"))
        assertEquals("wstawkowe (UC)", typ("UC 211 D1"))
        assertEquals("skośne (kulkowe)", typ("7310BEP"))
    }

    @Test
    fun `uczciwe nie wiem zamiast zgadywania`() {
        listOf("", "   ", "ABC", "ABC123", "xyz", "??", "-", "SKF", "12", "5").forEach {
            assertNull("$it nie powinno dostać typu", BearingTypeClassifier.classify(it))
        }
        assertNull(BearingTypeClassifier.classify(null))
    }
}
