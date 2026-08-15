package pl.lozyska.offline.sync

import android.content.Context
import kotlinx.coroutines.flow.first
import pl.lozyska.offline.BuildConfig
import pl.lozyska.offline.data.AppDatabase
import pl.lozyska.offline.data.Repository

sealed class SyncResult {
    data class Success(val bearingCount: Int, val shelfCount: Int) : SyncResult()
    object NotConfigured : SyncResult()
    data class Error(val message: String) : SyncResult()
    /** Appka jest starsza niż min_client_version zgłoszone przez serwer - dane NIE zostały pobrane/wysłane. */
    data class UpdateRequired(val serverVersion: String?) : SyncResult()
    /** Serwer odrzucił żądanie (401) - brak tokenu albo token nieprawidłowy. */
    object Unauthorized : SyncResult()
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
            val localAliases = repo.getLocalAliasChangesSince(lastSyncAt)
            // Ruchy magazynowe wysyłamy WSZYSTKIE oczekujące, niezależnie od znacznika
            // czasu - kasujemy je dopiero po potwierdzeniu, więc zerwane połączenie nie
            // gubi zmiany stanu. Serwer deduplikuje po id, więc powtórka nic nie psuje.
            val pendingMoves = repo.getPendingMoves()
            val api = SyncApiClient.forBaseUrl(baseUrl, settings.authToken.first())
            val serverState = api.pushSync(
                SyncPushRequest(
                    shelves = localShelves.map { it.toSyncDto() },
                    bearings = localBearings.map { it.toSyncDto() },
                    barcode_aliases = localAliases.map { it.toSyncDto() },
                    stock_moves = pendingMoves.map { it.toSyncDto() },
                )
            )

            settings.setVersionInfo(serverState.server_version, serverState.min_client_version)

            if (isClientOutdated(BuildConfig.VERSION_NAME, serverState.min_client_version)) {
                // Za stara appka - NIE nadpisujemy lokalnej bazy danymi w formacie, którego
                // może nie rozumieć poprawnie. Lokalne zmiany zostały już wysłane wyżej
                // (pushSync), więc nic nie ginie - zostaną domergowane po aktualizacji.
                settings.setLastSyncStatus("wymagana_aktualizacja")
                return SyncResult.UpdateRequired(serverState.server_version)
            }

            repo.replaceAllFromServer(
                serverState.shelves.map { it.toEntity(syncStartedAt) },
                serverState.bearings.map { it.toEntity(syncStartedAt) },
                // Starszy serwer nie zna aliasów i nie odsyła tego pola - wtedy zostawiamy
                // lokalne skojarzenia w spokoju zamiast kasować je pustą listą.
                serverState.barcode_aliases?.map { it.toEntity(syncStartedAt) } ?: repo.getLocalAliasChangesSince(0L),
            )

            // Serwer potwierdził przyjęcie tych ruchów (są już wliczone w odesłany stan),
            // więc dopiero teraz można je skasować lokalnie.
            repo.clearMoves(pendingMoves.map { it.id })
            // Gdyby w międzyczasie doszedł nowy ruch, nakładamy go na świeży stan -
            // inaczej zniknąłby z ekranu do następnej synchronizacji.
            repo.reapplyPendingMoves()

            settings.setLastSyncAt(syncStartedAt)
            settings.setLastSyncStatus("ok")
            SyncResult.Success(
                bearingCount = serverState.bearings.count { it.deleted_at == null },
                shelfCount = serverState.shelves.count { it.deleted_at == null },
            )
        } catch (e: retrofit2.HttpException) {
            if (e.code() == 401) {
                // Bez tego użytkownik zobaczyłby gołe "HTTP 401" i nie wiedziałby, że chodzi o token.
                settings.setLastSyncStatus("brak_autoryzacji")
                SyncResult.Unauthorized
            } else {
                settings.setLastSyncStatus("blad")
                SyncResult.Error("serwer odpowiedział błędem ${e.code()}")
            }
        } catch (e: Exception) {
            settings.setLastSyncStatus("blad")
            SyncResult.Error(e.message ?: "nieznany błąd połączenia")
        }
    }
}
