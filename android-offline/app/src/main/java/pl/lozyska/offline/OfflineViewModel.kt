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
import pl.lozyska.offline.data.*

@OptIn(ExperimentalCoroutinesApi::class)
class OfflineViewModel(application: Application) : AndroidViewModel(application) {
    private val db = AppDatabase.get(application)
    private val repo = Repository(db)

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

    fun setSearch(q: String) { _search.value = q }

    fun saveBearing(
        id: Int?, symbol: String, typ: String, d: Double?, dZew: Double?, b: Double?,
        ilosc: Int, zrodlo: String, uwagi: String, regalId: Int?, recznyPrzydzial: Boolean,
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

    // --------------------------------------------------------- eksport/import ----

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
