package pl.lozyska.offline.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

// poziom 1 = regał najniższy (duże łożyska), poziom 9 = najwyższy (małe łożyska) - jak w wersji desktopowej.
val DEFAULT_SHELVES = listOf(
    ShelfEntity(nazwa = "Regał 1 (dół)", poziom = 1, dMin = 200.0, dMax = null),
    ShelfEntity(nazwa = "Regał 2", poziom = 2, dMin = 150.0, dMax = 200.0),
    ShelfEntity(nazwa = "Regał 3", poziom = 3, dMin = 115.0, dMax = 150.0),
    ShelfEntity(nazwa = "Regał 4", poziom = 4, dMin = 90.0, dMax = 115.0),
    ShelfEntity(nazwa = "Regał 5", poziom = 5, dMin = 72.0, dMax = 90.0),
    ShelfEntity(nazwa = "Regał 6", poziom = 6, dMin = 55.0, dMax = 72.0),
    ShelfEntity(nazwa = "Regał 7", poziom = 7, dMin = 42.0, dMax = 55.0),
    ShelfEntity(nazwa = "Regał 8", poziom = 8, dMin = 30.0, dMax = 42.0),
    ShelfEntity(nazwa = "Regał 9 (góra)", poziom = 9, dMin = 0.0, dMax = 30.0),
)

@Database(entities = [BearingEntity::class, ShelfEntity::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun bearingDao(): BearingDao
    abstract fun shelfDao(): ShelfDao

    companion object {
        @Volatile private var INSTANCE: AppDatabase? = null

        fun get(context: Context): AppDatabase =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(context.applicationContext, AppDatabase::class.java, "lozyska_offline.db")
                    .addCallback(object : Callback() {
                        override fun onCreate(db: androidx.sqlite.db.SupportSQLiteDatabase) {
                            super.onCreate(db)
                            CoroutineScope(Dispatchers.IO).launch {
                                INSTANCE?.shelfDao()?.insertAll(DEFAULT_SHELVES)
                            }
                        }
                    })
                    .build()
                    .also { INSTANCE = it }
            }
    }
}
