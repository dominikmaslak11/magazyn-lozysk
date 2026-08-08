package pl.lozyska.offline.data

import pl.lozyska.offline.BearingCatalog
import pl.lozyska.offline.KatalogWpis
import pl.lozyska.offline.OnlineLookup
import java.util.regex.Pattern

const val SOURCE_OFFLINE = "offline"
const val SOURCE_ONLINE = "internet"
const val SOURCE_MANUAL = "recznie"

data class LookupResult(
    val symbol: String?, val d: Double?, val dZew: Double?, val b: Double?,
    val source: String, val typ: String?, val note: String?,
)

data class DimensionCandidate(val symbol: String, val d: Double, val dZew: Double, val b: Double, val typ: String)

private val LETTER_PREFIXES = listOf("UC", "UK", "SB", "SA", "UCP", "UCF", "UCFL")

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

class Repository(private val db: AppDatabase) {
    private val bearingDao = db.bearingDao()
    private val shelfDao = db.shelfDao()

    fun observeBearings(search: String) = bearingDao.observeAll(search)
    fun observeShelvesWithCounts() = shelfDao.observeAllWithCounts()

    suspend fun getBearing(id: Int) = bearingDao.getById(id)

    suspend fun saveBearing(
        id: Int?, symbol: String, typ: String, d: Double?, dZew: Double?, b: Double?,
        ilosc: Int, zrodlo: String, uwagi: String, regalId: Int?, recznyPrzydzial: Boolean,
    ) {
        val finalRegalId = if (recznyPrzydzial) regalId else suggestShelfId(dZew)
        val entity = BearingEntity(
            id = id ?: 0, symbol = symbol, typ = typ, d = d, dZew = dZew, b = b, ilosc = ilosc,
            regalId = finalRegalId, recznyPrzydzial = recznyPrzydzial, zrodlo = zrodlo, uwagi = uwagi,
        )
        if (id == null) bearingDao.insert(entity) else bearingDao.update(entity)
    }

    suspend fun deleteBearing(bearing: BearingEntity) = bearingDao.delete(bearing)

    suspend fun saveShelf(shelf: ShelfEntity) = shelfDao.update(shelf)

    suspend fun suggestShelfId(outerDiameter: Double?): Int? {
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
        for (bearing in auto) {
            val newShelf = suggestShelfId(bearing.dZew)
            bearingDao.updateRegal(bearing.id, newShelf)
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
        val online = OnlineLookup.lookupDimensionsBySymbol(symbol)
        if (online != null) {
            return LookupResult(symbol, online.first, online.second, online.third, SOURCE_ONLINE, null,
                "Dane orientacyjne z internetu - zweryfikuj suwmiarką.")
        }
        return LookupResult(symbol, null, null, null, SOURCE_MANUAL, null, "Nie znaleziono - wpisz wymiary ręcznie.")
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

    // ------------------------------------------------------- eksport/import ----

    suspend fun exportSnapshot(): Pair<List<ShelfEntity>, List<BearingEntity>> =
        shelfDao.getAllOnce() to bearingDao.getAllOnce()

    suspend fun importReplace(shelves: List<ShelfEntity>, bearings: List<BearingEntity>) {
        bearingDao.deleteAll()
        shelfDao.deleteAll()
        val idMap = mutableMapOf<Int, Int>()
        for (s in shelves) {
            val newId = shelfDao.insert(s.copy(id = 0)).toInt()
            idMap[s.id] = newId
        }
        for (b in bearings) {
            bearingDao.insert(b.copy(id = 0, regalId = idMap[b.regalId]))
        }
    }

    suspend fun importAppend(bearings: List<BearingEntity>) {
        val shelves = shelfDao.getAllOnce()
        for (b in bearings) {
            val regalId = if (b.recznyPrzydzial) {
                // spróbuj dopasować po poziomie/nazwie, w razie braku - auto na podstawie D
                shelves.find { it.id == b.regalId }?.id ?: suggestShelfId(b.dZew)
            } else suggestShelfId(b.dZew)
            bearingDao.insert(b.copy(id = 0, regalId = regalId))
        }
    }
}
