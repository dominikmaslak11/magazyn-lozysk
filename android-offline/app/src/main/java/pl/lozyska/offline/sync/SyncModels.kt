package pl.lozyska.offline.sync

import com.google.gson.annotations.SerializedName
import pl.lozyska.offline.data.BearingEntity
import pl.lozyska.offline.data.ShelfEntity
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
)

data class SyncBearingDto(
    val id: String, val symbol: String, val typ: String,
    val d: Double?, @SerializedName("D") val dZew: Double?, val B: Double?,
    val ilosc: Int, val regal_id: String?, val reczny_przydzial: Boolean,
    val zrodlo: String, val uwagi: String?,
    val updated_at: String? = null, val deleted_at: String? = null,
)

data class SyncStateDto(
    val server_time: String,
    val shelves: List<SyncShelfDto>,
    val bearings: List<SyncBearingDto>,
    // Nullable - starsze serwery (sprzed mechanizmu wersjonowania) ich nie wysyłają.
    val server_version: String? = null,
    val min_client_version: String? = null,
)

data class SyncPushRequest(val shelves: List<SyncShelfDto>, val bearings: List<SyncBearingDto>)

interface SyncApiService {
    @GET("api/sync/state")
    suspend fun getSyncState(): SyncStateDto

    @POST("api/sync/push")
    suspend fun pushSync(@Body body: SyncPushRequest): SyncStateDto
}

fun ShelfEntity.toSyncDto() = SyncShelfDto(
    id = id, nazwa = nazwa, poziom = poziom, d_min = dMin, d_max = dMax,
    deleted_at = deletedAt?.let { "deleted" },
)

fun BearingEntity.toSyncDto() = SyncBearingDto(
    id = id, symbol = symbol, typ = typ, d = d, dZew = dZew, B = b, ilosc = ilosc,
    regal_id = regalId, reczny_przydzial = recznyPrzydzial, zrodlo = zrodlo, uwagi = uwagi,
    deleted_at = deletedAt?.let { "deleted" },
)

fun SyncShelfDto.toEntity(localTimestamp: Long) = ShelfEntity(
    id = id, nazwa = nazwa, poziom = poziom, dMin = d_min, dMax = d_max,
    updatedAt = localTimestamp, deletedAt = null,
)

fun SyncBearingDto.toEntity(localTimestamp: Long) = BearingEntity(
    id = id, symbol = symbol, typ = typ, d = d, dZew = dZew, b = B, ilosc = ilosc,
    regalId = regal_id, recznyPrzydzial = reczny_przydzial, zrodlo = zrodlo, uwagi = uwagi ?: "",
    updatedAt = localTimestamp, deletedAt = null,
)
