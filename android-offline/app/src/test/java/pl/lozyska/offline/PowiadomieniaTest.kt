package pl.lozyska.offline

import org.junit.Assert.assertEquals
import org.junit.Test

/** Wiek danych pokazujemy wprost, bo offline lista podpowiedzi bywa nieaktualna. */
class PowiadomieniaTest {
    private val teraz = 1_700_000_000_000L
    private fun temu(minut: Long) = wiekSynchronizacji(teraz - minut * 60_000, teraz)

    @Test
    fun `wiek synchronizacji po polsku`() {
        assertEquals("przed chwilą", temu(0))
        assertEquals("przed chwilą", temu(1))
        assertEquals("12 min temu", temu(12))
        assertEquals("59 min temu", temu(59))
        assertEquals("1 godz. temu", temu(60))
        assertEquals("5 godz. temu", temu(5 * 60))
        assertEquals("47 godz. temu", temu(47 * 60))
        assertEquals("2 dni temu", temu(48 * 60))
        assertEquals("7 dni temu", temu(7 * 24 * 60))
    }
}
