package com.tourism.gate.viewmodel

import android.app.Application
import android.graphics.Bitmap
import android.util.Base64
import androidx.lifecycle.*
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.CheckinRequest
import com.tourism.gate.data.model.CheckinResponse
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream

/**
 * FaceViewModel — Logic xác thực khuôn mặt 1:1 (QR_FACE channel).
 *
 * Flow:
 *   1. Nhận bitmap từ camera (front camera)
 *   2. Encode sang JPEG base64
 *   3. Gửi POST /api/checkin với channel=QR_FACE + probe_image_b64
 *   4. Trả kết quả: match / no match / fallback
 */
class FaceViewModel(app: Application) : AndroidViewModel(app) {

    // ── UI State ──────────────────────────────────────────

    sealed class FaceState {
        object Idle       : FaceState()
        object Capturing  : FaceState()            // đang chụp ảnh
        object Verifying  : FaceState()            // đang gửi server
        data class Success(
            val response:  CheckinResponse,
            val faceScore: Double? = null
        ) : FaceState()
        data class Failure(
            val message:   String,
            val faceScore: Double? = null,
            val canRetry:  Boolean = true
        ) : FaceState()
        object ServiceUnavailable : FaceState()   // AI service down → fallback QR-only
    }

    private val _state = MutableLiveData<FaceState>(FaceState.Idle)
    val state: LiveData<FaceState> = _state

    private val _retryCount = MutableLiveData(0)
    val retryCount: LiveData<Int> = _retryCount

    companion object {
        const val MAX_RETRIES   = 3      // Tối đa 3 lần chụp lại
        const val JPEG_QUALITY  = 85     // Chất lượng JPEG (85% = đủ tốt cho ArcFace)
    }

    // ── Verify face ───────────────────────────────────────

    /**
     * Gửi ảnh khuôn mặt lên server để verify 1:1 với stored embedding.
     *
     * @param bitmap      Ảnh chụp từ camera trước
     * @param qrToken     JWT QR token (đã verify ở bước trước)
     * @param gateId      ID cổng đang làm việc
     * @param direction   IN hoặc OUT
     */
    fun verifyFace(
        bitmap:    Bitmap,
        qrToken:   String,
        gateId:    String,
        direction: String
    ) {
        _state.value = FaceState.Verifying

        viewModelScope.launch {
            try {
                val b64 = bitmapToBase64(bitmap)
                val api = ApiClient.create(getApplication())

                val req = CheckinRequest(
                    gate_id         = gateId,
                    direction       = direction,
                    channel         = "QR_FACE",
                    qr_token        = qrToken,
                    probe_image_b64 = b64
                )
                val resp = api.checkin(req)

                if (resp.success) {
                    _state.value = FaceState.Success(
                        response  = resp,
                        faceScore = resp.face_score
                    )
                } else {
                    val canRetry = (_retryCount.value ?: 0) < MAX_RETRIES
                    _state.value = FaceState.Failure(
                        message   = resp.message,
                        faceScore = resp.face_score,
                        canRetry  = canRetry
                    )
                }

            } catch (e: retrofit2.HttpException) {
                when (e.code()) {
                    503 -> {
                        // AI service không khả dụng → fallback QR-only
                        _state.value = FaceState.ServiceUnavailable
                    }
                    else -> {
                        _state.value = FaceState.Failure(
                            message  = "Lỗi server: ${e.code()}",
                            canRetry = true
                        )
                    }
                }
            } catch (e: Exception) {
                // Mất mạng → cũng fallback
                _state.value = FaceState.ServiceUnavailable
            }
        }
    }

    // ── Retry ─────────────────────────────────────────────

    fun incrementRetry() {
        _retryCount.value = (_retryCount.value ?: 0) + 1
    }

    fun hasReachedMaxRetries(): Boolean =
        (_retryCount.value ?: 0) >= MAX_RETRIES

    fun resetForRetry() {
        _state.value = FaceState.Idle
    }

    fun resetAll() {
        _state.value  = FaceState.Idle
        _retryCount.value = 0
    }

    // ── Helpers ───────────────────────────────────────────

    /**
     * Chuyển Bitmap → JPEG base64 string.
     * Resize nếu cần để giảm payload (max 600px mỗi chiều).
     */
    private fun bitmapToBase64(bitmap: Bitmap): String {
        val resized = resizeBitmap(bitmap, maxDim = 600)
        val stream  = ByteArrayOutputStream()
        resized.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, stream)
        val b64 = Base64.encodeToString(stream.toByteArray(), Base64.NO_WRAP)
        return "data:image/jpeg;base64,$b64"
    }

    private fun resizeBitmap(src: Bitmap, maxDim: Int): Bitmap {
        val w = src.width
        val h = src.height
        if (w <= maxDim && h <= maxDim) return src
        val scale = maxDim.toFloat() / maxOf(w, h)
        return Bitmap.createScaledBitmap(src, (w * scale).toInt(), (h * scale).toInt(), true)
    }
}
