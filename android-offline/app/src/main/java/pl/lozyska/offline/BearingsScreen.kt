package pl.lozyska.offline

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import pl.lozyska.offline.data.BearingEntity
import pl.lozyska.offline.data.SearchQuery

private fun sourceLabel(z: String) = when (z) {
    "offline" -> "baza offline"
    "internet" -> "internet"
    else -> "ręcznie"
}

@Composable
fun BearingsScreen(vm: OfflineViewModel) {
    val search by vm.search.collectAsState()
    val bearings by vm.bearings.collectAsState()
    val shelves by vm.shelves.collectAsState()
    val shelfNames = remember(shelves) { shelves.associate { it.id to it.nazwa } }

    var editing by remember { mutableStateOf<BearingEntity?>(null) }
    var showAdd by remember { mutableStateOf(false) }
    var addInitialSymbol by remember { mutableStateOf<String?>(null) }
    var showScanner by remember { mutableStateOf(false) }
    var unknownBarcode by remember { mutableStateOf<String?>(null) }
    var pendingDelete by remember { mutableStateOf<BearingEntity?>(null) }

    val context = LocalContext.current
    val cameraPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) showScanner = true
    }
    fun launchScanner() {
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        if (granted) showScanner = true else cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
    }

    Scaffold(
        floatingActionButton = {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                SmallFloatingActionButton(onClick = { launchScanner() }) {
                    Icon(Icons.Filled.QrCodeScanner, contentDescription = "Skanuj kod QR/kreskowy")
                }
                FloatingActionButton(onClick = { addInitialSymbol = null; showAdd = true }) {
                    Icon(Icons.Filled.Add, contentDescription = "Dodaj łożysko")
                }
            }
        }
    ) { padding ->
        Column(Modifier.padding(padding).fillMaxSize().padding(horizontal = 12.dp)) {
            val wymiarowe = remember(search) { SearchQuery.parseDimensions(search) }
            OutlinedTextField(
                value = search,
                onValueChange = { vm.setSearch(it) },
                // Etykieta krótka celowo: dłuższa zawijała się na telefonie na dwie linie
                // i zjadała miejsce na wyniki. Szczegóły składni są w podpowiedzi niżej.
                label = { Text("Szukaj") },
                supportingText = {
                    Text(
                        wymiarowe?.let { w ->
                            "Wymiary: " + listOfNotNull(
                                w.d?.let { "d=${fmt(it)}" },
                                w.dZew?.let { "D=${fmt(it)}" },
                                w.b?.let { "B=${fmt(it)}" },
                            ).joinToString(" ") + " ±${SearchQuery.TOLERANCE}mm"
                        } ?: "symbol (6205) albo wymiary (25x52)",
                        style = MaterialTheme.typography.bodySmall,
                    )
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
            )

            if (bearings.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    // Rozróżnienie ma znaczenie: pusty magazyn to co innego niż filtr bez
                    // trafień. Wcześniej oba przypadki mówiły "dodaj pierwsze łożysko",
                    // co przy niepasującym wyszukiwaniu było zwyczajnie mylące.
                    Text(
                        if (search.isBlank()) "Brak łożysk. Dodaj pierwsze przyciskiem +."
                        else "Nic nie pasuje do \"$search\".",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            } else {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), contentPadding = PaddingValues(bottom = 90.dp)) {
                    items(bearings, key = { it.id }) { b ->
                        BearingCard(
                            bearing = b,
                            shelfName = b.regalId?.let { shelfNames[it] },
                            onEdit = { editing = b },
                            onDelete = { pendingDelete = b },
                            onChangeQuantity = { delta -> vm.changeQuantity(b, delta) },
                        )
                    }
                }
            }
        }
    }

    if (showScanner) {
        BarcodeScannerScreen(
            onResult = { value, isProductBarcode ->
                showScanner = false
                vm.resolveScan(value, isProductBarcode) { outcome ->
                    when (outcome) {
                        is ScanOutcome.Symbol -> {
                            addInitialSymbol = outcome.symbol
                            showAdd = true
                        }
                        // Kod z pudełka, którego jeszcze nie znamy - dopytujemy, zamiast
                        // wstawiać ciąg cyfr w pole "Symbol" i udawać, że to oznaczenie.
                        is ScanOutcome.UnknownBarcode -> unknownBarcode = outcome.kod
                    }
                }
            },
            onClose = { showScanner = false },
        )
    }
    unknownBarcode?.let { kod ->
        UnknownBarcodeDialog(
            kod = kod,
            onDismiss = { unknownBarcode = null },
            onConfirm = { symbol ->
                unknownBarcode = null
                vm.rememberBarcode(kod, symbol) {
                    addInitialSymbol = symbol
                    showAdd = true
                }
            },
        )
    }
    if (showAdd) {
        BearingEditSheet(
            vm = vm, bearing = null, initialSymbol = addInitialSymbol,
            onDismiss = { showAdd = false; addInitialSymbol = null },
            onSaved = { showAdd = false; addInitialSymbol = null },
        )
    }
    editing?.let { b ->
        BearingEditSheet(vm = vm, bearing = b, onDismiss = { editing = null }, onSaved = { editing = null })
    }
    pendingDelete?.let { b ->
        AlertDialog(
            onDismissRequest = { pendingDelete = null },
            title = { Text("Usunąć łożysko?") },
            text = { Text("Usunąć łożysko ${b.symbol}?") },
            confirmButton = {
                TextButton(onClick = { vm.deleteBearing(b) {}; pendingDelete = null }) { Text("Usuń") }
            },
            dismissButton = { TextButton(onClick = { pendingDelete = null }) { Text("Anuluj") } },
        )
    }
}

