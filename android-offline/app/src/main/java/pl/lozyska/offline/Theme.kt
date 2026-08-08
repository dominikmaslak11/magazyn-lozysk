package pl.lozyska.offline

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val AccentGreen = Color(0xFF2E7D5A)
private val AccentGreenLight = Color(0xFF4CC794)

private val LightColors = lightColorScheme(
    primary = AccentGreen,
    secondary = AccentGreen,
    background = Color(0xFFF2F4F7),
    surface = Color(0xFFFFFFFF),
)

private val DarkColors = darkColorScheme(
    primary = AccentGreenLight,
    secondary = AccentGreenLight,
    background = Color(0xFF10151B),
    surface = Color(0xFF1A222B),
)

@Composable
fun LozyskaOfflineTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) DarkColors else LightColors
    MaterialTheme(colorScheme = colors, content = content)
}
