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
    fun `srednica z oznaczenia zgodna z katalogiem`() {
        // Dla każdego wpisu katalogu znamy prawdziwe d - reguła kodu otworu musi się zgadzać.
        val bledy = BearingCatalog.ENTRIES.mapNotNull { w ->
            val wyliczone = BearingTypeClassifier.boreFromSymbol(w.symbol)
            if (wyliczone != null && kotlin.math.abs(wyliczone - w.d) > 1.0)
                "${w.symbol}: katalog d=${w.d}, z oznaczenia=$wyliczone" else null
        }
        assertEquals("Rozbieżności otworu: $bledy", emptyList<String>(), bledy)
    }

    @Test
    fun `srednica z oznaczenia spoza katalogu`() {
        assertEquals(20.0, BearingTypeClassifier.boreFromSymbol("6204"))
        assertEquals(25.0, BearingTypeClassifier.boreFromSymbol("NU205"))
        assertEquals(30.0, BearingTypeClassifier.boreFromSymbol("UC206"))
        assertEquals(50.0, BearingTypeClassifier.boreFromSymbol("22210"))
        assertEquals(10.0, BearingTypeClassifier.boreFromSymbol("6000"))
        assertEquals(17.0, BearingTypeClassifier.boreFromSymbol("6003"))
        assertNull(BearingTypeClassifier.boreFromSymbol("HK1010"))
        assertNull(BearingTypeClassifier.boreFromSymbol("126"))
        assertNull(BearingTypeClassifier.boreFromSymbol(""))
    }

    @Test
    fun `odsiewanie blednych wymiarow z internetu`() {
        // Realny przypadek: dla 6204 wyszukiwarka zwracała 60x80 zamiast 20x47.
        val p = BearingTypeClassifier::dimensionsArePlausible
        assertEquals(true, p("6204", 20.0, 47.0, 14.0, 1.0))
        assertEquals(false, p("6204", 60.0, 80.0, 0.0, 1.0))
        assertEquals(false, p("6204", 60.0, 80.0, 18.0, 1.0))
        assertEquals(false, p("6205", 52.0, 25.0, 15.0, 1.0))
        assertEquals(true, p("HK1010", 10.0, 14.0, 10.0, 1.0))
    }

    @Test
    fun `uczciwe nie wiem zamiast zgadywania`() {
        listOf("", "   ", "ABC", "ABC123", "xyz", "??", "-", "SKF", "12", "5").forEach {
            assertNull("$it nie powinno dostać typu", BearingTypeClassifier.classify(it))
        }
        assertNull(BearingTypeClassifier.classify(null))
    }
}
