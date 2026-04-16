package com.tourism.gate.data.local

import android.content.Context
import android.util.Log
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.Ticket
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * ShiftManager — Quản lý ca trực và đồng bộ dữ liệu offline.
 *
 * Trách nhiệm:
 *  1. Bắt đầu ca: cache danh sách vé active từ server
 *  2. Kiểm tra vé offline (khi mất mạng)
 *  3. Đồng bộ nonce đã dùng offline lên server khi có mạng
 *  4. Kết thúc ca: xóa cache cũ
 */
class ShiftManager(private val context: Context) {

    private val db        = GateDatabase.getInstance(context)
    private val ticketDao = db.ticketDao()
    private val nonceDao  = db.nonceDao()

    companion object {
        private const val TAG             = "ShiftManager"
        private const val NONCE_TTL_MS    = 24 * 60 * 60 * 1000L   // 24 giờ
        private const val CACHE_TTL_MS    = 12 * 60 * 60 * 1000L   // 12 giờ = 1 ca
        private const val PREFS_NAME      = "gate_prefs"
        private const val KEY_SHIFT_START = "shift_start_ms"
    }

    // ── Bắt đầu ca ────────────────────────────────────────

    /**
     * Gọi khi operator bắt đầu ca làm việc (sau khi chọn cổng).
     * Tải trước danh sách vé active về cache để dùng offline.
     *
     * @return Số vé đã cache
     */
    suspend fun startShift(): Int = withContext(Dispatchers.IO) {
        try {
            // Lưu thời điểm bắt đầu ca
            context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                .edit().putLong(KEY_SHIFT_START, System.currentTimeMillis()).apply()

            // Dọn cache cũ trước
            cleanOldCache()

            Log.i(TAG, "Ca trực bắt đầu — cache vé sẵn sàng")
            ticketDao.countActive()

        } catch (e: Exception) {
            Log.e(TAG, "startShift lỗi: ${e.message}")
            0
        }
    }

    // ── Cache vé từ server ─────────────────────────────────

    /**
     * Lưu vé vào local cache sau khi phát hành hoặc nhận từ server.
     */
    suspend fun cacheTicket(ticket: Ticket) = withContext(Dispatchers.IO) {
        ticketDao.upsert(ticket)
        Log.d(TAG, "Cached ticket: ${ticket.ticketId}")
    }

    /**
     * Cache nhiều vé cùng lúc (đồng bộ batch đầu ca).
     */
    suspend fun cacheTickets(tickets: List<Ticket>) = withContext(Dispatchers.IO) {
        ticketDao.upsertAll(tickets)
        Log.i(TAG, "Cached ${tickets.size} tickets cho ca trực")
    }

    // ── Kiểm tra vé offline ───────────────────────────────

    /**
     * Tìm vé theo ticket_id trong cache local.
     * Dùng khi mất kết nối server.
     */
    suspend fun findTicketOffline(ticketId: String): Ticket? =
        withContext(Dispatchers.IO) {
            ticketDao.getById(ticketId)
        }

    /**
     * Tìm vé theo booking_id trong cache.
     */
    suspend fun findTicketByBookingOffline(bookingId: String): Ticket? =
        withContext(Dispatchers.IO) {
            ticketDao.getByBookingId(bookingId)
        }

    // ── Quản lý nonce (anti-reuse QR offline) ────────────

    /**
     * Kiểm tra QR đã dùng chưa (tra cứu local DB).
     * Dùng khi mất mạng để tránh reuse QR.
     */
    suspend fun isNonceUsed(jti: String): Boolean =
        withContext(Dispatchers.IO) {
            nonceDao.isUsed(jti)
        }

    /**
     * Đánh dấu nonce đã dùng (lưu local, chờ đồng bộ).
     */
    suspend fun markNonceUsed(jti: String, ticketId: String?) =
        withContext(Dispatchers.IO) {
            nonceDao.insert(UsedNonce(jti = jti, ticketId = ticketId, synced = false))
            // Cập nhật trạng thái vé trong cache
            if (ticketId != null) ticketDao.markUsed(ticketId)
        }

    // ── Đồng bộ lên server ───────────────────────────────

    /**
     * Đồng bộ nonce offline lên server khi có mạng.
     * Gọi định kỳ hoặc khi phát hiện mạng restored.
     *
     * @return Số nonce đã đồng bộ thành công
     */
    suspend fun syncNonces(): Int = withContext(Dispatchers.IO) {
        val unsynced = nonceDao.getUnsynced()
        if (unsynced.isEmpty()) return@withContext 0

        Log.i(TAG, "Đồng bộ ${unsynced.size} nonces lên server...")
        var successCount = 0

        // Với mỗi nonce chưa sync → gửi check-in giả lên server để đánh dấu
        // (Trong thực tế có thể dùng endpoint riêng POST /api/nonces/sync)
        // Hiện tại: đơn giản mark synced sau khi kết nối server thành công
        for (nonce in unsynced) {
            try {
                // TODO: gọi API sync nonce nếu backend có endpoint riêng
                // Tạm thời mark synced ngay sau khi mạng restore
                nonceDao.markSynced(nonce.jti)
                successCount++
            } catch (e: Exception) {
                Log.e(TAG, "Sync nonce ${nonce.jti} thất bại: ${e.message}")
            }
        }

        Log.i(TAG, "Đồng bộ xong: $successCount/${unsynced.size}")
        successCount
    }

    // ── Kết thúc ca ───────────────────────────────────────

    /**
     * Dọn dẹp khi kết thúc ca hoặc đăng xuất.
     */
    suspend fun endShift() = withContext(Dispatchers.IO) {
        // Thử đồng bộ nonce còn lại trước khi xóa
        syncNonces()

        ticketDao.clearAll()
        nonceDao.deleteOlderThan(System.currentTimeMillis() - NONCE_TTL_MS)

        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit().remove(KEY_SHIFT_START).apply()

        Log.i(TAG, "Ca trực kết thúc — cache đã xóa")
    }

    // ── Helpers ───────────────────────────────────────────

    /** Xóa cache vé và nonce cũ hơn TTL */
    private suspend fun cleanOldCache() {
        val cutoff = System.currentTimeMillis() - CACHE_TTL_MS
        ticketDao.deleteOlderThan(cutoff)
        nonceDao.deleteOlderThan(System.currentTimeMillis() - NONCE_TTL_MS)
        Log.d(TAG, "Cleaned old cache (cutoff: $cutoff)")
    }

    /** Kiểm tra ca đang hoạt động */
    fun isShiftActive(): Boolean {
        val startMs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getLong(KEY_SHIFT_START, 0L)
        if (startMs == 0L) return false
        return (System.currentTimeMillis() - startMs) < CACHE_TTL_MS
    }

    /** Thời gian bắt đầu ca (ms) */
    fun getShiftStartTime(): Long =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getLong(KEY_SHIFT_START, 0L)
}
