package pl.lozyska.klient

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PUT
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import java.util.concurrent.TimeUnit

// ------------------------------------------------------------- ustawienia ----

val Context.settingsDataStore by preferencesDataStore(name = "ustawienia")
private val KEY_SERVER_URL = stringPreferencesKey("server_url")

class SettingsRepository(private val context: Context) {
    val serverUrl: Flow<String> = context.settingsDataStore.data.map { it[KEY_SERVER_URL] ?: "" }

    suspend fun setServerUrl(url: String) {
        context.settingsDataStore.edit { it[KEY_SERVER_URL] = url }
    }
}

fun normalizeBaseUrl(raw: String): String {
    var url = raw.trim()
    if (url.isEmpty()) return url
    if (!url.startsWith("http://") && !url.startsWith("https://")) url = "http://$url"
    if (!url.endsWith("/")) url = "$url/"
    return url
}

// ------------------------------------------------------------------ dane -----

data class OkResponse(val ok: Boolean)
data class IdResponse(val id: Int)

interface ApiService {
    @GET("api/types")
    suspend fun getTypes(): List<String>

    @GET("api/bearings")
    suspend fun getBearings(@Query("search") search: String? = null): List<Bearing>

    @POST("api/bearings")
    suspend fun addBearing(@Body payload: BearingPayload): IdResponse

    @PUT("api/bearings/{id}")
    suspend fun updateBearing(@Path("id") id: Int, @Body payload: BearingPayload): OkResponse

    @DELETE("api/bearings/{id}")
    suspend fun deleteBearing(@Path("id") id: Int): OkResponse

    @GET("api/lookup/symbol")
    suspend fun lookupBySymbol(@Query("symbol") symbol: String): LookupSymbolResult

    @GET("api/lookup/dimensions")
    suspend fun lookupByDimensions(
        @Query("d") d: Double?,
        @Query("D") D: Double?,
        @Query("B") B: Double?,
    ): List<DimensionCandidate>

    @GET("api/shelves")
    suspend fun getShelves(): List<Shelf>

    @PUT("api/shelves/{id}")
    suspend fun updateShelf(@Path("id") id: Int, @Body payload: ShelfPayload): OkResponse

    @POST("api/shelves/reassign")
    suspend fun reassignShelves(): ReassignResult
}

/** Retrofit trzeba przebudować za każdym razem gdy zmieni się adres serwera w Ustawieniach. */
object ApiClient {
    private var cachedBaseUrl: String? = null
    private var cachedService: ApiService? = null

    fun forBaseUrl(baseUrl: String): ApiService {
        val normalized = normalizeBaseUrl(baseUrl)
        cachedService?.let { if (cachedBaseUrl == normalized) return it }

        val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
        val client = OkHttpClient.Builder()
            .connectTimeout(8, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl(normalized)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        val service = retrofit.create(ApiService::class.java)
        cachedBaseUrl = normalized
        cachedService = service
        return service
    }
}
