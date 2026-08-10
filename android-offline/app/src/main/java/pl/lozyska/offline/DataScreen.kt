package pl.lozyska.offline

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun DataScreen(vm: OfflineViewModel) {
    val scope = rememberCoroutineScope()
    var pendingImportMode by remember { mutableStateOf("zastap") }

    val savedUrl by vm.serverUrl.collectAsState()
    var urlField by remember(savedUrl) { mutableStateOf(savedUrl) }
    val lastSyncAt by vm.lastSyncAt.collectAsState()
    val lastSyncStatus by vm.lastSyncStatus.collectAsState()
    val syncing by vm.syncing.collectAsState()

    val exportLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        uri?.let { vm.exportToUri(it) {} }
    }
    val importLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let { vm.importFromUri(it, pendingImportMode) {} }
    }

    val fileName = remember {
        "lozyska_offline_" + SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date()) + ".json"
    }

    Column(Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState())) {
        Card {
            Column(Modifier.padding(16.dp)) {
                Text("Synchronizacja z serwerem", style = MaterialTheme.typography.titleMedium)
                Text(
                    "Wpisz adres komputera z uruchomionym serwerem Magazynu Łożysk (python server.py), " +
                        "np. 192.168.1.23:8420, albo adres Tailscale (100.x.x.x:8420) dla dostępu spoza domu. " +
                        "Appka synchronizuje się automatycznie przy otwarciu i co ok. godzinę w tle, gdy jest " +
                        "połączenie - baza na telefonie działa też w pełni offline między synchronizacjami.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp, bottom = 12.dp),
                )
                OutlinedTextField(
                    value = urlField, onValueChange = { urlField = it },
                    label = { Text("Adres serwera") }, singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Row(Modifier.padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Button(
                        enabled = !syncing,
                        onClick = {
                            scope.launch {
                                vm.setServerUrl(urlField)
                                vm.syncNow()
                            }
                        },
                    ) { Text(if (syncing) "Synchronizuję..." else "Zapisz i synchronizuj teraz") }
                }
                Spacer(Modifier.height(10.dp))
                Text(syncStatusText(lastSyncAt, lastSyncStatus), style = MaterialTheme.typography.bodySmall,
                    color = if (lastSyncStatus == "blad" || lastSyncStatus == "wymagana_aktualizacja")
                        MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }

        Spacer(Modifier.height(12.dp))

        Card {
            Column(Modifier.padding(16.dp)) {
                Text("Ręczny backup / przenoszenie pliku", style = MaterialTheme.typography.titleMedium)
                Text(
                    "Poza automatyczną synchronizacją możesz też ręcznie wyeksportować/zaimportować plik JSON " +
                        "(ten sam format co wersja komputerowa/webowa) - przydatne jako dodatkowa kopia zapasowa.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp, bottom = 12.dp),
                )
                Button(onClick = { exportLauncher.launch(fileName) }) { Text("Eksportuj do pliku JSON") }
            }
        }

        Spacer(Modifier.height(12.dp))

        Card {
            Column(Modifier.padding(16.dp)) {
                Text("Import", style = MaterialTheme.typography.titleMedium)
                Text(
                    "„Zastąp” kasuje bieżące dane na telefonie i wczytuje plik od nowa. „Dopisz” dodaje " +
                        "łożyska z pliku jako nowe pozycje, nie ruszając obecnych regałów. Po imporcie warto " +
                        "od razu zsynchronizować się z serwerem.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp, bottom = 12.dp),
                )
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedButton(onClick = {
                        pendingImportMode = "zastap"
                        importLauncher.launch(arrayOf("application/json", "*/*"))
                    }) { Text("Zastąp bieżące dane") }
                    OutlinedButton(onClick = {
                        pendingImportMode = "dolacz"
                        importLauncher.launch(arrayOf("application/json", "*/*"))
                    }) { Text("Dopisz jako nowe") }
                }
            }
        }

        Spacer(Modifier.height(12.dp))
        Text(
            "Baza łożysk mieszka lokalnie na telefonie i działa w pełni offline. Internet/serwer są " +
                "używane do: doszukiwania wymiarów spoza wbudowanego katalogu oraz do synchronizacji, " +
                "ale nigdy nie są wymagane, żeby appka działała.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

private fun syncStatusText(lastSyncAt: Long, status: String): String {
    if (lastSyncAt == 0L) return "Nigdy jeszcze nie zsynchronizowano."
    val when_ = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date(lastSyncAt))
    return when (status) {
        "blad" -> "Ostatnia próba synchronizacji nieudana. Ostatnia udana: $when_"
        "wymagana_aktualizacja" -> "Synchronizacja wstrzymana - appka wymaga aktualizacji. Ostatnia udana: $when_"
        else -> "Ostatnia synchronizacja: $when_"
    }
}
