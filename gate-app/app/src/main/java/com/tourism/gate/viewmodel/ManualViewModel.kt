package com.tourism.gate.viewmodel

import android.app.Application
import androidx.lifecycle.*
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.local.ShiftManager
import com.tourism.gate.data.model.CheckinRequest
import com.tourism.gate.data.model.CheckinResponse
import kotlinx.coroutines.launch

/**
 * ManualViewModel — Logic tra cứu thủ công (kênh MANUAL, BOOKING, ID).
 *
 * Hỗ trợ 3 loại tìm kiếm:
 *   PHONE    → channel=MANUAL, field=phone
 *   BOOKING  → channel=BOOKING, field=booking_id
 *   TICKET   → channel=MANUAL, field=ticket_id
 */
class ManualViewModel(app: Application) : AndroidViewModel(app) {

    private val shiftManager = ShiftManager(app)

    // ── Search type enum ──────────────────────────────────

    enum class SearchType { PHONE, BOOKING, TICKET }

    // ── UI State ──────────────────────────────────────────

    sealed class ManualState {
        object Idle       : ManualState()
        object Searching  : ManualState()
        data class Found(val response: CheckinResponse)  : ManualState()
        data class NotFound(val query: String)           : ManualState()
        data class Error(val message: String)            : ManualState()
    }

    private val _state = MutableLiveData<ManualState>(ManualState.Idle)
    val state: LiveData<ManualState> = _state

    // Lịch sử tìm kiếm trong ca (để operator không nhập lại)
    private val _searchHistory = MutableLiveData<List<String>>(emptyList())
    val searchHistory: LiveData<List<String>> = _searchHistory

    // ── Search ────────────────────────────────────────────

    /**
     * Tìm kiếm và check-in theo loại.
     *
     * @param query     Giá trị tìm kiếm (SĐT / booking ID / ticket ID)
     * @param type      Loại tìm kiếm
     * @param gateId    ID cổng
     * @param direction IN hoặc OUT
     */
    fun search(
        query:     String,
        type:      SearchType,
        gateId:    String,
        direction: String
    ) {
        val trimmed = query.trim()
        if (trimmed.isEmpty()) return

        _state.value = ManualState.Searching
        addToHistory(trimmed)

        viewModelScope.launch {
            try {
                val req = buildRequest(trimmed, type, gateId, direction)
                val api = ApiClient.create(getApplication())
                val resp = api.checkin(req)

                if (resp.success) {
                    _state.value = ManualState.Found(resp)
                } else {
                    _state.value = ManualState.NotFound(trimmed)
                }

            } catch (e: Exception) {
                // Thử offline nếu mất mạng
                val offlineResp = searchOffline(trimmed, type, gateId, direction)
                if (offlineResp != null) {
                    _state.value = ManualState.Found(offlineResp)
                } else {
                    _state.value = ManualState.Error(
                        if (e.message?.contains("Unable to resolve") == true)
                            "Không kết nối được server"
                        else "Lỗi: ${e.message}"
                    )
                }
            }
        }
    }

    // ── Offline search ────────────────────────────────────

    private suspend fun searchOffline(
        query:     String,
        type:      SearchType,
        gateId:    String,
        direction: String
    ): CheckinResponse? {
        val ticket = when (type) {
            SearchType.TICKET  -> shiftManager.findTicketOffline(query)
            SearchType.BOOKING -> shiftManager.findTicketByBookingOffline(query)
            SearchType.PHONE   -> null  // Không hỗ trợ tìm SĐT offline (cần hash)
        } ?: return null

        if (!ticket.isActive) return null

        return CheckinResponse(
            success     = true,
            direction   = direction,
            channel     = if (type == SearchType.BOOKING) "BOOKING" else "MANUAL",
            ticket_id   = ticket.ticketId,
            ticket_type = ticket.ticketType,
            message     = "${ticket.ticketTypeLabel} hợp lệ (offline mode)"
        )
    }

    // ── Build request ─────────────────────────────────────

    private fun buildRequest(
        query:     String,
        type:      SearchType,
        gateId:    String,
        direction: String
    ): CheckinRequest = when (type) {
        SearchType.PHONE -> CheckinRequest(
            gate_id   = gateId,
            direction = direction,
            channel   = "MANUAL",
            phone     = normalizePhone(query)
        )
        SearchType.BOOKING -> CheckinRequest(
            gate_id    = gateId,
            direction  = direction,
            channel    = "BOOKING",
            booking_id = query.uppercase()
        )
        SearchType.TICKET -> CheckinRequest(
            gate_id   = gateId,
            direction = direction,
            channel   = "MANUAL",
            ticket_id = query
        )
    }

    // ── Helpers ───────────────────────────────────────────

    /** Chuẩn hóa SĐT: chỉ giữ lại số */
    private fun normalizePhone(phone: String): String =
        phone.filter { it.isDigit() }

    private fun addToHistory(query: String) {
        val current = _searchHistory.value?.toMutableList() ?: mutableListOf()
        current.remove(query)         // tránh trùng
        current.add(0, query)         // thêm vào đầu
        _searchHistory.value = current.take(10)  // giữ tối đa 10
    }

    fun resetState() {
        _state.value = ManualState.Idle
    }

    fun clearHistory() {
        _searchHistory.value = emptyList()
    }
}
 