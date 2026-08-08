package pl.lozyska.offline.data

import com.google.gson.GsonBuilder
import com.google.gson.annotations.SerializedName
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Format identyczny z eksportem JSON wersji desktopowej/webowej (server.py -> /api/export/json),
 * żeby pliki dało się swobodnie przenosić między komputerem a telefonem w obie strony.
 */

data class ShelfDto(
    val id: Int, val nazwa: String, val poziom: Int,
    val d_min: Double?, val d_max: Double?,
)

data class BearingDto(
    val id: Int, val symbol: String, val typ: String,
    val d: Double?, @SerializedName("D") val dZew: Double?, val B: Double?,
    val ilosc: Int, val regal_id: Int?, val reczny_przydzial: Boolean,
    val zrodlo: String, val uwagi: String?,
)

data class ExportDto(
    val wersja: Int,
    val eksport_z_dnia: String,
    val regaly: List<ShelfDto>,
    val lozyska: List<BearingDto>,
)

object JsonSync {
    private val gson = GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create()

    fun toJson(shelves: List<ShelfEntity>, bearings: List<BearingEntity>): String {
        val dto = ExportDto(
            wersja = 1,
            eksport_z_dnia = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault()).format(Date()),
            regaly = shelves.map { ShelfDto(it.id, it.nazwa, it.poziom, it.dMin, it.dMax) },
            lozyska = bearings.map {
                BearingDto(it.id, it.symbol, it.typ, it.d, it.dZew, it.b, it.ilosc, it.regalId,
                    it.recznyPrzydzial, it.zrodlo, it.uwagi)
            },
        )
        return gson.toJson(dto)
    }

    /** Zwraca encje z ID-kami TAKIMI JAK W PLIKU (do remapowania przez Repository przy imporcie). */
    fun fromJson(json: String): Pair<List<ShelfEntity>, List<BearingEntity>> {
        val dto = gson.fromJson(json, ExportDto::class.java)
        val shelves = dto.regaly.map { ShelfEntity(it.id, it.nazwa, it.poziom, it.d_min, it.d_max) }
        val bearings = dto.lozyska.map {
            BearingEntity(it.id, it.symbol, it.typ, it.d, it.dZew, it.B, it.ilosc, it.regal_id,
                it.reczny_przydzial, it.zrodlo, it.uwagi ?: "")
        }
        return shelves to bearings
    }
}