/**
 * Kod z opakowania, którego appka jeszcze nie zna. Pytamy RAZ, do jakiego łożyska należy -
 * odpowiedź zostaje zapamiętana i zsynchronizowana, więc kolejny skan tego samego pudełka
 * (na dowolnym telefonie) rozpozna je już bez pytania.
 */
@Composable
private fun UnknownBarcodeDialog(kod: String, onDismiss: () -> Unit, onConfirm: (String) -> Unit) {
    var symbol by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Nieznany kod z opakowania") },
        text = {
            Column {
                Text(
                    "Zeskanowany kod ($kod) to handlowy numer produktu, a nie oznaczenie łożyska - " +
                        "nie da się z niego odczytać symbolu ani wymiarów.",
                    style = MaterialTheme.typography.bodySmall,
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    "Podaj symbol łożyska w tym opakowaniu, a appka zapamięta to skojarzenie i " +
                        "następnym razem rozpozna je sama (także na pozostałych telefonach).",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = symbol, onValueChange = { symbol = it },
                    label = { Text("Symbol łożyska, np. 6205-2RS") },
                    singleLine = true, modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            TextButton(onClick = { onConfirm(symbol.trim()) }, enabled = symbol.isNotBlank()) {
                Text("Zapamiętaj")
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Anuluj") } },
    )
}

@Composable
private fun BearingCard(
    bearing: BearingEntity,
    shelfName: String?,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
    onChangeQuantity: (Int) -> Unit,
) {
    ElevatedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text(bearing.symbol, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                AssistChip(onClick = {}, label = { Text(sourceLabel(bearing.zrodlo), style = MaterialTheme.typography.labelSmall) })
            }
            Spacer(Modifier.height(4.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                Text("d ${fmt(bearing.d)} mm", style = MaterialTheme.typography.bodySmall)
                Text("D ${fmt(bearing.dZew)} mm", style = MaterialTheme.typography.bodySmall)
                Text("B ${fmt(bearing.b)} mm", style = MaterialTheme.typography.bodySmall)
            }
            Spacer(Modifier.height(2.dp))
            Text(bearing.typ, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                (shelfName ?: "—") + if (bearing.recznyPrzydzial) " (ręcznie)" else "",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (bearing.uwagi.isNotBlank()) {
                Text(bearing.uwagi, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }

            // Wydanie/przyjęcie sztuki to NAJCZĘSTSZA czynność w warsztacie - ma być
            // jednym tapnięciem, bez otwierania arkusza edycji.
            Row(
                Modifier.fillMaxWidth().padding(top = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    FilledTonalIconButton(
                        onClick = { onChangeQuantity(-1) },
                        enabled = bearing.ilosc > 0,
                        modifier = Modifier.size(38.dp),
                    ) { Icon(Icons.Filled.Remove, contentDescription = "Wydaj jedną sztukę") }

                    Text(
                        bearing.ilosc.toString(),
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.widthIn(min = 52.dp).padding(horizontal = 6.dp),
                        textAlign = TextAlign.Center,
                    )

                    FilledTonalIconButton(
                        onClick = { onChangeQuantity(+1) },
                        modifier = Modifier.size(38.dp),
                    ) { Icon(Icons.Filled.Add, contentDescription = "Przyjmij jedną sztukę") }

                    Text(" szt.", style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Row {
                    IconButton(onClick = onEdit) { Icon(Icons.Filled.Edit, contentDescription = "Edytuj") }
                    IconButton(onClick = onDelete) { Icon(Icons.Filled.Delete, contentDescription = "Usuń") }
                }
            }
        }
    }
}

private fun fmt(v: Double?): String = if (v == null) "—" else if (v == v.toLong().toDouble()) v.toLong().toString() else v.toString()
