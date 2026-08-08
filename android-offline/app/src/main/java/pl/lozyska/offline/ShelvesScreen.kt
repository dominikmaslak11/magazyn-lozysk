package pl.lozyska.offline

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import pl.lozyska.offline.data.ShelfEntity
import pl.lozyska.offline.data.ShelfWithCounts

private class ShelfFields(nazwa: String, poziom: String, dMin: String, dMax: String) {
    var nazwa by mutableStateOf(nazwa)
    var poziom by mutableStateOf(poziom)
    var dMin by mutableStateOf(dMin)
    var dMax by mutableStateOf(dMax)
}

@Composable
fun ShelvesScreen(vm: OfflineViewModel) {
    val shelves by vm.shelves.collectAsState()
    val localFields = remember { mutableStateMapOf<String, ShelfFields>() }

    LaunchedEffect(shelves.map { it.id }) {
        for (s in shelves) {
            if (!localFields.containsKey(s.id)) {
                localFields[s.id] = ShelfFields(
                    s.nazwa, s.poziom.toString(),
                    s.dMin?.let { fmtNum(it) } ?: "", s.dMax?.let { fmtNum(it) } ?: "",
                )
            }
        }
    }

    fun buildEntity(s: ShelfWithCounts): ShelfEntity? {
        val f = localFields[s.id] ?: return null
        return ShelfEntity(
            id = s.id,
            nazwa = f.nazwa.ifBlank { s.nazwa },
            poziom = f.poziom.toIntOrNull() ?: s.poziom,
            dMin = f.dMin.toDoubleOrNull(),
            dMax = f.dMax.toDoubleOrNull(),
        )
    }

    fun saveAll(onDone: (() -> Unit)? = null) {
        var remaining = shelves.size
        if (remaining == 0) { onDone?.invoke(); return }
        for (s in shelves) {
            val entity = buildEntity(s) ?: continue
            vm.saveShelf(entity) {
                remaining -= 1
                if (remaining == 0) onDone?.invoke()
            }
        }
    }

    Column(Modifier.fillMaxSize().padding(12.dp)) {
        Text(
            "Duże łożyska (większa średnica zewnętrzna D) trafiają na regały o niższym poziomie, " +
                "małe - na regały o wyższym poziomie. Łożyska przypisane ręcznie nie są ruszane przy przeliczaniu.",
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(bottom = 10.dp),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(bottom = 10.dp)) {
            Button(onClick = { saveAll() }) { Text("Zapisz zmiany") }
            OutlinedButton(onClick = {
                saveAll { vm.reassignAll { } }
            }) { Text("Przelicz przydziały") }
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), contentPadding = PaddingValues(bottom = 24.dp)) {
            items(shelves, key = { it.id }) { s ->
                val f = localFields[s.id] ?: return@items
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedTextField(
                                value = f.poziom, onValueChange = { f.poziom = it },
                                label = { Text("Poziom") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                modifier = Modifier.width(90.dp),
                            )
                            OutlinedTextField(
                                value = f.nazwa, onValueChange = { f.nazwa = it },
                                label = { Text("Nazwa") }, modifier = Modifier.weight(1f),
                            )
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 8.dp)) {
                            OutlinedTextField(
                                value = f.dMin, onValueChange = { f.dMin = it },
                                label = { Text("D od [mm]") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                                modifier = Modifier.weight(1f),
                            )
                            OutlinedTextField(
                                value = f.dMax, onValueChange = { f.dMax = it },
                                label = { Text("D do [mm]") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                                placeholder = { Text("bez limitu") }, modifier = Modifier.weight(1f),
                            )
                        }
                        Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                            Text("Pozycje: ${s.pozycje}", style = MaterialTheme.typography.bodySmall)
                            Text("Sztuki: ${s.sztuki}", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
    }
}

private fun fmtNum(v: Double): String = if (v == v.toLong().toDouble()) v.toLong().toString() else v.toString()
