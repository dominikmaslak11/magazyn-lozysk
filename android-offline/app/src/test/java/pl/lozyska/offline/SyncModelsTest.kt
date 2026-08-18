package pl.lozyska.offline

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test
import pl.lozyska.offline.data.BearingEntity
import pl.lozyska.offline.sync.SyncBarcodeAliasDto
import pl.lozyska.offline.sync.SyncBearingDto
import pl.lozyska.offline.sync.SyncPowiadomienieDto
import pl.lozyska.offline.sync.SyncShelfDto
import pl.lozyska.offline.sync.toSyncDto
import pl.lozyska.offline.sync.toEntity

/**
 * Regresja błędu, przez który SKASOWANE rekordy wracały na telefon.
 *
 * Konwersja DTO -> encja ustawiała deletedAt zawsze na null, więc nagrobek z serwera
 * stawał się zwykłym, aktywnym rekordem i przechodził przez filtr w
 * Repository.replaceAllFromServer. Objaw u użytkownika: łożysko skasowane 8 sierpnia
 * nadal widniało na liście w telefonie kilka dni później.
 */
class SyncModelsTest {

    @Test
    fun `nagrobek lozyska z serwera zostaje nagrobkiem lokalnie`() {
        val skasowane = SyncBearingDto(
            id = "x", symbol = "6008", typ = "kulkowe zwykłe", d = 40.0, dZew = 68.0, B = 15.0,
            ilosc = 1, regal_id = null, reczny_przydzial = false, zrodlo = "offline", uwagi = "",
            deleted_at = "deleted",
        ).toEntity(TS)
        assertNotNull("skasowane łożysko musi zostać nagrobkiem", skasowane.deletedAt)

        val aktywne = SyncBearingDto(
            id = "y", symbol = "6205", typ = "kulkowe zwykłe", d = 25.0, dZew = 52.0, B = 15.0,
            ilosc = 1, regal_id = null, reczny_przydzial = false, zrodlo = "offline", uwagi = "",
            deleted_at = null,
        ).toEntity(TS)
        assertNull("aktywne łożysko nie może dostać nagrobka", aktywne.deletedAt)
    }

    @Test
    fun `nagrobek regalu z serwera zostaje nagrobkiem lokalnie`() {
        val skasowany = SyncShelfDto("x", "Regał 1", 1, 0.0, 30.0, deleted_at = "deleted").toEntity(TS)
        assertNotNull(skasowany.deletedAt)
        val aktywny = SyncShelfDto("y", "Regał 2", 2, 0.0, 30.0, deleted_at = null).toEntity(TS)
        assertNull(aktywny.deletedAt)
    }

    @Test
    fun `nagrobek aliasu kodu z serwera zostaje nagrobkiem lokalnie`() {
        val skasowany = SyncBarcodeAliasDto("x", "590123", "6205", deleted_at = "deleted").toEntity(TS)
        assertNotNull(skasowany.deletedAt)
        val aktywny = SyncBarcodeAliasDto("y", "590124", "6008", deleted_at = null).toEntity(TS)
        assertNull(aktywny.deletedAt)
    }

    @Test
    fun `pozostale pola przechodza bez zmian`() {
        val e = SyncBearingDto(
            id = "abc", symbol = "30204", typ = "stożkowe", d = 20.0, dZew = 47.0, B = 15.25,
            ilosc = 7, regal_id = "r1", reczny_przydzial = true, zrodlo = "offline", uwagi = "test",
        ).toEntity(TS)
        assertEquals("abc", e.id)
        assertEquals("30204", e.symbol)
        assertEquals(7, e.ilosc)
        assertEquals("r1", e.regalId)
        assertEquals(true, e.recznyPrzydzial)
        assertEquals(TS, e.updatedAt)
    }

    @Test
    fun `progi jada w obie strony`() {
        // Serwer -> telefon.
        val e = SyncBearingDto(
            id = "abc", symbol = "6205", typ = "kulkowe zwykłe", d = 25.0, dZew = 52.0, B = 15.0,
            ilosc = 1, regal_id = null, reczny_przydzial = false, zrodlo = "offline",
            uwagi = "wał corncrackera", stan_min = 5, stan_opt = 10, zapotrzebowanie = 10,
        ).toEntity(TS)
        assertEquals(5, e.stanMin)
        assertEquals(10, e.stanOpt)
        assertEquals(10, e.zapotrzebowanie)

        // Telefon -> serwer. Progi MUSZĄ wyjechać, inaczej apply_sync_push uzna, że ta
        // appka ich nie zna, i zostawi na serwerze poprzednie wartości.
        val dto = e.toSyncDto()
        assertEquals(5, dto.stan_min)
        assertEquals(10, dto.stan_opt)
        assertEquals(10, dto.zapotrzebowanie)
    }

    @Test
    fun `lozysko bez ustawionych progow ma zera`() {
        val e = BearingEntity(
            id = "x", symbol = "6008", typ = "", d = null, dZew = null, b = null, ilosc = 0,
            regalId = null, recznyPrzydzial = false, zrodlo = "recznie", uwagi = "",
        )
        assertEquals(0, e.toSyncDto().stan_min)
        assertEquals(0, e.stanOpt)
    }

    /**
     * Podpowiedzi są liczone WYŁĄCZNIE na serwerze, więc telefon nie może o nich
     * zakładać niczego poza kształtem - w szczególności `rodzaj` musi przejść jako
     * dowolny tekst, żeby nowa reguła na serwerze nie wywracała starszej appki.
     */
    @Test
    fun `podpowiedz z serwera zachowuje tresc i nieznany rodzaj`() {
        val p = SyncPowiadomienieDto(
            id = "pilne:abc", bearing_id = "abc", rodzaj = "zupelnie-nowa-regula",
            waga = "ostrzezenie", tytul = "Uzupełnij zapas", komunikat = "zostało 1 szt.",
        ).toEntity(TS)
        assertEquals("pilne:abc", p.id)
        assertEquals("abc", p.bearingId)
        assertEquals("zupelnie-nowa-regula", p.rodzaj)
        assertEquals("zostało 1 szt.", p.komunikat)
        assertEquals("znacznik pobrania jest potrzebny, by pokazać wiek danych offline", TS, p.pobranoO)
    }

    /** Podpowiedź ogólna (np. duplikat symbolu) nie dotyczy jednego rekordu. */
    @Test
    fun `podpowiedz bez lozyska ma puste bearingId`() {
        val p = SyncPowiadomienieDto("duplikat:6203", null, "duplikat", "ostrzezenie", "Zdublowany wpis", "…")
            .toEntity(TS)
        assertNull(p.bearingId)
    }

    private companion object {
        const val TS = 1_700_000_000_000L
    }
}
