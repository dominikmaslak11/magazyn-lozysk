package pl.lozyska.offline

import org.junit.Assert.assertEquals
import org.junit.Test
import pl.lozyska.offline.data.ShelfWithCounts

/**
 * Regresja błędu, który SPŁASZCZAŁ HIERARCHIĘ LOKALIZACJI.
 *
 * Ekran regałów budował rekord od zera z czterech pól formularza, więc wszystko inne
 * wracało do wartości domyślnych: półka traciła przypisanie do regału (parentId = null),
 * typ poziomu wracał na "regał", a dedykowane typy i zmierzone wymiary były czyszczone.
 * Zapisany rekord jechał potem na serwer i rozsypywał układ magazynu na wszystkich
 * urządzeniach - jednym tapnięciem "Zapisz zmiany".
 */
class ShelfEditTest {

    private val polka = ShelfWithCounts(
        id = "p2", nazwa = "Półka 2", poziom = 2, dMin = null, dMax = null,
        pozycje = 22, sztuki = 57,
        parentId = "regal-2", poziomTyp = "półka", typy = "wstawkowe",
        szerokoscMm = 860.0, glebokoscMm = 500.0, wysokoscMm = 460.0,
    )

    @Test
    fun `edycja nazwy nie zrywa przypisania do regalu`() {
        val zapisana = zaktualizowanaPolka(polka, "Półka 2 (góra)", "2", "", "")
        assertEquals("Półka 2 (góra)", zapisana.nazwa)
        assertEquals("półka musi zostać w swoim regale", "regal-2", zapisana.parentId)
        assertEquals("półka", zapisana.poziomTyp)
        assertEquals("wstawkowe", zapisana.typy)
    }

    @Test
    fun `zmierzone wymiary przezywaja edycje`() {
        val zapisana = zaktualizowanaPolka(polka, "", "", "", "")
        assertEquals(860.0, zapisana.szerokoscMm!!, 0.001)
        assertEquals(500.0, zapisana.glebokoscMm!!, 0.001)
        assertEquals(460.0, zapisana.wysokoscMm!!, 0.001)
    }

    @Test
    fun `puste pola nie kasuja nazwy ani kolejnosci`() {
        val zapisana = zaktualizowanaPolka(polka, "   ", "nie-liczba", "", "")
        assertEquals("Półka 2", zapisana.nazwa)
        assertEquals(2, zapisana.poziom)
    }
}
