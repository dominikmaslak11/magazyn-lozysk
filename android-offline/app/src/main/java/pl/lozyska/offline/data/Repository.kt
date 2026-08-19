package pl.lozyska.offline.data

import kotlinx.coroutines.flow.Flow
import pl.lozyska.offline.BearingCatalog
import pl.lozyska.offline.BearingTypeClassifier
import pl.lozyska.offline.KatalogWpis
import pl.lozyska.offline.OnlineLookup
import java.util.UUID
import java.util.regex.Pattern

const val SOURCE_OFFLINE = "offline"
const val SOURCE_ONLINE = "internet"
const val SOURCE_MANUAL = "recznie"

data class LookupResult(
    val symbol: String?, val d: Double?, val dZew: Double?, val b: Double?,
    val source: String, val typ: String?, val note: String?,
)

data class DimensionCandidate(val symbol: String, val d: Double, val dZew: Double, val b: Double, val typ: String)

/** 25.0 -> "25", 15.25 -> "15.25" (bez zbędnego ".0" w komunikatach). */
private fun fmtMm(v: Double): String =
    if (v == v.toLong().toDouble()) v.toLong().toString() else v.toString()

// Przedrostki serii, które trzeba ZACHOWAĆ (nie sprowadzać oznaczenia do samych cyfr).
// Bez tego "NU205" stałoby się "205" i szukalibyśmy w sieci zupełnie innego łożyska
// (realny przypadek: NU205 to 25x52x15, a wyszukiwarka na "205" zwracała 205x285x38).
// Sortowane od najdłuższego, żeby "NUP" wygrało z "NU", a "NU" z "N".
// Lista musi odpowiadać _LETTER_PREFIXES w lookup.py na serwerze.
private val LETTER_PREFIXES = listOf(
    "UCFL", "UCFC", "UCPH", "UCP", "UCF", "UCT", "UCX", "UC", "UK", "SB", "SA", "CSA",
    // ES/ESP MUSZĄ tu być: bez nich "ES208" redukowało się do "208", czyli do zwykłego
    // łożyska kulkowego 40x80x18 - zupełnie innej części. Ta sama pułapka, co przy NU205.
    "ESPA", "ESP", "ES",
    // INA/Schaeffler - liczba to wprost otwór w milimetrach (RAE35 = 35 mm).
    "GRAE", "RALE", "RASE", "RAE", "GRA",
    "NNU", "NNCF", "NCF", "NUP", "NN", "NU", "NJ", "NF",
    "RNAO", "RNA", "NKIA", "NKI", "NAO", "NA", "NK", "HK", "BK", "IR",
    "QJ",
).sortedByDescending { it.length }

fun normalizeSymbol(raw: String): String {
    if (raw.isBlank()) return ""
    val upper = raw.trim().uppercase()
    for (prefix in LETTER_PREFIXES) {
        val m = Pattern.compile("\\b$prefix\\s*-?\\s*(\\d{3,4})").matcher(upper)
        if (m.find()) return prefix + m.group(1)
    }
    val m = Pattern.compile("\\d{3,6}").matcher(upper)
    return if (m.find()) m.group(0) else upper
}

fun newLocalId(): String = UUID.randomUUID().toString()

class Repository(private val db: AppDatabase) {
    private val bearingDao = db.bearingDao()
    private val shelfDao = db.shelfDao()
    private val aliasDao = db.barcodeAliasDao()
    private val stockMoveDao = db.stockMoveDao()
    private val powiadomienieDao = db.powiadomienieDao()

    /**
     * Jedno pole wyszukiwania obsługuje dwa pytania: "czy mam 6205?" (po symbolu)
     * i "czy mam coś 25x52?" (po wymiarach). O tym, które to jest, decyduje sam zapis -
     * patrz SearchQuery.
     */
    fun observeBearings(search: String): Flow<List<BearingEntity>> {
        val wymiary = SearchQuery.parseDimensions(search)
        return if (wymiary != null)
            bearingDao.observeByDimensions(wymiary.d, wymiary.dZew, wymiary.b, SearchQuery.TOLERANCE)
        else
            bearingDao.observeAll(search)
    }
    fun observeShelvesWithCounts() = shelfDao.observeAllWithCounts()

    /** Podpowiedzi z ostatniej synchronizacji - patrz PowiadomienieEntity. */
    fun observeNotifications() = powiadomienieDao.observeAll()
    fun observeNotificationsByBearing() = powiadomienieDao.observeByBearing()

