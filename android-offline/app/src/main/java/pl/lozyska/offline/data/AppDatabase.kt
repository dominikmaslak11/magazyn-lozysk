package pl.lozyska.offline.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(entities = [BearingEntity::class, ShelfEntity::class], version = 2, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun bearingDao(): BearingDao
    abstract fun shelfDao(): ShelfDao

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
                    .build()
                    .also { INSTANCE = it }
            }
    }
}
