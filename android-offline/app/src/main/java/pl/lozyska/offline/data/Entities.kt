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

/**
 * Węzeł drzewa lokalizacji: regał, półka, szuflada albo skrytka.
 *
 * Hierarchia jest KONFIGUROWALNA i niesymetryczna - jeden regał może mieć półki
 * z szufladami, a inny od razu skrytki albo nic. Dlatego to jedna tabela z
 * `parentId`, a nie osobna na każdy poziom (patrz Shelf w database.py).
 * Łożysko wskazuje na DOWOLNY węzeł, więc można je położyć wprost na regale.
 */
@Entity(tableName = "shelves", indices = [Index(value = ["parentId"])])
data class ShelfEntity(
    @PrimaryKey val id: String,
    val nazwa: String,
    val poziom: Int,
    val dMin: Double?,
    val dMax: Double?,
    val updatedAt: Long = System.currentTimeMillis(),
    val deletedAt: Long? = null,
    val parentId: String? = null,
    val poziomTyp: String = "regał",
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

/**
 * Ruch magazynowy: ile sztuk przybyło (+) albo ubyło (-) - patrz stock_moves w database.py.
 *
 * Po co, skoro ilość jest już w BearingEntity: ilość to LICZNIK, a licznika nie wolno
 * synchronizować regułą "kto ostatni, ten lepszy". Gdy jedna osoba weźmie offline 2 sztuki,
 * a druga 1, nadpisywanie wartością bezwzględną gubi jedną ze zmian bez śladu. Dlatego
 * telefon wysyła RÓŻNICE, a serwer je sumuje.
 *
 * `id` jest nadawane tutaj i służy serwerowi do DEDUPLIKACJI: jeśli odpowiedź zginie po
 * drodze i ten sam ruch pojedzie ponownie, drugi raz nie zostanie policzony.
 *
 * Rekordy kasujemy dopiero po potwierdzonej synchronizacji (patrz SyncEngine).
 */
@Entity(tableName = "stock_moves", indices = [Index(value = ["bearingId"])])
data class StockMoveEntity(
    @PrimaryKey val id: String,
    val bearingId: String,
    val delta: Int,
    val createdAt: Long = System.currentTimeMillis(),
)

data class ShelfWithCounts(
    val id: String,
    val nazwa: String,
    val poziom: Int,
    val dMin: Double?,
    val dMax: Double?,
    val pozycje: Int,
    val sztuki: Int,
    val parentId: String? = null,
    val poziomTyp: String = "regał",
)
