package pl.lozyska.klient

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp

private class ShelfFields(nazwa: String, poziom: String, dMin: String, dMax: String) {
    var nazwa by mutableStateOf(nazwa)
    var poziom by mutableStateOf(poziom)
    var dMin by mutableStateOf(dMin)
    var dMax by mutableStateOf(dMax)
}

@Composable
fun ShelvesScreen(vm: AppViewModel) {
    val localFields = remember { mutableStateMapOf<Int, ShelfFields>() }

    LaunchedEffect(vm.shelves.map { it.id }) {
        for (s in vm.shelves) {
            if (!localFields.containsKey(s.id)) {
                localFields[s.id] = ShelfFields(
                    s.nazwa, s.poziom.toString(),
                    s.d_min?.let { fmtNum(it) } ?: "", s.d_max?.let { fmtNum(it) } ?: "",
                )
            }
        }
    }

    fun saveAll(onDone: (() -> Unit)? = null) {
        var remaining = vm.shelves.size
        if (remaining == 0) { onDone?.invoke(); return }
        for (s in vm.shelves) {
            val f = localFields[s.id] ?: continue
            val payload = ShelfPayload(
                nazwa = f.nazwa.ifBlank { s.nazwa },
                poziom = f.poziom.toIntOrNull() ?: s.poziom,
                d_min = f.dMin.toDoubleOrNull(),
                d_max = f.dMax.toDoubleOrNull(),
            )
            vm.saveShelf(s.id, payload) {
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
            Button(onClick = { saveAll { vm.loadShelves() } }) { Text("Zapisz zmiany") }
            OutlinedButton(onClick = {
                saveAll {
                    vm.reassignAll { vm.loadShelves() }
                }
            }) { Text("Przelicz przydziały") }
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), contentPadding = PaddingValues(bottom = 24.dp)) {
            items(vm.shelves, key = { it.id }) { s ->
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
