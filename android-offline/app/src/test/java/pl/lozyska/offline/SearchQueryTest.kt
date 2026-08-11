package pl.lozyska.offline

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import pl.lozyska.offline.data.SearchQuery
import org.junit.Test

class SearchQueryTest {

    private fun dims(q: String) = SearchQuery.parseDimensions(q)

    @Test
    fun `pelne wymiary`() {
        val w = dims("25x52x15")!!
        assertEquals(25.0, w.d!!, 0.001)
        assertEquals(52.0, w.dZew!!, 0.001)
        assertEquals(15.0, w.b!!, 0.001)
    }

    @Test
    fun `dwa wymiary - szerokosc dowolna`() {
        val w = dims("25x52")!!
        assertEquals(25.0, w.d!!, 0.001)
        assertEquals(52.0, w.dZew!!, 0.001)
        assertNull(w.b)
    }

    @Test
    fun `puste miejsca oznaczaja dowolny wymiar`() {
        val tylkoZewnetrzna = dims("x52")!!
        assertNull(tylkoZewnetrzna.d)
        assertEquals(52.0, tylkoZewnetrzna.dZew!!, 0.001)

        val tylkoWewnetrzna = dims("25x")!!
        assertEquals(25.0, tylkoWewnetrzna.d!!, 0.001)
        assertNull(tylkoWewnetrzna.dZew)

        val bezWewnetrznej = dims("x52x15")!!
        assertNull(bezWewnetrznej.d)
        assertEquals(52.0, bezWewnetrznej.dZew!!, 0.001)
        assertEquals(15.0, bezWewnetrznej.b!!, 0.001)
    }

    @Test
    fun `spacje i przecinki dzialaja jak x`() {
        val w = dims("25 52 15")!!
        assertEquals(25.0, w.d!!, 0.001)
        assertEquals(52.0, w.dZew!!, 0.001)
        assertEquals(15.0, w.b!!, 0.001)
    }

    @Test
    fun `ulamki dziesietne z kropka i przecinkiem`() {
        assertEquals(15.25, dims("20x47x15.25")!!.b!!, 0.001)
        assertEquals(15.25, dims("20x47x15,25")!!.b!!, 0.001)
    }

    @Test
    fun `wielka litera X i znak mnozenia`() {
        assertEquals(52.0, dims("25X52")!!.dZew!!, 0.001)
        assertEquals(52.0, dims("25×52")!!.dZew!!, 0.001)
    }

    @Test
    fun `pojedyncza liczba to symbol, nie wymiary`() {
        // Kluczowe rozróżnienie: "6205" musi trafić do szukania po symbolu.
        assertNull(dims("6205"))
        assertNull(dims("25"))
        assertNull(dims("30204"))
    }

    @Test
    fun `tekst i smieci to nie wymiary`() {
        assertNull(dims(""))
        assertNull(dims("   "))
        assertNull(dims("NU205"))
        assertNull(dims("UC 206"))       // dwa człony, ale "UC" nie jest liczbą
        assertNull(dims("x"))            // sam separator, bez liczb
        assertNull(dims("xx"))
        assertNull(dims("25x52x15x20"))  // za dużo członów
        assertNull(dims("abc x def"))
    }
}
