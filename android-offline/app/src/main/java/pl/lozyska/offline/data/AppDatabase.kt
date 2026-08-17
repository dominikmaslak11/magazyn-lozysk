package pl.lozyska.offline.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

/**
 * v2 -> v3: dokładamy tabelę aliasów kodów kreskowych (kod z opakowania -> symbol łożyska).
 *
 * Celowo PRAWDZIWA migracja, a nie fallbackToDestructiveMigration: skasowanie lokalnej bazy
 * zabrałoby ze sobą zmiany zrobione offline, których telefon nie zdążył jeszcze wypchnąć na
 * serwer. Nowa tabela jest pusta i niezależna od pozostałych, więc migracja jest bezpieczna.
 */
private val MIGRATION_2_3 = object : Migration(2, 3) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS `barcode_aliases` (" +
                "`id` TEXT NOT NULL, `kod` TEXT NOT NULL, `symbol` TEXT NOT NULL, " +
                "`updatedAt` INTEGER NOT NULL, `deletedAt` INTEGER, PRIMARY KEY(`id`))"
        )
        db.execSQL("CREATE INDEX IF NOT EXISTS `index_barcode_aliases_kod` ON `barcode_aliases` (`kod`)")
    }
}

/**
 * v3 -> v4: dziennik ruchów magazynowych (zmiany ilości jako różnice, nie wartości bezwzględne).
 * Znowu PRAWDZIWA migracja, nie czyszczenie bazy - telefon może mieć zmiany zrobione offline,
 * których jeszcze nie wypchnął na serwer.
 */
private val MIGRATION_3_4 = object : Migration(3, 4) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS `stock_moves` (" +
                "`id` TEXT NOT NULL, `bearingId` TEXT NOT NULL, `delta` INTEGER NOT NULL, " +
                "`createdAt` INTEGER NOT NULL, PRIMARY KEY(`id`))"
        )
        db.execSQL("CREATE INDEX IF NOT EXISTS `index_stock_moves_bearingId` ON `stock_moves` (`bearingId`)")
    }
}

/**
 * v4 -> v5: hierarchia lokalizacji. Dokładamy kolumny do istniejącej tabeli shelves,
 * więc dotychczasowe regały stają się korzeniami drzewa i nic nie trzeba przenosić.
 */
private val MIGRATION_4_5 = object : Migration(4, 5) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("ALTER TABLE `shelves` ADD COLUMN `parentId` TEXT")
        db.execSQL("ALTER TABLE `shelves` ADD COLUMN `poziomTyp` TEXT NOT NULL DEFAULT 'regał'")
        db.execSQL("CREATE INDEX IF NOT EXISTS `index_shelves_parentId` ON `shelves` (`parentId`)")
    }
}

/** v5 -> v6: lokalizacja może być dedykowana konkretnym typom łożysk. */
private val MIGRATION_5_6 = object : Migration(5, 6) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("ALTER TABLE `shelves` ADD COLUMN `typy` TEXT NOT NULL DEFAULT ''")
    }
}

@Database(
    entities = [BearingEntity::class, ShelfEntity::class, BarcodeAliasEntity::class, StockMoveEntity::class],
    version = 6,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun bearingDao(): BearingDao
    abstract fun shelfDao(): ShelfDao
    abstract fun barcodeAliasDao(): BarcodeAliasDao
    abstract fun stockMoveDao(): StockMoveDao

    companion object {
        @Volatile private var INSTANCE: AppDatabase? = null

        fun get(context: Context): AppDatabase =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(context.applicationContext, AppDatabase::class.java, "lozyska_offline.db")
                    // v1 -> v2: zmiana ID z liczby na UUID (obsługa synchronizacji). Lokalne dane
                    // sprzed synchronizacji nie mają odpowiednika na serwerze, więc przy tej JEDNEJ
                    // aktualizacji celowo czyścimy lokalną bazę - i tak zostanie odtworzona z
                    // pierwszej synchronizacji z serwerem.
                    .fallbackToDestructiveMigration()
                    // v2 -> v3 ma już prawdziwą migrację (nie chcemy tracić zmian zrobionych
                    // offline), więc jest zarejestrowana PO fallbacku - Room użyje jej zamiast
                    // czyszczenia bazy.
                    .addMigrations(MIGRATION_2_3, MIGRATION_3_4, MIGRATION_4_5, MIGRATION_5_6)
                    .build()
                    .also { INSTANCE = it }
            }
    }
}
