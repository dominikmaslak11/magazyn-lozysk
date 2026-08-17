package pl.lozyska.offline.sync

import com.google.gson.annotations.SerializedName
import pl.lozyska.offline.data.BarcodeAliasEntity
import pl.lozyska.offline.data.BearingEntity
import pl.lozyska.offline.data.ShelfEntity
import pl.lozyska.offline.data.StockMoveEntity
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

// Format zgodny z database.py: sync_state() / apply_sync_push() na serwerze.
// To ŻYWY format do automatycznej synchronizacji - osobny od formatu ręcznego
// eksportu/importu JSON (JsonSync.kt).

data class SyncShelfDto(
    val id: String, val nazwa: String, val poziom: Int,
    val d_min: Double?, val d_max: Double?,
    val updated_at: String? = null, val deleted_at: String? = null,
    // Hierarchia lokalizacji - null u starszego serwera, wtedy węzeł jest korzeniem.
    val parent_id: String? = null, val poziom_typ: String? = null, val typy: String? = null,
)

data class SyncBearingDto(
    val id: String, val symbol: String, val typ: String,
    val d: Double?, @SerializedName("D") val dZew: Double?, val B: Double?,
    val ilosc: Int, val regal_id: String?, val reczny_przydzial: Boolean,
    val zrodlo: String, val uwagi: String?,
    val updated_at: String? = null, val deleted_at: String? = null,
)

data class SyncBarcodeAliasDto(
    val id: String, val kod: String, val symbol: String,
    val updated_at: String? = null, val deleted_at: String? = null,
)

data class SyncStateDto(
    val server_time: String,
    val shelves: List<SyncShelfDto>,
    val bearings: List<SyncBearingDto>,
    // Nullable - starsze serwery (sprzed mechanizmu wersjonowania) ich nie wysyłają.
    val server_version: String? = null,
    val min_client_version: String? = null,
    // Nullable z tego samego powodu - serwer sprzed aliasów kodów kreskowych ich nie zna.
    val barcode_aliases: List<SyncBarcodeAliasDto>? = null,
)

/** Ruch magazynowy wysyłany na serwer. `id` służy serwerowi do deduplikacji. */
data class SyncStockMoveDto(val id: String, val bearing_id: String, val delta: Int)

data class SyncPushRequest(
    val shelves: List<SyncShelfDto>,
    val bearings: List<SyncBearingDto>,
    val barcode_aliases: List<SyncBarcodeAliasDto> = emptyList(),
    val stock_moves: List<SyncStockMoveDto> = emptyList(),
)

/**
 * Podpowiedź wymiarów od modeli AI. Zapytanie idzie do WŁASNEGO serwera, nie do
 * dostawców AI - klucze API nigdy nie trafiają na telefon (patrz ai_assist.py).
 */
data class AiAvailability(val available: Boolean = false)

data class AiLookupRequest(val symbol: String)

data class AiLookupResponse(
    val symbol: String,
    val d: Double?, @SerializedName("D") val dZew: Double?, @SerializedName("B") val b: Double?,
    val typ: String?,
    val zgodnych: Int = 0,
    val odpytanych: Int = 0,
    val znaleziono: Boolean = false,
    val uwaga: String = "",
)

interface SyncApiService {
    @POST("api/ai/lookup")
    suspend fun aiLookup(@Body body: AiLookupRequest): AiLookupResponse

    @GET("api/ai/available")
    suspend fun aiAvailable(): AiAvailability

    @GET("api/sync/state")
    suspend fun getSyncState(): SyncStateDto

    @POST("api/sync/push")
    suspend fun pushSync(@Body body: SyncPushRequest): SyncStateDto
}

fun ShelfEntity.toSyncDto() = SyncShelfDto(
    id = id, nazwa = nazwa, poziom = poziom, d_min = dMin, d_max = dMax,
    deleted_at = deletedAt?.let { "deleted" },
    parent_id = parentId, poziom_typ = poziomTyp, typy = typy,
)

fun BearingEntity.toSyncDto() = SyncBearingDto(
    id = id, symbol = symbol, typ = typ, d = d, dZew = dZew, B = b, ilosc = ilosc,
    regal_id = regalId, reczny_przydzial = recznyPrzydzial, zrodlo = zrodlo, uwagi = uwagi,
    deleted_at = deletedAt?.let { "deleted" },
)

/**
 * Znacznik skasowania z serwera -> lokalny "nagrobek".
 *
 * UWAGA - tu był błąd, przez który skasowane rekordy WRACAŁY na telefon: konwersja
 * ustawiała deletedAt zawsze na null, więc nagrobek z serwera stawał się zwykłym,
 * aktywnym rekordem i przechodził przez filtr w Repository.replaceAllFromServer.
 * Objaw: łożysko skasowane na jednym urządzeniu nadal widniało na liście na drugim.
 */
private fun tombstone(deletedAt: String?, localTimestamp: Long): Long? =
    if (deletedAt != null) localTimestamp else null

fun SyncShelfDto.toEntity(localTimestamp: Long) = ShelfEntity(
    id = id, nazwa = nazwa, poziom = poziom, dMin = d_min, dMax = d_max,
    updatedAt = localTimestamp, deletedAt = tombstone(deleted_at, localTimestamp),
    parentId = parent_id, poziomTyp = poziom_typ ?: "regał", typy = typy ?: "",
)

fun StockMoveEntity.toSyncDto() = SyncStockMoveDto(id = id, bearing_id = bearingId, delta = delta)

fun BarcodeAliasEntity.toSyncDto() = SyncBarcodeAliasDto(
    id = id, kod = kod, symbol = symbol,
    deleted_at = deletedAt?.let { "deleted" },
)

fun SyncBarcodeAliasDto.toEntity(localTimestamp: Long) = BarcodeAliasEntity(
    id = id, kod = kod, symbol = symbol,
    updatedAt = localTimestamp, deletedAt = tombstone(deleted_at, localTimestamp),
)

fun SyncBearingDto.toEntity(localTimestamp: Long) = BearingEntity(
    id = id, symbol = symbol, typ = typ, d = d, dZew = dZew, b = B, ilosc = ilosc,
    regalId = regal_id, recznyPrzydzial = reczny_przydzial, zrodlo = zrodlo, uwagi = uwagi ?: "",
    updatedAt = localTimestamp, deletedAt = tombstone(deleted_at, localTimestamp),
)
