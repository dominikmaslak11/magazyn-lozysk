package pl.lozyska.offline.data

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.PrimaryKey

@Entity(tableName = "shelves")
data class ShelfEntity(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val nazwa: String,
    val poziom: Int,
    val dMin: Double?,
    val dMax: Double?,
)

@Entity(
    tableName = "bearings",
    foreignKeys = [
        ForeignKey(
            entity = ShelfEntity::class, parentColumns = ["id"], childColumns = ["regalId"],
            onDelete = ForeignKey.SET_NULL,
        )
    ],
)
data class BearingEntity(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val symbol: String,
    val typ: String,
    val d: Double?,
    val dZew: Double?,
    val b: Double?,
    val ilosc: Int,
    val regalId: Int?,
    val recznyPrzydzial: Boolean,
    val zrodlo: String,
    val uwagi: String,
)

data class ShelfWithCounts(
    val id: Int,
    val nazwa: String,
    val poziom: Int,
    val dMin: Double?,
    val dMax: Double?,
    val pozycje: Int,
    val sztuki: Int,
)
