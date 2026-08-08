package pl.lozyska.offline.sync

import android.content.Context
import kotlinx.coroutines.flow.first
import pl.lozyska.offline.data.AppDatabase
import pl.lozyska.offline.data.Repository

sealed class SyncResult {
    data class Success(val bearingCount: Int, val shelfCount: Int) : SyncResult()
    object NotConfigured : SyncResult()
    data class Error(val message: String) : SyncResult()
}

/**
 * Silnik synchronizacji telefon <-> serwer. Algorytm (patrz też database.py na serwerze):
 *
 *  1. Wyślij (push) rekordy zmienione LOKALNIE od ostatniej udanej synchronizacji
 *     (porównanie wyłącznie względem WŁASNEGO zegara telefonu).
 *  2. Serwer bezwarunkowo zapisuje przychodzące rekordy (upsert po ID) i odsyła
 *     PEŁNY, aktualny stan (włącznie z nagrobkami skasowanych rekordów).
 *  3. Podmień CAŁĄ lokalną bazę na to, co przyszło z serwera - serwer jest
 *     jedynym źródłem prawdy, telefon to tylko podręczna kopia + bufor offline.
 *
 * Konflikty (dwa telefony edytują offline tę samą pozycję) rozstrzyga serwer
 * regułą "kto ostatni wypchnie zmianę, wygrywa" - proste i wystarczające dla
 * magazynu edytowanego przez kilka osób.
 */
class SyncEngine(private val context: Context) {
    private val settings = SyncSettingsRepository(context)

    suspend fun sync(): SyncResult {
        val baseUrl = settings.serverUrl.first()
        if (baseUrl.isBlank()) return SyncResult.NotConfigured

        val repo = Repository(AppDatabase.get(context))
        val lastSyncAt = settings.lastSyncAt.first()
        val syncStartedAt = System.currentTimeMillis()

        return try {
            val (localShelves, localBearings) = repo.getLocalChangesSince(lastSyncAt)
            val api = SyncApiClient.forBaseUrl(baseUrl)
            val serverState = api.pushSync(
                SyncPushRequest(
                    shelves = localShelves.map { it.toSyncDto() },
                    bearings = localBearings.map { it.toSyncDto() },
                )
            )

            repo.replaceAllFromServer(
                serverState.shelves.map { it.toEntity(syncStartedAt) },
                serverState.bearings.map { it.toEntity(syncStartedAt) },
            )

            settings.setLastSyncAt(syncStartedAt)
            settings.setLastSyncStatus("ok")
            SyncResult.Success(
                bearingCount = serverState.bearings.count { it.deleted_at == null },
                shelfCount = serverState.shelves.count { it.deleted_at == null },
            )
        } catch (e: Exception) {
            settings.setLastSyncStatus("blad")
            SyncResult.Error(e.message ?: "nieznany błąd połączenia")
        }
    }
}
