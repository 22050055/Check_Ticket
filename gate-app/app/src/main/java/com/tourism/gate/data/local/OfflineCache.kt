package com.tourism.gate.data.local

import android.content.Context
import androidx.room.*
import com.tourism.gate.data.model.Ticket

// ── Room Database ─────────────────────────────────────────────

/**
 * OfflineCache — Room DB lưu cache vé theo ca trực.
 *
 * Mục đích: khi mạng yếu tại cổng, operator vẫn check-in được
 * bằng cách so sánh ticket_id với danh sách đã cache từ đầu ca.
 *
 * Lưu ý: chỉ cache ticket_id + status, không cache embedding khuôn mặt.
 */
@Database(entities = [Ticket::class, UsedNonce::class], version = 1, exportSchema = false)
abstract class GateDatabase : RoomDatabase() {
    abstract fun ticketDao(): TicketDao
    abstract fun nonceDao(): NonceDao

    companion object {
        @Volatile private var INSTANCE: GateDatabase? = null

        fun getInstance(context: Context): GateDatabase {
            return INSTANCE ?: synchronized(this) {
                Room.databaseBuilder(
                    context.applicationContext,
                    GateDatabase::class.java,
                    "gate_cache.db"
                )
                    .fallbackToDestructiveMigration()
                    .build()
                    .also { INSTANCE = it }
            }
        }
    }
}

// ── Ticket DAO ────────────────────────────────────────────────

@Dao
interface TicketDao {

    /** Lưu hoặc cập nhật vé vào cache */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(ticket: Ticket)

    /** Lưu nhiều vé cùng lúc (đầu ca trực) */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(tickets: List<Ticket>)

    /** Lấy vé theo ticket_id */
    @Query("SELECT * FROM tickets WHERE ticketId = :ticketId")
    suspend fun getById(ticketId: String): Ticket?

    /** Lấy vé theo booking_id */
    @Query("SELECT * FROM tickets WHERE bookingId = :bookingId")
    suspend fun getByBookingId(bookingId: String): Ticket?

    /** Tất cả vé đang active trong cache */
    @Query("SELECT * FROM tickets WHERE status = 'active' ORDER BY cachedAt DESC")
    suspend fun getActiveTickets(): List<Ticket>

    /** Cập nhật status vé sau check-in thành công */
    @Query("UPDATE tickets SET status = 'used' WHERE ticketId = :ticketId")
    suspend fun markUsed(ticketId: String)

    /** Xóa cache cũ (hết ca) */
    @Query("DELETE FROM tickets WHERE cachedAt < :cutoffMs")
    suspend fun deleteOlderThan(cutoffMs: Long)

    /** Xóa toàn bộ cache khi đăng xuất / kết thúc ca */
    @Query("DELETE FROM tickets")
    suspend fun clearAll()

    @Query("SELECT COUNT(*) FROM tickets WHERE status = 'active'")
    suspend fun countActive(): Int
}

// ── Nonce (used QR IDs) ───────────────────────────────────────

/**
 * UsedNonce — lưu JWT ID (jti) đã quét offline.
 * Khi có mạng trở lại → đồng bộ lên server để tránh reuse QR.
 */
@Entity(tableName = "used_nonces")
data class UsedNonce(
    @PrimaryKey
    val jti: String,                  // JWT ID từ QR payload
    val ticketId: String? = null,
    val usedAt: Long = System.currentTimeMillis(),
    val synced: Boolean = false       // đã đồng bộ lên server chưa
)

@Dao
interface NonceDao {

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(nonce: UsedNonce)

    @Query("SELECT EXISTS(SELECT 1 FROM used_nonces WHERE jti = :jti)")
    suspend fun isUsed(jti: String): Boolean

    /** Lấy các nonce chưa đồng bộ để gửi lên server */
    @Query("SELECT * FROM used_nonces WHERE synced = 0")
    suspend fun getUnsynced(): List<UsedNonce>

    @Query("UPDATE used_nonces SET synced = 1 WHERE jti = :jti")
    suspend fun markSynced(jti: String)

    /** Dọn nonce cũ > 24h */
    @Query("DELETE FROM used_nonces WHERE usedAt < :cutoffMs")
    suspend fun deleteOlderThan(cutoffMs: Long)
}
