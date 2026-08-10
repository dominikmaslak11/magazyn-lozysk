package pl.lozyska.offline.data

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

// ID to UUID (nie liczba) - dzięki temu telefon może tworzyć nowe rekordy OFFLINE
// bez ryzyka kolizji identyfikatorów przy późniejszej synchronizacji z serwerem
// (patrz SyncEngine.kt). updatedAt to WŁASNY zegar telefonu, używany WYŁĄCZNIE do
// ustalenia co wysłać przy najbliższym sync-u (nigdy nie jest porównywany z zegarem
// serwera ani innych telefonów - to rozstrzyga serwer, patrz komentarz w database.py).
// deletedAt to "miękkie" kasowanie (nagrobek), żeby kasowanie poprawnie propagowało
// się do innych urządzeń przy synchronizacji.

@Entity(tableName = "shelves")
data class ShelfEntity(
    @PrimaryKey val id: String,
    val nazwa: String,
    val poziom: Int,
    val dMin: Double?,
    val dMax: Double?,
    val updatedAt: Long = System.currentTimeMillis(),
    val deletedAt: Long? = null,
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
    @PrimaryKey val id: String,
    val symbol: String,
    val typ: String,
    val d: Double?,
    val dZew: Double?,
    val b: Double?,
    val ilosc: Int,
    val regalId: String?,
    val recznyPrzydzial: Boolean,
    val zrodlo: String,
    val uwagi: String,
    val updatedAt: Long = System.currentTimeMillis(),
    val deletedAt: Long? = null,
)

/**
 * Skojarzenie kodu kreskowego z opakowania (zwykle EAN-13, czyli numer handlowy
 * producenta) z symbolem łożyska - patrz BarcodeAlias w database.py na serwerze.
 *
 * Kod EAN nie zawiera oznaczenia łożyska, więc sam skan nic nie mówi o zawartości
 * pudełka. Zamiast płatnych baz GTIN appka pyta użytkownika RAZ i zapamiętuje
 * odpowiedź tutaj; skojarzenie synchronizuje się przez serwer na pozostałe telefony.
 */
@Entity(tableName = "barcode_aliases", indices = [Index(value = ["kod"])])
data class BarcodeAliasEntity(
    @PrimaryKey val id: String,
    val kod: String,
    val symbol: String,
    val updatedAt: Long = System.currentTimeMillis(),
    val deletedAt: Long? = null,
)

data class ShelfWithCounts(
    val id: String,
    val nazwa: String,
    val poziom: Int,
    val dMin: Double?,
    val dMax: Double?,
    val pozycje: Int,
    val sztuki: Int,
)
