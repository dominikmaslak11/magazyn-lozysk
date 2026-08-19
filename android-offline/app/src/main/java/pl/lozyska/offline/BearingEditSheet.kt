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
import pl.lozyska.offline.data.LookupResult
import pl.lozyska.offline.data.ShelfWithCounts

private val AUTO_SHELF: String? = null

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BearingEditSheet(
    vm: OfflineViewModel,
    bearing: BearingEntity?,
    initialSymbol: String? = null,
    onDismiss: () -> Unit,
    onSaved: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val shelves by vm.shelves.collectAsState()
    val aiDostepne by vm.aiDostepne.collectAsState()
    val aiTrwa by vm.aiTrwa.collectAsState()
    LaunchedEffect(Unit) { vm.sprawdzAi() }

    var typ by remember { mutableStateOf(bearing?.typ ?: vm.types.firstOrNull() ?: "") }
    var symbol by remember { mutableStateOf(bearing?.symbol ?: initialSymbol ?: "") }
    var d by remember { mutableStateOf(bearing?.d?.let { fmtInput(it) } ?: "") }
    var D by remember { mutableStateOf(bearing?.dZew?.let { fmtInput(it) } ?: "") }
    var B by remember { mutableStateOf(bearing?.b?.let { fmtInput(it) } ?: "") }
    var ilosc by remember { mutableStateOf((bearing?.ilosc ?: 1).toString()) }
    var uwagi by remember { mutableStateOf(bearing?.uwagi ?: "") }
    // Puste pole = 0 = "nie pilnuj tej pozycji". Pokazujemy pustkę zamiast zera, żeby
    // nie sugerować, że próg został świadomie ustawiony na zero.
    var stanMin by remember { mutableStateOf(bearing?.stanMin?.takeIf { it > 0 }?.toString() ?: "") }
    var stanOpt by remember { mutableStateOf(bearing?.stanOpt?.takeIf { it > 0 }?.toString() ?: "") }
    var zapotrzebowanie by remember { mutableStateOf(bearing?.zapotrzebowanie?.takeIf { it > 0 }?.toString() ?: "") }
    var source by remember { mutableStateOf(bearing?.zrodlo ?: "recznie") }
    var selectedShelf by remember { mutableStateOf(if (bearing?.recznyPrzydzial == true) bearing.regalId ?: AUTO_SHELF else AUTO_SHELF) }
    var note by remember { mutableStateOf<String?>(null) }

    // Gdy użytkownik sam wybierze typ z listy, przestajemy go nadpisywać rozpoznaniem
    // z symbolu - ręczna decyzja ma pierwszeństwo nad automatem (ta sama zasada co przy
    // ręcznym przydziale regału).
    //
    // Przy EDYCJI istniejącego łożyska zakładamy ręczny wybór wtedy, gdy zapisany typ
    // różni się od tego, co wynika z oznaczenia - to ślad świadomej decyzji sprzed lat,
    // której poprawka literówki w symbolu nie powinna po cichu skasować.
    var typWybranyRecznie by remember {
        mutableStateOf(
            bearing != null && bearing.typ.isNotBlank() &&
                BearingTypeClassifier.classify(bearing.symbol)?.etykieta.let { it != null && it != bearing.typ }
        )
    }
    // Informacja "rozpoznano X z oznaczenia" pokazywana pod listą typów.
    var typZOznaczenia by remember { mutableStateOf<String?>(null) }

    /**
     * Rozpoznaje kategorię na bieżąco, w trakcie wpisywania symbolu - bez czekania na
     * "Pobierz wymiary" ani na skan. Klasyfikacja jest lokalna i natychmiastowa
     * (patrz BearingTypeClassifier), więc nie ma tu żadnego ruchu sieciowego.
     */
    fun onSymbolChanged(nowy: String) {
        symbol = nowy
        val rozpoznany = BearingTypeClassifier.classify(nowy)?.etykieta
        typZOznaczenia = rozpoznany
        if (rozpoznany != null && !typWybranyRecznie) typ = rozpoznany
    }

    fun applyLookupResult(result: LookupResult) {
        symbol = result.symbol ?: symbol
        result.d?.let { d = fmtInput(it) }
        result.dZew?.let { D = fmtInput(it) }
        result.b?.let { B = fmtInput(it) }
        result.typ?.let { typ = it }
        source = result.source
        note = result.note
    }

    // Symbol z zeskanowanego kodu QR/kreskowego (patrz BarcodeScannerScreen) - dociągnij
    // wymiary automatycznie, tak jak przy ręcznym kliknięciu "Pobierz wymiary".
    LaunchedEffect(initialSymbol) {
        if (bearing == null && !initialSymbol.isNullOrBlank()) {
            vm.lookupBySymbol(initialSymbol) { applyLookupResult(it) }
        }
    }

    fun sourceText() = when (source) {
        "offline" -> "Źródło danych: baza offline (pewne)"
        "internet" -> "Źródło danych: internet (orientacyjne - zweryfikuj suwmiarką)"
        "ai" -> "Źródło danych: modele AI (propozycja - zweryfikuj suwmiarką)"
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

            // Symbol PRZED typem: wpisanie oznaczenia samo ustawia kategorię poniżej,
            // więc taka kolejność czyta się naturalnie (najpierw przyczyna, potem skutek).
            OutlinedTextField(
                value = symbol, onValueChange = { onSymbolChanged(it) },
                label = { Text("Symbol") }, singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Row {
                TextButton(onClick = { vm.lookupBySymbol(symbol) { applyLookupResult(it) } }) { Text("Pobierz wymiary") }
                // Widoczne tylko, gdy serwer ma skonfigurowane modele. Zapytanie idzie do
                // NASZEGO serwera - klucze API nigdy nie trafiają na telefon.
                if (aiDostepne) {
                    TextButton(
                        onClick = { vm.askAi(symbol) { wynik -> wynik?.let { applyLookupResult(it) } } },
                        enabled = !aiTrwa && symbol.isNotBlank(),
                    ) { Text(if (aiTrwa) "Pytam AI..." else "Zapytaj AI") }
                }
            }

            Spacer(Modifier.height(6.dp))
            TypDropdown(
                selected = typ,
                options = vm.types,
                onSelected = { typ = it; typWybranyRecznie = true },
            )
            opisTypu(typ)?.let {
                Text(it, style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp))
            }
            typZOznaczenia?.let { rozpoznany ->
                Text(
                    if (typWybranyRecznie && typ != rozpoznany)
                        "Z oznaczenia wynika: $rozpoznany (zostawiono Twój wybór)"
                    else "Kategoria rozpoznana z oznaczenia",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }

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
                supportingText = { Text("Np. \"wał corncrackera\" - wyszukiwarka przeszukuje też to pole.",
                    style = MaterialTheme.typography.bodySmall) },
                modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
            )

            // Progi magazynowe. Wystarczy wypełnić samo roczne zużycie - resztę serwer
            // wyprowadzi (optymalny = zużycie, minimalny = połowa), patrz progi_lozyska().
            Spacer(Modifier.height(14.dp))
            Text("Progi magazynowe (opcjonalne)", style = MaterialTheme.typography.titleSmall)
            Text(
                "Puste = appka nie pilnuje tej pozycji. Wystarczy podać roczne zużycie.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 2.dp, bottom = 6.dp),
            )
            // Zużycie osobno, nad progami: to jedyne pole, które trzeba wypełnić, a w rzędzie
            // po trzy etykiety łamały się na telefonie w połowie słowa ("Optym / alnie").
            OutlinedTextField(
                value = zapotrzebowanie, onValueChange = { zapotrzebowanie = it },
                label = { Text("Roczne zużycie [szt.]") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 8.dp)) {
                OutlinedTextField(value = stanMin, onValueChange = { stanMin = it },
                    label = { Text("Minimum") }, singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.weight(1f))
                OutlinedTextField(value = stanOpt, onValueChange = { stanOpt = it },
                    label = { Text("Optymalnie") }, singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.weight(1f))
            }

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
                            stanMin = stanMin.toIntOrNull() ?: 0,
                            stanOpt = stanOpt.toIntOrNull() ?: 0,
                            zapotrzebowanie = zapotrzebowanie.toIntOrNull() ?: 0,
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
        else shelves.find { it.id == selectedId }?.let { sciezkaLokalizacji(it, shelves) }
            ?: "Auto (na podstawie średnicy D)"

    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
        OutlinedTextField(
            value = label, onValueChange = {}, readOnly = true,
            label = { Text("Lokalizacja") },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier.fillMaxWidth().menuAnchor(),
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            DropdownMenuItem(text = { Text("Auto (na podstawie średnicy D)") }, onClick = { onSelected(AUTO_SHELF); expanded = false })
            shelves.forEach { s ->
                DropdownMenuItem(
                    text = { Text(sciezkaLokalizacji(s, shelves)) },
                    onClick = { onSelected(s.id); expanded = false },
                )
            }
        }
    }
}