    /** Podmienia całą listę podpowiedzi (serwer je liczy, telefon tylko przechowuje). */
    suspend fun replaceNotifications(items: List<PowiadomienieEntity>) {
        powiadomienieDao.deleteAllHard()
        powiadomienieDao.insertAll(items)
    }

    suspend fun getBearing(id: String) = bearingDao.getById(id)

    suspend fun saveBearing(
        id: String?, symbol: String, typ: String, d: Double?, dZew: Double?, b: Double?,
        ilosc: Int, zrodlo: String, uwagi: String, regalId: String?, recznyPrzydzial: Boolean,
        stanMin: Int = 0, stanOpt: Int = 0, zapotrzebowanie: Int = 0,
        doWeryfikacji: Boolean = false,
    ) {
        val finalRegalId = if (recznyPrzydzial) regalId else suggestShelfId(dZew)
        val bearingId = id ?: newLocalId()
        // Ilość NIGDY nie jedzie na serwer jako wartość bezwzględna - liczy się różnica
        // względem stanu sprzed edycji, zapisana jako ruch magazynowy. Dzięki temu
        // równoległa zmiana z drugiego telefonu nie zostaje po cichu nadpisana.
        val poprzedniaIlosc = if (id == null) 0 else bearingDao.getById(id)?.ilosc ?: 0
        val entity = BearingEntity(
            id = bearingId, symbol = symbol, typ = typ, d = d, dZew = dZew, b = b, ilosc = ilosc,
            regalId = finalRegalId, recznyPrzydzial = recznyPrzydzial, zrodlo = zrodlo, uwagi = uwagi,
            updatedAt = System.currentTimeMillis(),
            stanMin = stanMin, stanOpt = stanOpt, zapotrzebowanie = zapotrzebowanie,
            doWeryfikacji = doWeryfikacji,
        )
        if (id == null) bearingDao.insert(entity) else bearingDao.update(entity)
        if (ilosc != poprzedniaIlosc) zapiszRuch(bearingId, ilosc - poprzedniaIlosc)
    }

    /**
     * Zmiana stanu o podaną liczbę sztuk (np. +1 / -1 z listy). Zwraca nowy stan.
     * Stan lokalny aktualizujemy od razu (żeby UI reagował natychmiast), a różnicę
     * zapisujemy jako ruch do wysłania przy najbliższej synchronizacji.
     */
    suspend fun changeQuantity(bearing: BearingEntity, delta: Int): Int {
        val nowaIlosc = (bearing.ilosc + delta).coerceAtLeast(0)
        val rzeczywistaZmiana = nowaIlosc - bearing.ilosc
        if (rzeczywistaZmiana == 0) return bearing.ilosc     // próba zejścia poniżej zera
        bearingDao.update(bearing.copy(ilosc = nowaIlosc, updatedAt = System.currentTimeMillis()))
        zapiszRuch(bearing.id, rzeczywistaZmiana)
        return nowaIlosc
    }

    private suspend fun zapiszRuch(bearingId: String, delta: Int) {
        stockMoveDao.insert(StockMoveEntity(id = newLocalId(), bearingId = bearingId, delta = delta))
    }

    /** Miękkie kasowanie - patrz komentarz przy BearingEntity.deletedAt (propagacja przy synchronizacji). */
    suspend fun deleteBearing(bearing: BearingEntity) = bearingDao.softDelete(bearing.id, System.currentTimeMillis())

    suspend fun saveShelf(shelf: ShelfEntity) = shelfDao.update(shelf.copy(updatedAt = System.currentTimeMillis()))

    suspend fun suggestShelfId(outerDiameter: Double?): String? {
        if (outerDiameter == null) return null
        val shelves = shelfDao.getAllOnce() // poziom malejąco
        if (shelves.isEmpty()) return null
        for (s in shelves) {
            val lo = s.dMin ?: Double.NEGATIVE_INFINITY
            val hi = s.dMax ?: Double.POSITIVE_INFINITY
            if (outerDiameter >= lo && outerDiameter < hi) return s.id
        }
        val biggest = shelves.maxBy { it.poziom }
        val smallest = shelves.minBy { it.poziom }
        return if (outerDiameter >= (biggest.dMin ?: 0.0)) biggest.id else smallest.id
    }

