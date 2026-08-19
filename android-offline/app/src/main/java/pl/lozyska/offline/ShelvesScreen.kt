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
        return zaktualizowanaPolka(s, f.nazwa, f.poziom, f.dMin, f.dMax)
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
                        if (s.bufor) {
                            Text("miejsce tymczasowe (bufor)", style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.primary)
                        }
                        Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                            Text("Pozycje: ${s.pozycje}", style = MaterialTheme.typography.bodySmall)
                            Text("Sztuki: ${s.sztuki}", style = MaterialTheme.typography.bodySmall)
                        }
                        // Wymiary tylko do odczytu: mierzy się je miarą i wpisuje w wersji
                        // webowej, a na telefonie służą do sprawdzenia "czy to tu wejdzie".
                        wymiaryPolki(s)?.let {
                            Text(it, style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }
    }
}

/**
 * Rekord półki po edycji formularza na tym ekranie.
 *
 * UWAGA - tu był błąd: rekord budowano od zera, więc pola, których ten ekran nie
 * edytuje, wracały do wartości domyślnych. Zapis regału z telefonu KASOWAŁ wtedy
 * przypisanie do rodzica (parentId = null), spłaszczając całą hierarchię lokalizacji
 * do listy korzeni, a przy okazji czyścił dedykowane typy i zmierzone wymiary -
 * i taki "wyczyszczony" rekord jechał następnie na serwer, na wszystkie urządzenia.
 *
 * Wszystko, czego formularz nie dotyka, MUSI tu przejść bez zmian.
 */
internal fun zaktualizowanaPolka(
    s: ShelfWithCounts, nazwa: String, poziom: String, dMin: String, dMax: String,
) = ShelfEntity(
    id = s.id,
    nazwa = nazwa.ifBlank { s.nazwa },
    poziom = poziom.toIntOrNull() ?: s.poziom,
    dMin = dMin.toDoubleOrNull(),
    dMax = dMax.toDoubleOrNull(),
    parentId = s.parentId,
    poziomTyp = s.poziomTyp,
    typy = s.typy,
    szerokoscMm = s.szerokoscMm,
    glebokoscMm = s.glebokoscMm,
    wysokoscMm = s.wysokoscMm,
    bufor = s.bufor,
)

/** "88 × 50 × 21 cm (prześwit)" albo null, gdy półki nie zmierzono. */
private fun wymiaryPolki(s: ShelfWithCounts): String? {
    val sz = s.szerokoscMm ?: return null
    val gl = s.glebokoscMm ?: return null
    val cm = { v: Double -> fmtNum(v / 10.0) }
    val wys = s.wysokoscMm?.let { " × ${cm(it)} cm prześwitu" } ?: ""
    return "${cm(sz)} × ${cm(gl)} cm$wys"
}

private fun fmtNum(v: Double): String = if (v == v.toLong().toDouble()) v.toLong().toString() else v.toString()
