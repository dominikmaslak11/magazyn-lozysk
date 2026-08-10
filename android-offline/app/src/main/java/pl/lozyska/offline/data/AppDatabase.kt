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

@Database(
    entities = [BearingEntity::class, ShelfEntity::class, BarcodeAliasEntity::class],
    version = 3,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun bearingDao(): BearingDao
    abstract fun shelfDao(): ShelfDao
    abstract fun barcodeAliasDao(): BarcodeAliasDao

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
                    .addMigrations(MIGRATION_2_3)
                    .build()
                    .also { INSTANCE = it }
            }
    }
}
