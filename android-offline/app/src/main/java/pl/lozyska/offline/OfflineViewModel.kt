package pl.lozyska.offline

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.map
import pl.lozyska.offline.data.*
import pl.lozyska.offline.sync.SyncEngine
import pl.lozyska.offline.sync.SyncResult
import pl.lozyska.offline.sync.SyncSettingsRepository
import pl.lozyska.offline.sync.isClientOutdated
import pl.lozyska.offline.sync.isUpdateAvailable
import pl.lozyska.offline.sync.normalizeBaseUrl

@OptIn(ExperimentalCoroutinesApi::class)
class OfflineViewModel(application: Application) : AndroidViewModel(application) {
    private val db = AppDatabase.get(application)
    private val repo = Repository(db)
    private val syncSettings = SyncSettingsRepository(application)
    private val syncEngine = SyncEngine(application)

    private val _search = MutableStateFlow("")
    val search: StateFlow<String> = _search

    val bearings: StateFlow<List<BearingEntity>> =
        _search.flatMapLatest { s -> repo.observeBearings(s) }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val shelves: StateFlow<List<ShelfWithCounts>> =
        repo.observeShelvesWithCounts().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    private val _message = MutableStateFlow<String?>(null)
    val message: StateFlow<String?> = _message
    fun clearMessage() { _message.value = null }

    val types = TypLozyska.values().map { it.etykieta }

    // --------------------------------------------------------- synchronizacja ----

    val serverUrl: StateFlow<String> = syncSettings.serverUrl.stateIn(viewModelScope, SharingStarted.Eagerly, "")
    val lastSyncAt: StateFlow<Long> = syncSettings.lastSyncAt.stateIn(viewModelScope, SharingStarted.Eagerly, 0L)
    val lastSyncStatus: StateFlow<String> = syncSettings.lastSyncStatus.stateIn(viewModelScope, SharingStarted.Eagerly, "")

    private val _syncing = MutableStateFlow(false)
    val syncing: StateFlow<Boolean> = _syncing

    // ----------------------------------------------------- wersjonowanie/aktualizacje ----

    /** Appka jest za stara, żeby bezpiecznie synchronizować się z serwerem - blokuje sync, nie działanie offline. */
    val updateRequired: StateFlow<Boolean> = syncSettings.minClientVersion
        .map { min -> isClientOutdated(BuildConfig.VERSION_NAME, min) }
        .stateIn(viewModelScope, SharingStarted.Eagerly, false)

    /** Serwer ma nowszą wersję niż ta zainstalowana, ale nadal kompatybilną - informacyjne, nie blokujące. */
    val updateAvailable: StateFlow<Boolean> = syncSettings.serverVersion
        .map { server -> isUpdateAvailable(BuildConfig.VERSION_NAME, server) }
        .stateIn(viewModelScope, SharingStarted.Eagerly, false)

    val latestServerVersion: StateFlow<String?> =
        syncSettings.serverVersion.stateIn(viewModelScope, SharingStarted.Eagerly, null)

    suspend fun setServerUrl(url: String) = syncSettings.setServerUrl(normalizeBaseUrl(url))

    fun syncNow() {
        if (_syncing.value) return
        viewModelScope.launch {
            _syncing.value = true
            when (val result = syncEngine.sync()) {
                is SyncResult.Success ->
                    _message.value = "Zsynchronizowano: ${result.bearingCount} łożysk, ${result.shelfCount} regałów."
                is SyncResult.NotConfigured ->
                    _message.value = "Ustaw adres serwera w zakładce Dane, żeby móc synchronizować."
                is SyncResult.Error ->
                    _message.value = "Synchronizacja nieudana: ${result.message}"
                is SyncResult.UpdateRequired ->
                    _message.value = "Ta wersja appki jest za stara, żeby synchronizować się z serwerem " +
                        "(serwer: ${result.serverVersion ?: "nowsza wersja"}). Zaktualizuj appkę."
            }
            _syncing.value = false
        }
    }

    fun setSearch(q: String) { _search.value = q }

    fun saveBearing(
        id: String?, symbol: String, typ: String, d: Double?, dZew: Double?, b: Double?,
        ilosc: Int, zrodlo: String, uwagi: String, regalId: String?, recznyPrzydzial: Boolean,
        onDone: () -> Unit,
    ) = viewModelScope.launch {
        repo.saveBearing(id, symbol, typ, d, dZew, b, ilosc, zrodlo, uwagi, regalId, recznyPrzydzial)
        onDone()
    }

    fun deleteBearing(bearing: BearingEntity, onDone: () -> Unit) = viewModelScope.launch {
        repo.deleteBearing(bearing)
        onDone()
    }

    fun saveShelf(shelf: ShelfEntity, onDone: () -> Unit = {}) = viewModelScope.launch {
        repo.saveShelf(shelf)
        onDone()
    }

    fun reassignAll(onDone: (Int) -> Unit) = viewModelScope.launch {
        val changed = repo.reassignAllAuto()
        onDone(changed)
    }

    fun lookupBySymbol(symbol: String, onResult: (LookupResult) -> Unit) = viewModelScope.launch {
        onResult(repo.lookupBySymbol(symbol))
    }

    fun lookupByDimensions(d: Double?, dZew: Double?, b: Double?, onResult: (List<DimensionCandidate>) -> Unit) =
        viewModelScope.launch { onResult(repo.lookupByDimensions(d, dZew, b)) }

    // --------------------------------------------------------- eksport/import (ręczny backup) ----

    fun exportToUri(uri: Uri, onDone: (Boolean) -> Unit) = viewModelScope.launch {
        try {
            val (shelvesList, bearingsList) = repo.exportSnapshot()
            val json = JsonSync.toJson(shelvesList, bearingsList)
            getApplication<Application>().contentResolver.openOutputStream(uri)?.use {
                it.write(json.toByteArray(Charsets.UTF_8))
            }
            _message.value = "Wyeksportowano ${bearingsList.size} łożysk i ${shelvesList.size} regałów."
            onDone(true)
        } catch (e: Exception) {
            _message.value = "Błąd eksportu: ${e.message}"
            onDone(false)
        }
    }

    fun importFromUri(uri: Uri, mode: String, onDone: (Boolean) -> Unit) = viewModelScope.launch {
        try {
            val text = getApplication<Application>().contentResolver.openInputStream(uri)?.bufferedReader()?.use { it.readText() }
                ?: throw IllegalStateException("Nie udało się odczytać pliku")
            val (shelvesList, bearingsList) = JsonSync.fromJson(text)
            if (mode == "zastap") {
                repo.importReplace(shelvesList, bearingsList)
            } else {
                repo.importAppend(bearingsList)
            }
            _message.value = "Zaimportowano ${bearingsList.size} łożysk, ${shelvesList.size} regałów."
            onDone(true)
        } catch (e: Exception) {
            _message.value = "Błąd importu: ${e.message ?: "niepoprawny plik"}"
            onDone(false)
        }
    }
}
