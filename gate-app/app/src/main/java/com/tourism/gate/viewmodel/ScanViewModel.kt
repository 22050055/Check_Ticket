package com.tourism.gate.viewmodel

import android.app.Application
import androidx.lifecycle.*
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.local.ShiftManager
import com.tourism.gate.data.model.CheckinRequest
import com.tourism.gate.data.model.CheckinResponse
import kotlinx.coroutines.launch

/**
 * ScanViewModel — Logic quét QR và gửi check-in lên server.
 *
 * State machine:
 *   IDLE → PROCESSING → SUCCESS / FAIL → IDLE (tự reset sau 4s)
 */
class ScanViewModel(app: Application) : AndroidViewModel(app) {

    private val shiftManager = ShiftManager(app)

    // ── UI State ──────────────────────────────────────────

    sealed class ScanState {
        object Idle : ScanState()
        object Processing : ScanState()
        data class Success(val response: CheckinResponse) : ScanState()
        data class Failure(val message: String, val ticketId: String? = null) : ScanState()
        data class NeedFaceVerify(val qrToken: String, val ticketId: String?, val ticketType: String?) : ScanState()
    }

    private val _state = MutableLiveData<ScanState>(ScanState.Idle)
    val state: LiveData<ScanState> = _state

    private val _isOffline = MutableLiveData(false)
    val isOffline: LiveData<Boolean> = _isOffline

    // ── QR Check-in ───────────────────────────────────────

    /**
     * Xử lý QR token sau khi ML Kit scan được.
     * Tự phát hiện kênh: QR hoặc QR_FACE tùy vé có đăng ký face không.
     */
    fun processQrToken(
        qrToken:   String,
        gateId:    String,
        direction: String,
        withFace:  Boolean = false  // operator bật chế độ verify face
    ) {
        if (_state.value is ScanState.Processing) return  // tránh double-submit
        _state.value = ScanState.Processing

        viewModelScope.launch {
            try {
                val api = ApiClient.create(getApplication())
                val req = CheckinRequest(
                    gate_id   = gateId,
                    direction = direction,
                    channel   = "QR",
                    qr_token  = qrToken
                )
                val resp = api.checkin(req)

                // Nếu vé có face + operator chọn withFace → yêu cầu chụp mặt
                if (resp.success && withFace) {
                    _state.value = ScanState.NeedFaceVerify(
                        qrToken    = qrToken,
                        ticketId   = resp.ticket_id,
                        ticketType = resp.ticket_type
                    )
                } else if (resp.success) {
                    // Cache cập nhật status vé
                    resp.ticket_id?.let { shiftManager.markNonceUsed(extractJti(qrToken), it) }
                    _state.value = ScanState.Success(resp)
                } else {
                    _state.value = ScanState.Failure(resp.message, resp.ticket_id)
                }

            } catch (e: Exception) {
                // Mất mạng → thử offline check
                val offlineResult = checkOffline(qrToken, gateId, direction)
                if (offlineResult != null) {
                    _isOffline.value = true
                    _state.value = ScanState.Success(offlineResult)
                } else {
                    _state.value = ScanState.Failure("Lỗi kết nối: ${e.message}")
                }
            }
        }
    }

    // ── Offline fallback ──────────────────────────────────

    /**
     * Kiểm tra QR offline khi mất mạng:
     * 1. Giải mã JWT lấy jti + ticket_id (không verify chữ ký — chấp nhận rủi ro thấp)
     * 2. Kiểm tra nonce chưa dùng trong local DB
     * 3. Tìm vé trong cache, kiểm tra status + thời hạn
     */
    private suspend fun checkOffline(
        qrToken: String, gateId: String, direction: String
    ): CheckinResponse? {
        return try {
            val jti      = extractJti(qrToken)
            val ticketId = extractTicketId(qrToken)

            if (jti.isEmpty() || ticketId.isEmpty()) return null
            if (shiftManager.isNonceUsed(jti)) return null  // đã dùng

            val ticket = shiftManager.findTicketOffline(ticketId) ?: return null
            if (!ticket.isActive) return null

            // Đánh dấu đã dùng offline
            shiftManager.markNonceUsed(jti, ticketId)

            CheckinResponse(
                success     = true,
                direction   = direction,
                channel     = "QR",
                ticket_id   = ticketId,
                ticket_type = ticket.ticketType,
                message     = "✅ QR hợp lệ (offline mode)"
            )
        } catch (e: Exception) {
            null
        }
    }

    // ── Helpers: decode JWT payload (không verify sig) ────

    private fun extractJti(jwt: String): String = decodeJwtField(jwt, "jti")
    private fun extractTicketId(jwt: String): String = decodeJwtField(jwt, "sub")

    private fun decodeJwtField(jwt: String, field: String): String {
        return try {
            val payload = jwt.split(".").getOrElse(1) { return "" }
            val decoded = android.util.Base64.decode(
                payload.padEnd((payload.length + 3) / 4 * 4, '='),
                android.util.Base64.URL_SAFE
            ).toString(Charsets.UTF_8)
            val regex = """"$field"\s*:\s*"([^"]+)"""".toRegex()
            regex.find(decoded)?.groupValues?.getOrElse(1) { "" } ?: ""
        } catch (e: Exception) { "" }
    }

    // ── Reset ─────────────────────────────────────────────

    fun resetState() {
        _state.value = ScanState.Idle
        _isOffline.value = false
    }
}
