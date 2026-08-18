package pl.lozyska.offline

import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import pl.lozyska.offline.data.PowiadomienieEntity

/**
 * Kolory podpowiedzi. Trzy poziomy, bo znaczą co innego i wymagają innej reakcji:
 * czerwony = coś jest nie tak TERAZ, żółty = potrzebna interwencja, szary = do wiadomości.
 *
 * Żółty definiujemy jawnie zamiast brać z motywu: w Material 3 nie ma roli "ostrzeżenie",
 * a podpięcie pod tertiary dałoby kolor zależny od tapety telefonu (dynamic color) -
 * czyli czasem zielony albo różowy tam, gdzie użytkownik oczekuje żółtego.
 */
data class KolorWagi(val tlo: Color, val tekst: Color)

@Composable
fun kolorWagi(waga: String): KolorWagi {
    val ciemny = isSystemInDarkTheme()
    return when (waga) {
        "krytyczna" -> KolorWagi(MaterialTheme.colorScheme.errorContainer, MaterialTheme.colorScheme.onErrorContainer)
        "ostrzezenie" ->
            if (ciemny) KolorWagi(Color(0xFF4A3A00), Color(0xFFFFE082))
            else KolorWagi(Color(0xFFFFF0C2), Color(0xFF4A3A00))
        else -> KolorWagi(MaterialTheme.colorScheme.surfaceVariant, MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

/** "przed chwilą", "12 min temu", "3 godz. temu", "2 dni temu". */
fun wiekSynchronizacji(pobranoO: Long, teraz: Long = System.currentTimeMillis()): String {
    val minuty = (teraz - pobranoO) / 60_000
    return when {
        minuty < 2 -> "przed chwilą"
        minuty < 60 -> "$minuty min temu"
        minuty < 48 * 60 -> "${minuty / 60} godz. temu"
        else -> "${minuty / (60 * 24)} dni temu"
    }
}

/**
 * Pasek podpowiedzi nad listą łożysk.
 *
 * Podpowiedzi liczy SERWER (patrz powiadomienia() w database.py), telefon tylko je
 * wyświetla. Dlatego jawnie pokazujemy, z kiedy pochodzą - bez tego użytkownik offline
 * mógłby uznać nieaktualną listę za bieżący stan magazynu.
 *
 * Domyślnie zwinięty do jednej linijki: przy porządkowaniu magazynu od zera podpowiedzi
 * są dziesiątki i rozwinięta lista zasłaniałaby to, po co się tu weszło - czyli łożyska.
 */
@Composable
fun PowiadomieniaBanner(powiadomienia: List<PowiadomienieEntity>, modifier: Modifier = Modifier) {
    if (powiadomienia.isEmpty()) return
    var rozwiniete by remember { mutableStateOf(false) }

    val krytyczne = powiadomienia.count { it.waga == "krytyczna" }
    val ostrzezenia = powiadomienia.count { it.waga == "ostrzezenie" }
    val naglowekWaga = if (krytyczne > 0) "krytyczna" else if (ostrzezenia > 0) "ostrzezenie" else "informacja"
    val kolor = kolorWagi(naglowekWaga)

    val podsumowanie = listOfNotNull(
        krytyczne.takeIf { it > 0 }?.let { "$it pilne" },
        ostrzezenia.takeIf { it > 0 }?.let { "$it do przełożenia" },
        (powiadomienia.size - krytyczne - ostrzezenia).takeIf { it > 0 }?.let { "$it drobnych" },
    ).joinToString(" · ")

    Surface(color = kolor.tlo, shape = MaterialTheme.shapes.medium, modifier = modifier.fillMaxWidth()) {
        Column(Modifier.clickable { rozwiniete = !rozwiniete }.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Podpowiedzi: $podsumowanie", color = kolor.tekst,
                        fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.bodyMedium)
                    Text("dane z serwera, ${wiekSynchronizacji(powiadomienia.first().pobranoO)}",
                        color = kolor.tekst, style = MaterialTheme.typography.bodySmall)
                }
                Icon(
                    if (rozwiniete) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                    contentDescription = if (rozwiniete) "Zwiń podpowiedzi" else "Rozwiń podpowiedzi",
                    tint = kolor.tekst,
                )
            }
            if (rozwiniete) {
                Spacer(Modifier.height(8.dp))
                // Wysokość MUSI być ograniczona: rozwinięty pasek bez limitu wypychał listę
                // łożysk poza ekran, czyli zasłaniał to, po co się tu weszło.
                // Własne przewijanie, a nie LazyColumn - pasek jest sąsiadem listy łożysk,
                // nie jej elementem, a podpowiedzi jest z natury kilkanaście.
                Column(Modifier.heightIn(max = 260.dp).verticalScroll(rememberScrollState())) {
                powiadomienia.forEach { p ->
                    val k = kolorWagi(p.waga)
                    Surface(color = k.tlo, shape = MaterialTheme.shapes.small,
                        modifier = Modifier.fillMaxWidth().padding(bottom = 6.dp)) {
                        Column(Modifier.padding(10.dp)) {
                            Text(p.tytul, color = k.tekst, fontWeight = FontWeight.SemiBold,
                                style = MaterialTheme.typography.labelLarge)
                            Text(p.komunikat, color = k.tekst, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
                }
            }
        }
    }
}
