package pl.lozyska.offline

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun DataScreen(vm: OfflineViewModel) {
    var pendingImportMode by remember { mutableStateOf("zastap") }

    val exportLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        uri?.let { vm.exportToUri(it) {} }
    }
    val importLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let { vm.importFromUri(it, pendingImportMode) {} }
    }

    val fileName = remember {
        "lozyska_offline_" + SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date()) + ".json"
    }

    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Card {
            Column(Modifier.padding(16.dp)) {
                Text("Kopia zapasowa i eksport", style = MaterialTheme.typography.titleMedium)
                Text(
                    "Eksport JSON jest w tym samym formacie co wersja komputerowa/webowa - plikiem " +
                        "możesz swobodnie przenosić dane w obie strony (telefon ↔ komputer), np. przez " +
                        "e-mail, chmurę albo kabel USB.",
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
                        "łożyska z pliku jako nowe pozycje, nie ruszając obecnych regałów.",
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
            "Ta appka działa w pełni offline - baza łożysk mieszka na telefonie i nie wymaga " +
                "komputera ani sieci Wi-Fi. Internet jest używany tylko opcjonalnie, gdy w oknie " +
                "dodawania łożyska szukasz wymiarów/symbolu, których nie ma w wbudowanym katalogu.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
