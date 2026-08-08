package pl.lozyska.offline

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import pl.lozyska.offline.data.BearingEntity
import pl.lozyska.offline.data.ShelfWithCounts

private val AUTO_SHELF: String? = null

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BearingEditSheet(vm: OfflineViewModel, bearing: BearingEntity?, onDismiss: () -> Unit, onSaved: () -> Unit) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val shelves by vm.shelves.collectAsState()

    var typ by remember { mutableStateOf(bearing?.typ ?: vm.types.firstOrNull() ?: "") }
    var symbol by remember { mutableStateOf(bearing?.symbol ?: "") }
    var d by remember { mutableStateOf(bearing?.d?.let { fmtInput(it) } ?: "") }
    var D by remember { mutableStateOf(bearing?.dZew?.let { fmtInput(it) } ?: "") }
    var B by remember { mutableStateOf(bearing?.b?.let { fmtInput(it) } ?: "") }
    var ilosc by remember { mutableStateOf((bearing?.ilosc ?: 1).toString()) }
    var uwagi by remember { mutableStateOf(bearing?.uwagi ?: "") }
    var source by remember { mutableStateOf(bearing?.zrodlo ?: "recznie") }
    var selectedShelf by remember { mutableStateOf(if (bearing?.recznyPrzydzial == true) bearing.regalId ?: AUTO_SHELF else AUTO_SHELF) }
    var note by remember { mutableStateOf<String?>(null) }

    fun sourceText() = when (source) {
        "offline" -> "Źródło danych: baza offline (pewne)"
        "internet" -> "Źródło danych: internet (orientacyjne - zweryfikuj suwmiarką)"
        else -> "Źródło danych: wpisane ręcznie"
    }

    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            Modifier
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp)
                .padding(bottom = 24.dp)
        ) {
            Text(
                if (bearing == null) "Dodaj łożysko" else "Edytuj łożysko",
                style = MaterialTheme.typography.titleLarge,
                modifier = Modifier.padding(bottom = 14.dp),
            )

            TypDropdown(selected = typ, options = vm.types, onSelected = { typ = it })
            Spacer(Modifier.height(10.dp))

            OutlinedTextField(
                value = symbol, onValueChange = { symbol = it },
                label = { Text("Symbol") }, singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            TextButton(onClick = {
                vm.lookupBySymbol(symbol) { result ->
                    symbol = result.symbol ?: symbol
                    result.d?.let { d = fmtInput(it) }
                    result.dZew?.let { D = fmtInput(it) }
                    result.b?.let { B = fmtInput(it) }
                    result.typ?.let { typ = it }
                    source = result.source
                    note = result.note
                }
            }) { Text("Pobierz wymiary") }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 6.dp)) {
                OutlinedTextField(value = d, onValueChange = { d = it }, label = { Text("d [mm]") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal), modifier = Modifier.weight(1f))
                OutlinedTextField(value = D, onValueChange = { D = it }, label = { Text("D [mm]") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal), modifier = Modifier.weight(1f))
                OutlinedTextField(value = B, onValueChange = { B = it }, label = { Text("B [mm]") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal), modifier = Modifier.weight(1f))
            }
            TextButton(onClick = {
                vm.lookupByDimensions(d.toDoubleOrNull(), D.toDoubleOrNull(), B.toDoubleOrNull()) { candidates ->
                    val first = candidates.firstOrNull()
                    if (first == null) {
                        note = "Nie znaleziono pasującego symbolu."
                    } else {
                        symbol = first.symbol
                        d = fmtInput(first.d)
                        D = fmtInput(first.dZew)
                        B = fmtInput(first.b)
                        if (first.typ.isNotBlank()) typ = first.typ
                        source = if (first.typ.isBlank()) "internet" else "offline"
                        note = if (candidates.size > 1) "Inne pasujące: ${candidates.drop(1).take(5).joinToString(", ") { c -> c.symbol }}"
                        else if (first.typ.isBlank()) "Propozycja z internetu - zweryfikuj przed zapisem." else null
                    }
                }
            }) { Text("Znajdź symbol na podstawie wymiarów") }

            Surface(tonalElevation = 1.dp, shape = MaterialTheme.shapes.small, modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
                Text(sourceText(), Modifier.padding(10.dp), style = MaterialTheme.typography.bodySmall)
            }
            note?.let {
                Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(bottom = 8.dp))
            }

            OutlinedTextField(
                value = ilosc, onValueChange = { ilosc = it }, label = { Text("Ilość sztuk") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
            )

            Spacer(Modifier.height(10.dp))
            ShelfDropdown(shelves = shelves, selectedId = selectedShelf, onSelected = { selectedShelf = it })

            OutlinedTextField(
                value = uwagi, onValueChange = { uwagi = it }, label = { Text("Uwagi") },
                modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
            )

            Row(Modifier.fillMaxWidth().padding(top = 18.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                if (bearing != null) {
                    OutlinedButton(onClick = {
                        vm.deleteBearing(bearing) { onSaved() }
                    }, colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)) { Text("Usuń") }
                }
                OutlinedButton(onClick = onDismiss, modifier = Modifier.weight(1f)) { Text("Anuluj") }
                Button(
                    onClick = {
                        vm.saveBearing(
                            id = bearing?.id, symbol = symbol.trim(), typ = typ,
                            d = d.toDoubleOrNull(), dZew = D.toDoubleOrNull(), b = B.toDoubleOrNull(),
                            ilosc = ilosc.toIntOrNull() ?: 0, zrodlo = source, uwagi = uwagi.trim(),
                            regalId = if (selectedShelf == AUTO_SHELF) null else selectedShelf,
                            recznyPrzydzial = selectedShelf != AUTO_SHELF,
                        ) { onSaved() }
                    },
                    modifier = Modifier.weight(1f),
                ) { Text("Zapisz") }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TypDropdown(selected: String, options: List<String>, onSelected: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
        OutlinedTextField(
            value = selected, onValueChange = {}, readOnly = true,
            label = { Text("Typ łożyska") },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier.fillMaxWidth().menuAnchor(),
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { opt ->
                DropdownMenuItem(text = { Text(opt) }, onClick = { onSelected(opt); expanded = false })
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ShelfDropdown(shelves: List<ShelfWithCounts>, selectedId: String?, onSelected: (String?) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val label = if (selectedId == AUTO_SHELF) "Auto (na podstawie średnicy D)"
        else shelves.find { it.id == selectedId }?.let { shelfLabel(it) } ?: "Auto (na podstawie średnicy D)"

    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
        OutlinedTextField(
            value = label, onValueChange = {}, readOnly = true,
            label = { Text("Regał") },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier.fillMaxWidth().menuAnchor(),
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            DropdownMenuItem(text = { Text("Auto (na podstawie średnicy D)") }, onClick = { onSelected(AUTO_SHELF); expanded = false })
            shelves.forEach { s ->
                DropdownMenuItem(text = { Text(shelfLabel(s)) }, onClick = { onSelected(s.id); expanded = false })
            }
        }
    }
}

private fun shelfLabel(s: ShelfWithCounts): String {
    val lo = s.dMin?.let { fmtInput(it) } ?: "0"
    val hi = s.dMax?.let { fmtInput(it) } ?: "∞"
    return "${s.nazwa} (poziom ${s.poziom}, D: $lo-$hi mm)"
}

private fun fmtInput(v: Double): String = if (v == v.toLong().toDouble()) v.toLong().toString() else v.toString()