/**
 * Krótkie wyjaśnienie typu tam, gdzie się go wybiera.
 *
 * Dopisane dla serii wstawkowych, bo UC208 i ES208 mają ten sam otwór i tę samą
 * średnicę zewnętrzną (40 x 80 mm) i bez podpowiedzi nie da się ich odróżnić
 * z samej nazwy typu - a jedna nie zastąpi drugiej w maszynie.
 */
private fun opisTypu(typ: String): String? = when (typ) {
    "wstawkowe (UC)" -> "Do opraw; kulista powierzchnia zewnętrzna (samonastawne w oprawie). " +
        "Mocowane DWOMA WKRĘTAMI dociskowymi, szeroki pierścień wewnętrzny."
    "wstawkowe (ES)" -> "Do opraw; kulista powierzchnia zewnętrzna (samonastawne w oprawie). " +
        "Mocowane MIMOŚRODOWYM PIERŚCIENIEM zaciskowym, węższy pierścień wewnętrzny niż UC."
    else -> null
}

/** Pełna ścieżka lokalizacji, np. "Regał 3 › Półka 2 › Skrytka A". */
internal fun sciezkaLokalizacji(s: ShelfWithCounts, wszystkie: List<ShelfWithCounts>): String {
    val wgId = wszystkie.associateBy { it.id }
    val czesci = mutableListOf<String>()
    var biezacy: ShelfWithCounts? = s
    var krok = 0
    while (biezacy != null && krok < 10) {          // limit chroni przed zapętleniem
        czesci.add(biezacy.nazwa)
        biezacy = biezacy.parentId?.let { wgId[it] }
        krok++
    }
    return czesci.reversed().joinToString(" › ")
}

private fun shelfLabel(s: ShelfWithCounts): String {
    val lo = s.dMin?.let { fmtInput(it) } ?: "0"
    val hi = s.dMax?.let { fmtInput(it) } ?: "∞"
    return "${s.nazwa} (poziom ${s.poziom}, D: $lo-$hi mm)"
}

private fun fmtInput(v: Double): String = if (v == v.toLong().toDouble()) v.toLong().toString() else v.toString()
