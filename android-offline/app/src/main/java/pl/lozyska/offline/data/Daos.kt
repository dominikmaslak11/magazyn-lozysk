package pl.lozyska.offline.data

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface BearingDao {
    @Query("SELECT * FROM bearings WHERE deletedAt IS NULL AND symbol LIKE '%' || :search || '%' ORDER BY symbol")
    fun observeAll(search: String = ""): Flow<List<BearingEntity>>

    @Query("SELECT * FROM bearings WHERE id = :id AND deletedAt IS NULL")
    suspend fun getById(id: String): BearingEntity?

    @Query("SELECT * FROM bearings WHERE recznyPrzydzial = 0 AND deletedAt IS NULL")
    suspend fun getAutoAssigned(): List<BearingEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(bearing: BearingEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(bearings: List<BearingEntity>)

    @Update
    suspend fun update(bearing: BearingEntity)

    @Query("UPDATE bearings SET regalId = :regalId, updatedAt = :updatedAt WHERE id = :id")
    suspend fun updateRegal(id: String, regalId: String?, updatedAt: Long)

    /** Miękkie kasowanie - patrz komentarz przy BearingEntity.deletedAt. */
    @Query("UPDATE bearings SET deletedAt = :deletedAt, updatedAt = :deletedAt WHERE id = :id")
    suspend fun softDelete(id: String, deletedAt: Long)

    @Query("DELETE FROM bearings")
    suspend fun deleteAllHard()

    @Query("SELECT * FROM bearings WHERE deletedAt IS NULL ORDER BY symbol")
    suspend fun getAllOnce(): List<BearingEntity>

    /** Rekordy zmienione lokalnie od ostatniej udanej synchronizacji - do wypchnięcia na serwer. */
    @Query("SELECT * FROM bearings WHERE updatedAt > :since")
    suspend fun getChangedSince(since: Long): List<BearingEntity>
}

@Dao
interface ShelfDao {
    @Query("""
        SELECT s.id, s.nazwa, s.poziom, s.dMin, s.dMax,
               COUNT(b.id) AS pozycje, COALESCE(SUM(b.ilosc), 0) AS sztuki
        FROM shelves s LEFT JOIN bearings b ON b.regalId = s.id AND b.deletedAt IS NULL
        WHERE s.deletedAt IS NULL
        GROUP BY s.id ORDER BY s.poziom DESC
    """)
    fun observeAllWithCounts(): Flow<List<ShelfWithCounts>>

    @Query("SELECT * FROM shelves WHERE deletedAt IS NULL ORDER BY poziom DESC")
    suspend fun getAllOnce(): List<ShelfEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(shelf: ShelfEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(shelves: List<ShelfEntity>)

    @Update
    suspend fun update(shelf: ShelfEntity)

    @Query("DELETE FROM shelves")
    suspend fun deleteAllHard()

    @Query("SELECT COUNT(*) FROM shelves")
    suspend fun count(): Int

    @Query("SELECT * FROM shelves WHERE updatedAt > :since")
    suspend fun getChangedSince(since: Long): List<ShelfEntity>
}
