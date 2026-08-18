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
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import pl.lozyska.offline.data.*
import pl.lozyska.offline.sync.AiLookupRequest
import pl.lozyska.offline.sync.SyncApiClient
import pl.lozyska.offline.sync.SyncEngine
import pl.lozyska.offline.sync.SyncResult
import pl.lozyska.offline.sync.SyncSettingsRepository
import pl.lozyska.offline.sync.isClientOutdated
import pl.lozyska.offline.sync.isUpdateAvailable
import pl.lozyska.offline.sync.normalizeBaseUrl

/** Wynik rozpoznania zeskanowanego kodu - patrz OfflineViewModel.resolveScan. */
sealed class ScanOutcome {
    /** Znamy symbol łożyska (nasza naklejka QR albo zapamiętany wcześniej kod z pudełka). */
    data class Symbol(val symbol: String) : ScanOutcome()
    /** Kod handlowy (EAN/UPC), którego jeszcze nie skojarzono z żadnym łożyskiem. */
    data class UnknownBarcode(val kod: String) : ScanOutcome()
}

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

    /**
     * Podpowiedzi wyliczone przez serwer i pobrane przy ostatniej synchronizacji
     * (patrz PowiadomienieEntity). Telefon ich NIE liczy - trzyma jedno źródło prawdy.
     */
    val powiadomienia: StateFlow<List<PowiadomienieEntity>> =
        repo.observeNotifications().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    /** Podpowiedzi w rozbiciu na łożyska - do podświetlenia wierszy (id łożyska -> najcięższa waga). */
    val wagaWgLozyska: StateFlow<Map<String, String>> =
        repo.observeNotificationsByBearing().map { lista ->
            val kolejnosc = mapOf("krytyczna" to 0, "ostrzezenie" to 1, "informacja" to 2)
            lista.groupBy { it.bearingId!! }
                .mapValues { (_, p) -> p.minBy { kolejnosc[it.waga] ?: 9 }.waga }
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyMap())

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

    val authToken: StateFlow<String> = syncSettings.authToken.stateIn(viewModelScope, SharingStarted.Eagerly, "")

    suspend fun setServerUrl(url: String) = syncSettings.setServerUrl(normalizeBaseUrl(url))
    suspend fun setAuthToken(token: String) = syncSettings.setAuthToken(token)

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
                is SyncResult.Unauthorized ->
                    _message.value = "Serwer odrzucił połączenie - sprawdź token dostępu w zakładce Dane."
            }
            _syncing.value = false
        }
    }

    // --------------------------------------------- podpowiedzi AI ----

    /** Czy serwer ma skonfigurowane modele AI (UI chowa przycisk, gdy nie). */
    private val _aiDostepne = MutableStateFlow(false)
    val aiDostepne: StateFlow<Boolean> = _aiDostepne

    private val _aiTrwa = MutableStateFlow(false)
    val aiTrwa: StateFlow<Boolean> = _aiTrwa

    fun sprawdzAi() = viewModelScope.launch {
        val url = syncSettings.serverUrl.first()
        if (url.isBlank()) { _aiDostepne.value = false; return@launch }
        _aiDostepne.value = try {
            SyncApiClient.forBaseUrl(url, syncSettings.authToken.first()).aiAvailable().available
        } catch (e: Exception) { false }
    }

    /**
     * Pyta WŁASNY serwer o podpowiedź wymiarów od modeli AI. Klucze API zostają na
     * serwerze - telefon ich nigdy nie widzi. Wynik to propozycja: wymiary trafiają
     * do formularza oznaczone źródłem "ai", ale zapisuje je dopiero użytkownik.
     */
    fun askAi(symbol: String, onResult: (LookupResult?) -> Unit) = viewModelScope.launch {
        if (_aiTrwa.value) return@launch
        _aiTrwa.value = true
        try {
            val url = syncSettings.serverUrl.first()
            val r = SyncApiClient.forBaseUrl(url, syncSettings.authToken.first())
                .aiLookup(AiLookupRequest(symbol))
            if (r.znaleziono) {
                onResult(LookupResult(r.symbol, r.d, r.dZew, r.b, "ai", r.typ,
                    "AI: ${r.zgodnych}/${r.odpytanych} modeli zgodnych. ${r.uwaga}"))
            } else {
                _message.value = r.uwaga.ifBlank { "Modele nie znają tego oznaczenia." }
                onResult(null)
            }
        } catch (e: Exception) {
            _message.value = "Zapytanie do AI nieudane: ${e.message ?: "brak połączenia z serwerem"}"
            onResult(null)
        } finally {
            _aiTrwa.value = false
        }
    }

    fun setSearch(q: String) { _search.value = q }

    // ------------------------------------- skanowanie kodów z opakowań ----

    /**
     * Rozstrzyga, co zrobić z zeskanowanym kodem:
     *  - nasza własna naklejka QR zawiera wprost symbol łożyska -> używamy go od razu,
     *  - kod EAN/UPC z opakowania producenta to numer handlowy, nie oznaczenie łożyska
     *    -> sprawdzamy zapamiętane skojarzenia, a gdy kodu nie znamy, trzeba dopytać
     *       użytkownika (patrz ScanOutcome.UnknownBarcode).
     */
    fun resolveScan(rawValue: String, isProductBarcode: Boolean, onResult: (ScanOutcome) -> Unit) =
        viewModelScope.launch {
            val kod = rawValue.trim()
            if (!isProductBarcode) {
                onResult(ScanOutcome.Symbol(kod))
                return@launch
            }
            val known = repo.findSymbolByBarcode(kod)
            onResult(if (known != null) ScanOutcome.Symbol(known) else ScanOutcome.UnknownBarcode(kod))
        }

    /** Zapamiętuje "ten kod z pudełka = to łożysko" i synchronizuje to na pozostałe urządzenia. */
    fun rememberBarcode(kod: String, symbol: String, onDone: () -> Unit = {}) = viewModelScope.launch {
        repo.setBarcodeAlias(kod, symbol)
        _message.value = "Zapamiętano: kod $kod = $symbol."
        onDone()
    }

    fun saveBearing(
        id: String?, symbol: String, typ: String, d: Double?, dZew: Double?, b: Double?,
        ilosc: Int, zrodlo: String, uwagi: String, regalId: String?, recznyPrzydzial: Boolean,
        stanMin: Int = 0, stanOpt: Int = 0, zapotrzebowanie: Int = 0,
        onDone: () -> Unit,
    ) = viewModelScope.launch {
        repo.saveBearing(id, symbol, typ, d, dZew, b, ilosc, zrodlo, uwagi, regalId, recznyPrzydzial,
            stanMin, stanOpt, zapotrzebowanie)
        onDone()
    }

    /**
     * Wydanie/przyjęcie sztuk jednym tapnięciem (przyciski +/- na liście).
     * Zapisuje RÓŻNICĘ jako ruch magazynowy, nie ustawia wartości bezwzględnej -
     * dzięki temu równoległa zmiana z innego urządzenia nie zostaje nadpisana.
     */
    fun changeQuantity(bearing: BearingEntity, delta: Int) = viewModelScope.launch {
        val nowa = repo.changeQuantity(bearing, delta)
        if (nowa == bearing.ilosc && delta < 0) {
            _message.value = "${bearing.symbol}: stan już wynosi 0."
        }
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
