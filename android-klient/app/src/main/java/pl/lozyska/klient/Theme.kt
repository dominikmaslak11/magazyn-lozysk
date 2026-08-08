package pl.lozyska.klient

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val AccentBlue = Color(0xFF1E6FA8)
private val AccentBlueLight = Color(0xFF3F9BDA)

private val LightColors = lightColorScheme(
    primary = AccentBlue,
    secondary = AccentBlue,
    background = Color(0xFFF2F4F7),
    surface = Color(0xFFFFFFFF),
)

private val DarkColors = darkColorScheme(
    primary = AccentBlueLight,
    secondary = AccentBlueLight,
    background = Color(0xFF10151B),
    surface = Color(0xFF1A222B),
)

@Composable
fun LozyskaTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) DarkColors else LightColors
    MaterialTheme(colorScheme = colors, content = content)
}