    suspend fun reassignAllAuto(): Int {
        val auto = bearingDao.getAutoAssigned()
        val now = System.currentTimeMillis()
        for (bearing in auto) {
            val newShelf = suggestShelfId(bearing.dZew)
            bearingDao.updateRegal(bearing.id, newShelf, now)
        }
        return auto.size
    }

    // -------------------------------------------------------------- lookup ----

    suspend fun lookupBySymbol(raw: String): LookupResult {
        val symbol = normalizeSymbol(raw)
        val entry = BearingCatalog.BY_SYMBOL[symbol]
        if (entry != null) {
            return LookupResult(entry.symbol, entry.d, entry.dZew, entry.b, SOURCE_OFFLINE, entry.typ.etykieta, null)
        }
        // Symbolu nie ma w katalogu, ale TYP wynika wprost z oznaczenia (ISO 15/355) -
        // bez katalogu i bez sieci. Klasyfikujemy z SUROWEGO wejścia, bo normalizeSymbol()
        // potrafi obciąć przedrostek literowy, który niesie informację o typie.
        val rozpoznanyTyp = BearingTypeClassifier.classify(raw)?.etykieta

        val online = OnlineLookup.lookupDimensionsBySymbol(symbol)
        var odrzuconeZSieci = false
        if (online != null) {
            // Wyszukiwarka potrafi zwrócić wymiary ZUPEŁNIE innego łożyska (realny przypadek:
            // dla 6204 przyszło 60x80 zamiast 20x47). Oznaczenie samo mówi, jaki powinien być
            // otwór, więc taki wynik odrzucamy zamiast zapisywać bzdurę.
            if (BearingTypeClassifier.dimensionsArePlausible(raw, online.first, online.second, online.third)) {
                return LookupResult(symbol, online.first, online.second, online.third, SOURCE_ONLINE,
                    rozpoznanyTyp, "Dane orientacyjne z internetu - zweryfikuj suwmiarką.")
            }
            odrzuconeZSieci = true
        }

        val note = when {
            odrzuconeZSieci -> {
                val oczekiwane = BearingTypeClassifier.boreFromSymbol(raw)
                if (oczekiwane != null)
                    "Wynik z internetu nie pasuje do tego oznaczenia (otwór powinien mieć ok. " +
                        "${fmtMm(oczekiwane)} mm) i został odrzucony. Wpisz wymiary ręcznie."
                else "Wynik z internetu nie pasuje do tego oznaczenia i został odrzucony. Wpisz wymiary ręcznie."
            }
            rozpoznanyTyp != null ->
                "Nie znaleziono wymiarów - typ rozpoznany z oznaczenia ($rozpoznanyTyp). Wpisz wymiary ręcznie."
            else -> "Nie znaleziono - wpisz wymiary ręcznie."
        }
        return LookupResult(symbol, null, null, null, SOURCE_MANUAL, rozpoznanyTyp, note)
    }

    suspend fun lookupByDimensions(d: Double?, dOut: Double?, b: Double?, tolerance: Double = 0.6): List<DimensionCandidate> {
        val scored = BearingCatalog.ENTRIES.mapNotNull { e: KatalogWpis ->
            var score = 0.0
            var checks = 0
            d?.let { score += Math.abs(e.d - it); checks++ }
            dOut?.let { score += Math.abs(e.dZew - it); checks++ }
            b?.let { score += Math.abs(e.b - it); checks++ }
            if (checks == 0) return@mapNotNull null
            val matches = (d == null || Math.abs(e.d - d) <= tolerance) &&
                (dOut == null || Math.abs(e.dZew - dOut) <= tolerance) &&
                (b == null || Math.abs(e.b - b) <= tolerance)
            if (matches) score to e else null
        }.sortedBy { it.first }.map { it.second }

        if (scored.isNotEmpty()) {
            return scored.take(8).map { DimensionCandidate(it.symbol, it.d, it.dZew, it.b, it.typ.etykieta) }
        }
        val onlineSymbol = OnlineLookup.lookupSymbolByDimensions(d, dOut, b)
        return if (onlineSymbol != null) {
            listOf(DimensionCandidate(onlineSymbol, d ?: 0.0, dOut ?: 0.0, b ?: 0.0, ""))
        } else emptyList()
    }

    // ------------------------------------------------------- eksport/import JSON (ręczny backup) ----

    suspend fun exportSnapshot(): Pair<List<ShelfEntity>, List<BearingEntity>> =
        shelfDao.getAllOnce() to bearingDao.getAllOnce()

