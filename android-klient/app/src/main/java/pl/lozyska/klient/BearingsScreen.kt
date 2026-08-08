package pl.lozyska.klient

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay

private fun sourceLabel(z: String) = when (z) {
    "offline" -> "baza offline"
    "internet" -> "internet"
    else -> "ręcznie"
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BearingsScreen(vm: AppViewModel) {
    var search by remember { mutableStateOf("") }
    var editing by remember { mutableStateOf<Bearing?>(null) }
    var showAdd by remember { mutableStateOf(false) }
    var pendingDelete by remember { mutableStateOf<Bearing?>(null) }

    LaunchedEffect(search) {
        delay(250)
        vm.loadBearings(search)
    }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(onClick = { showAdd = true }) { Icon(Icons.Filled.Add, contentDescription = "Dodaj łożysko") }
        }
    ) { padding ->
        Column(Modifier.padding(padding).fillMaxSize().padding(horizontal = 12.dp)) {
            OutlinedTextField(
                value = search,
                onValueChange = { search = it },
                label = { Text("Szukaj po symbolu...") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
            )

            if (vm.isLoading.collectAsState().value && vm.bearings.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            } else if (vm.bearings.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Brak łożysk. Dodaj pierwsze przyciskiem +.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            } else {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), contentPadding = PaddingValues(bottom = 90.dp)) {
                    items(vm.bearings, key = { it.id }) { b ->
                        BearingCard(
                            bearing = b,
                            onEdit = { editing = b },
                            onDelete = { pendingDelete = b },
                        )
                    }
                }
            }
        }
    }

    if (showAdd) {
        BearingEditSheet(vm = vm, bearing = null, onDismiss = { showAdd = false }, onSaved = { showAdd = false; vm.loadBearings(search) })
    }
    editing?.let { b ->
        BearingEditSheet(vm = vm, bearing = b, onDismiss = { editing = null }, onSaved = { editing = null; vm.loadBearings(search) })
    }
    pendingDelete?.let { b ->
        AlertDialog(
            onDismissRequest = { pendingDelete = null },
            title = { Text("Usunąć łożysko?") },
            text = { Text("Usunąć łożysko ${b.symbol}?") },
            confirmButton = {
                TextButton(onClick = {
                    vm.deleteBearing(b.id) { vm.loadBearings(search) }
                    pendingDelete = null
                }) { Text("Usuń") }
            },
            dismissButton = { TextButton(onClick = { pendingDelete = null }) { Text("Anuluj") } },
        )
    }
}

@Composable
private fun BearingCard(bearing: Bearing, onEdit: () -> Unit, onDelete: () -> Unit) {
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
                Text("B ${fmt(bearing.B)} mm", style = MaterialTheme.typography.bodySmall)
            }
            Spacer(Modifier.height(2.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(bearing.typ, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("Ilość: ${bearing.ilosc}", fontWeight = FontWeight.Medium)
            }
            Text(
                (bearing.regal_nazwa ?: "—") + if (bearing.reczny_przydzial) " (ręcznie)" else "",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (!bearing.uwagi.isNullOrBlank()) {
                Text(bearing.uwagi, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Row(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.End) {
                TextButton(onClick = onEdit) { Icon(Icons.Filled.Edit, null, Modifier.size(18.dp)); Spacer(Modifier.width(4.dp)); Text("Edytuj") }
                TextButton(onClick = onDelete) { Icon(Icons.Filled.Delete, null, Modifier.size(18.dp)); Spacer(Modifier.width(4.dp)); Text("Usuń") }
            }
        }
    }
}

private fun fmt(v: Double?): String = if (v == null) "—" else if (v == v.toLong().toDouble()) v.toLong().toString() else v.toString()
