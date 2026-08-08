package pl.lozyska.klient

import com.google.gson.annotations.SerializedName

// Uwaga: pola JSON z serwera to "d" i "D" (średnica wewnętrzna/zewnętrzna), ale w Kotlinie/JVM
// właściwości "d" i "D" generują identyczny getter (getD()) i się nie skompilują - stąd
// wewnętrzna nazwa "dZew" z adnotacją @SerializedName("D") do mapowania z/do JSON-a.

data class Bearing(
    val id: Int,
    val symbol: String,
    val typ: String,
    val d: Double?,
    @SerializedName("D") val dZew: Double?,
    val B: Double?,
    val ilosc: Int,
    val regal_id: Int?,
    val regal_nazwa: String?,
    val reczny_przydzial: Boolean,
    val zrodlo: String,
    val uwagi: String?,
)

data class BearingPayload(
    val symbol: String,
    val typ: String,
    val d: Double?,
    @SerializedName("D") val dZew: Double?,
    val B: Double?,
    val ilosc: Int,
    val zrodlo: String,
    val uwagi: String,
    val regal_id: Int?,
    val reczny_przydzial: Boolean,
)

data class Shelf(
    val id: Int,
    val nazwa: String,
    val poziom: Int,
    val d_min: Double?,
    val d_max: Double?,
    val pozycje: Int,
    val sztuki: Int,
)

data class ShelfPayload(
    val nazwa: String,
    val poziom: Int,
    val d_min: Double?,
    val d_max: Double?,
)

data class LookupSymbolResult(
    val symbol: String?,
    val d: Double?,
    @SerializedName("D") val dZew: Double?,
    val B: Double?,
    val source: String,
    val typ: String?,
    val note: String?,
)

data class DimensionCandidate(
    val symbol: String,
    val d: Double?,
    @SerializedName("D") val dZew: Double?,
    val B: Double?,
    val typ: String?,
    val online: Boolean? = null,
)

data class ReassignResult(val changed: Int)
