package pl.lozyska.offline.data

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface BearingDao {
    @Query("SELECT * FROM bearings WHERE symbol LIKE '%' || :search || '%' ORDER BY symbol")
    fun observeAll(search: String = ""): Flow<List<BearingEntity>>

    @Query("SELECT * FROM bearings WHERE id = :id")
    suspend fun getById(id: Int): BearingEntity?

    @Query("SELECT * FROM bearings WHERE recznyPrzydzial = 0")
    suspend fun getAutoAssigned(): List<BearingEntity>

    @Insert
    suspend fun insert(bearing: BearingEntity): Long

    @Update
    suspend fun update(bearing: BearingEntity)

    @Query("UPDATE bearings SET regalId = :regalId WHERE id = :id")
    suspend fun updateRegal(id: Int, regalId: Int?)

    @Delete
    suspend fun delete(bearing: BearingEntity)

    @Query("DELETE FROM bearings")
    suspend fun deleteAll()

    @Query("SELECT * FROM bearings ORDER BY symbol")
    suspend fun getAllOnce(): List<BearingEntity>
}

@Dao
interface ShelfDao {
    @Query("""
        SELECT s.id, s.nazwa, s.poziom, s.dMin, s.dMax,
               COUNT(b.id) AS pozycje, COALESCE(SUM(b.ilosc), 0) AS sztuki
        FROM shelves s LEFT JOIN bearings b ON b.regalId = s.id
        GROUP BY s.id ORDER BY s.poziom DESC
    """)
    fun observeAllWithCounts(): Flow<List<ShelfWithCounts>>

    @Query("SELECT * FROM shelves ORDER BY poziom DESC")
    suspend fun getAllOnce(): List<ShelfEntity>

    @Insert
    suspend fun insert(shelf: ShelfEntity): Long

    @Insert
    suspend fun insertAll(shelves: List<ShelfEntity>)

    @Update
    suspend fun update(shelf: ShelfEntity)

    @Query("DELETE FROM shelves")
    suspend fun deleteAll()

    @Query("SELECT COUNT(*) FROM shelves")
    suspend fun count(): Int
}
