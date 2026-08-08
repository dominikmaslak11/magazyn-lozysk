package pl.lozyska.klient

import android.app.Application
import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class AppViewModel(application: Application) : AndroidViewModel(application) {
    private val settings = SettingsRepository(application)

    val serverUrl: StateFlow<String> = settings.serverUrl.stateIn(
        viewModelScope, SharingStarted.Eagerly, ""
    )

    val bearings = mutableStateListOf<Bearing>()
    val shelves = mutableStateListOf<Shelf>()
    val types = mutableStateListOf<String>()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage

    fun clearError() { _errorMessage.value = null }

    suspend fun setServerUrl(url: String) = settings.setServerUrl(url)

    private fun api() = ApiClient.forBaseUrl(serverUrl.value)

    private fun <T> launchSafely(block: suspend () -> T, onSuccess: (T) -> Unit) {
        viewModelScope.launch {
            if (serverUrl.value.isBlank()) {
                _errorMessage.value = "Ustaw adres serwera w zakładce Ustawienia."
                return@launch
            }
            _isLoading.value = true
            try {
                onSuccess(block())
            } catch (e: Exception) {
                _errorMessage.value = "Błąd połączenia: ${e.message ?: "sprawdź adres serwera i sieć Wi-Fi"}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun loadTypes() = launchSafely({ api().getTypes() }) { types.clear(); types.addAll(it) }

    fun loadBearings(search: String = "") = launchSafely({ api().getBearings(search.ifBlank { null }) }) {
        bearings.clear(); bearings.addAll(it)
    }

    fun loadShelves() = launchSafely({ api().getShelves() }) { shelves.clear(); shelves.addAll(it) }

    fun saveBearing(id: Int?, payload: BearingPayload, onDone: () -> Unit) = launchSafely({
        if (id != null) api().updateBearing(id, payload) else api().addBearing(payload)
    }) { onDone() }

    fun deleteBearing(id: Int, onDone: () -> Unit) = launchSafely({ api().deleteBearing(id) }) { onDone() }

    fun lookupBySymbol(symbol: String, onResult: (LookupSymbolResult) -> Unit) =
        launchSafely({ api().lookupBySymbol(symbol) }) { onResult(it) }

    fun lookupByDimensions(d: Double?, D: Double?, B: Double?, onResult: (List<DimensionCandidate>) -> Unit) =
        launchSafely({ api().lookupByDimensions(d, D, B) }) { onResult(it) }

    fun saveShelf(id: Int, payload: ShelfPayload, onDone: () -> Unit) =
        launchSafely({ api().updateShelf(id, payload) }) { onDone() }

    fun reassignAll(onDone: (Int) -> Unit) =
        launchSafely({ api().reassignShelves() }) { onDone(it.changed) }

    /** Testuje połączenie z podanym (jeszcze niezapisanym) adresem, niezależnie od zapisanego serverUrl. */
    fun testConnection(url: String, onResult: (Boolean, String) -> Unit) {
        viewModelScope.launch {
            try {
                val count = ApiClient.forBaseUrl(url).getTypes().size
                onResult(true, "Połączono! Serwer odpowiedział ($count typów łożysk).")
            } catch (e: Exception) {
                onResult(false, "Nie udało się połączyć: ${e.message ?: "sprawdź adres i sieć Wi-Fi"}")
            }
        }
    }
}