    suspend fun importReplace(shelves: List<ShelfEntity>, bearings: List<BearingEntity>) {
        bearingDao.deleteAllHard()
        shelfDao.deleteAllHard()
        shelfDao.insertAll(shelves)
        bearingDao.insertAll(bearings)
    }

    suspend fun importAppend(bearings: List<BearingEntity>) {
        val shelves = shelfDao.getAllOnce()
        val now = System.currentTimeMillis()
        for (b in bearings) {
            val regalId = if (b.recznyPrzydzial) {
                shelves.find { it.id == b.regalId }?.id ?: suggestShelfId(b.dZew)
            } else suggestShelfId(b.dZew)
            bearingDao.insert(b.copy(id = newLocalId(), regalId = regalId, updatedAt = now))
        }
    }

    // ----------------------------------------------------- synchronizacja z serwerem ----
    // Szczegóły algorytmu: patrz SyncEngine.kt oraz komentarz nad sync_state()/
    // apply_sync_push() w database.py (serwer).

    suspend fun getLocalChangesSince(sinceLocalMillis: Long): Pair<List<ShelfEntity>, List<BearingEntity>> =
        shelfDao.getChangedSince(sinceLocalMillis) to bearingDao.getChangedSince(sinceLocalMillis)

    suspend fun getLocalAliasChangesSince(sinceLocalMillis: Long): List<BarcodeAliasEntity> =
        aliasDao.getChangedSince(sinceLocalMillis)

    /** Ruchy magazynowe czekające na wysłanie (kasowane dopiero po potwierdzeniu). */
    suspend fun getPendingMoves(): List<StockMoveEntity> = stockMoveDao.getPending()

    suspend fun clearMoves(ids: List<String>) {
        if (ids.isNotEmpty()) stockMoveDao.deleteByIds(ids)
    }

    /** Podmienia CAŁĄ lokalną bazę na stan otrzymany z serwera (serwer jest źródłem prawdy). */
    suspend fun replaceAllFromServer(
        shelves: List<ShelfEntity>,
        bearings: List<BearingEntity>,
        aliases: List<BarcodeAliasEntity> = emptyList(),
    ) {
        shelfDao.deleteAllHard()
        bearingDao.deleteAllHard()
        aliasDao.deleteAllHard()
        // nie wstawiamy rekordów skasowanych na serwerze (deletedAt != null) - to tylko nagrobki do propagacji
        shelfDao.insertAll(shelves.filter { it.deletedAt == null })
        bearingDao.insertAll(bearings.filter { it.deletedAt == null })
        aliasDao.insertAll(aliases.filter { it.deletedAt == null })
    }

    /**
     * Nakłada na świeżo pobrany stan te ruchy, które nadal czekają na wysłanie.
     *
     * Potrzebne, gdy użytkownik zmieni stan W TRAKCIE synchronizacji: taki ruch nie
     * zdążył pojechać w tej rundzie, więc stan z serwera go nie zawiera. Bez tego
     * zmiana zniknęłaby z ekranu aż do następnej synchronizacji, choć nie jest zgubiona.
     */
    suspend fun reapplyPendingMoves() {
        val oczekujace = stockMoveDao.getPending()
        if (oczekujace.isEmpty()) return
        for ((bearingId, ruchy) in oczekujace.groupBy { it.bearingId }) {
            val bearing = bearingDao.getById(bearingId) ?: continue
            val suma = ruchy.sumOf { it.delta }
            bearingDao.update(bearing.copy(ilosc = (bearing.ilosc + suma).coerceAtLeast(0)))
        }
    }

    // ------------------------------------- aliasy kodów kreskowych (opakowania) ----

    /** Symbol łożyska zapamiętany dla tego kodu z opakowania, albo null gdy appka go nie zna. */
    suspend fun findSymbolByBarcode(kod: String): String? = aliasDao.findSymbolByKod(kod.trim())

    /** Zapamiętuje skojarzenie kod -> symbol (nadpisuje poprzednie dla tego samego kodu). */
    suspend fun setBarcodeAlias(kod: String, symbol: String) {
        val normalized = kod.trim()
        val existing = aliasDao.findByKod(normalized)
        aliasDao.insert(
            BarcodeAliasEntity(
                id = existing?.id ?: UUID.randomUUID().toString(),
                kod = normalized,
                symbol = symbol.trim(),
                updatedAt = System.currentTimeMillis(),
            )
        )
    }
}
