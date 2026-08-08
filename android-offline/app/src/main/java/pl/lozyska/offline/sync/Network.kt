package pl.lozyska.offline.sync

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

val Context.syncDataStore by preferencesDataStore(name = "sync_ustawienia")
private val KEY_SERVER_URL = stringPreferencesKey("server_url")
private val KEY_LAST_SYNC_AT = longPreferencesKey("last_sync_at")
private val KEY_LAST_SYNC_STATUS = stringPreferencesKey("last_sync_status")

class SyncSettingsRepository(private val context: Context) {
    val serverUrl: Flow<String> = context.syncDataStore.data.map { it[KEY_SERVER_URL] ?: "" }
    val lastSyncAt: Flow<Long> = context.syncDataStore.data.map { it[KEY_LAST_SYNC_AT] ?: 0L }
    val lastSyncStatus: Flow<String> = context.syncDataStore.data.map { it[KEY_LAST_SYNC_STATUS] ?: "" }

    suspend fun setServerUrl(url: String) = context.syncDataStore.edit { it[KEY_SERVER_URL] = url }
    suspend fun setLastSyncAt(millis: Long) = context.syncDataStore.edit { it[KEY_LAST_SYNC_AT] = millis }
    suspend fun setLastSyncStatus(status: String) = context.syncDataStore.edit { it[KEY_LAST_SYNC_STATUS] = status }
}

fun normalizeBaseUrl(raw: String): String {
    var url = raw.trim()
    if (url.isEmpty()) return url
    if (!url.startsWith("http://") && !url.startsWith("https://")) url = "http://$url"
    if (!url.endsWith("/")) url = "$url/"
    return url
}

object SyncApiClient {
    private var cachedBaseUrl: String? = null
    private var cachedService: SyncApiService? = null

    fun forBaseUrl(baseUrl: String): SyncApiService {
        val normalized = normalizeBaseUrl(baseUrl)
        cachedService?.let { if (cachedBaseUrl == normalized) return it }

        val client = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl(normalized)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        val service = retrofit.create(SyncApiService::class.java)
        cachedBaseUrl = normalized
        cachedService = service
        return service
    }
}
