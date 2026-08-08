package pl.lozyska.klient

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(vm: AppViewModel) {
    val scope = rememberCoroutineScope()
    val savedUrl by vm.serverUrl.collectAsState()
    var urlField by remember(savedUrl) { mutableStateOf(savedUrl) }
    var testResult by remember { mutableStateOf<Pair<Boolean, String>?>(null) }
    var testing by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Text("Adres serwera", style = MaterialTheme.typography.titleMedium)
        Text(
            "Wpisz adres komputera, na którym działa serwer Magazynu Łożysk (python server.py), " +
                "np. http://192.168.1.23:8420. Telefon i komputer muszą być w tej samej sieci Wi-Fi.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 4.dp, bottom = 14.dp),
        )

        OutlinedTextField(
            value = urlField,
            onValueChange = { urlField = it; testResult = null },
            label = { Text("np. 192.168.1.23:8420") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )

        Row(Modifier.padding(top = 12.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            OutlinedButton(
                enabled = !testing,
                onClick = {
                    testing = true
                    vm.testConnection(urlField) { ok, msg ->
                        testing = false
                        testResult = ok to msg
                    }
                },
            ) { Text(if (testing) "Testuję..." else "Testuj połączenie") }

            Button(onClick = {
                scope.launch {
                    vm.setServerUrl(normalizeBaseUrl(urlField))
                }
            }) { Text("Zapisz adres") }
        }

        testResult?.let { (ok, msg) ->
            Text(
                msg,
                color = if (ok) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 10.dp),
            )
        }

        Spacer(Modifier.height(24.dp))
        Text(
            "Wskazówka: adres komputera znajdziesz w konsoli po uruchomieniu serwera - Flask wypisuje " +
                "linijkę \"Running on http://<adres>:8420\". Jeśli adres się zmienia (np. router przydziela go dynamicznie), " +
                "warto ustawić w routerze stały adres IP dla komputera.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
