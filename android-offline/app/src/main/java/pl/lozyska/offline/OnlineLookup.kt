package pl.lozyska.offline

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit
import java.util.regex.Pattern

/**
 * Wyszukiwanie w internecie jako uzupełnienie wbudowanego katalogu offline (best-effort,
 * dokładnie ten sam mechanizm co w wersji desktopowej/webowej - proste rozpoznawanie wzorców
 * w wynikach wyszukiwarki). Wyniki stąd są zawsze oznaczane w UI jako orientacyjne.
 */
object OnlineLookup {
    private const val USER_AGENT = "Mozilla/5.0 (Linux; Android) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"

    private val client = OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS)
        .readTimeout(8, TimeUnit.SECONDS)
        .build()

    private val dimsPattern = Pattern.compile("(\\d{1,3}(?:\\.\\d+)?)\\s*[x×]\\s*(\\d{1,3}(?:\\.\\d+)?)\\s*[x×]\\s*(\\d{1,3}(?:\\.\\d+)?)")

    suspend fun lookupDimensionsBySymbol(symbol: String): Triple<Double, Double, Double>? = withContext(Dispatchers.IO) {
        val text = search("$symbol bearing dimensions bore mm outer diameter width") ?: return@withContext null
        val m = dimsPattern.matcher(text)
        if (m.find()) {
            val d = m.group(1)!!.toDouble()
            val dOut = m.group(2)!!.toDouble()
            val b = m.group(3)!!.toDouble()
            if (d < dOut) return@withContext Triple(d, dOut, b)
        }
        null
    }

    suspend fun lookupSymbolByDimensions(d: Double?, dOut: Double?, b: Double?): String? = withContext(Dispatchers.IO) {
        if (d == null && dOut == null && b == null) return@withContext null
        val parts = listOfNotNull(d?.toInt(), dOut?.toInt(), b?.toInt()).joinToString("x")
        val text = search("bearing $parts mm symbol number") ?: return@withContext null
        for (pattern in listOf("\\b1[0-9]{4}\\b", "\\b6[0-9]{3}\\b", "\\b6[0-9]{4}\\b")) {
            val m = Pattern.compile(pattern).matcher(text)
            if (m.find()) return@withContext m.group(0)
        }
        null
    }

    private fun search(query: String): String? {
        return try {
            val url = "https://html.duckduckgo.com/html/?q=" + java.net.URLEncoder.encode(query, "UTF-8")
            val request = Request.Builder().url(url).header("User-Agent", USER_AGENT).build()
            client.newCall(request).execute().use { resp ->
                if (resp.isSuccessful) resp.body?.string() else null
            }
        } catch (e: Exception) {
            null
        }
    }
}
