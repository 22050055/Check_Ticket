package com.tourism.gate.utils

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.util.Log
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * NetworkUtils — Detect trạng thái mạng và retry helper.
 *
 * Tính năng:
 *  - isOnline(): kiểm tra mạng ngay lập tức
 *  - observeNetworkState(): Flow<Boolean> emit mỗi khi mạng thay đổi
 *  - retryWithBackoff(): retry coroutine với exponential backoff
 *  - requiresOnline(): wrapper throw OfflineException nếu không có mạng
 */
object NetworkUtils {

    private const val TAG = "NetworkUtils"

    // ── State Flow (reactive) ─────────────────────────────

    private val _isOnline = MutableStateFlow(true)

    /** Flow<Boolean> — emit true khi có mạng, false khi mất mạng */
    val networkState: Flow<Boolean> = _isOnline.asStateFlow()

    // ── Singleton callback (register 1 lần trong Application) ──

    private var _callbackRegistered = false

    /**
     * Đăng ký listener mạng — gọi 1 lần trong Application.onCreate().
     * Tự động cập nhật networkState khi mạng thay đổi.
     */
    fun registerNetworkCallback(context: Context) {
        if (_callbackRegistered) return

        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE)
                as ConnectivityManager

        // Cập nhật state ngay lập tức
        _isOnline.value = isOnline(context)

        val request = NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()

        cm.registerNetworkCallback(request, object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                Log.i(TAG, "Mạng khả dụng: $network")
                _isOnline.value = true
            }

            override fun onLost(network: Network) {
                Log.w(TAG, "Mạng bị ngắt: $network")
                // Kiểm tra còn network khác không
                _isOnline.value = isOnline(context)
            }

            override fun onCapabilitiesChanged(
                network: Network,
                caps: NetworkCapabilities
            ) {
                val hasInternet = caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                        && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
                _isOnline.value = hasInternet
            }
        })

        _callbackRegistered = true
    }

    // ── Instant check ─────────────────────────────────────

    /**
     * Kiểm tra mạng ngay lập tức (synchronous).
     * Dùng trong coroutine hoặc khi cần check nhanh.
     */
    fun isOnline(context: Context): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE)
                as ConnectivityManager
        val network = cm.activeNetwork ?: return false
        val caps    = cm.getNetworkCapabilities(network) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
    }

    fun isOffline(context: Context): Boolean = !isOnline(context)

    // ── Retry with exponential backoff ────────────────────

    /**
     * Retry một suspend function với exponential backoff.
     *
     * @param times         Số lần retry tối đa
     * @param initialDelay  Delay ban đầu (ms)
     * @param maxDelay      Delay tối đa (ms)
     * @param factor        Hệ số tăng delay (mặc định 2.0)
     * @param block         Suspend function cần retry
     *
     * Ví dụ:
     *   val result = retryWithBackoff(times = 3) { api.checkin(req) }
     */
    suspend fun <T> retryWithBackoff(
        times:        Int   = 3,
        initialDelay: Long  = 500L,
        maxDelay:     Long  = 5000L,
        factor:       Double = 2.0,
        block:        suspend () -> T
    ): T {
        var currentDelay = initialDelay
        repeat(times - 1) { attempt ->
            try {
                return block()
            } catch (e: Exception) {
                Log.w(TAG, "Retry ${attempt + 1}/$times thất bại: ${e.message}")
            }
            delay(currentDelay)
            currentDelay = minOf((currentDelay * factor).toLong(), maxDelay)
        }
        // Lần cuối — không catch để bubble up exception
        return block()
    }

    /**
     * Wrapper: throw OfflineException nếu mất mạng, ngược lại chạy block.
     * Dùng để phân biệt lỗi mạng vs lỗi server trong ViewModel.
     */
    suspend fun <T> requiresOnline(context: Context, block: suspend () -> T): T {
        if (isOffline(context)) throw OfflineException("Không có kết nối mạng")
        return block()
    }

    /**
     * Thử kết nối server bằng cách ping /health endpoint.
     *
     * @return true nếu server phản hồi trong timeout
     */
    suspend fun pingServer(serverUrl: String, timeoutMs: Int = 3000): Boolean {
        return try {
            val url = java.net.URL("${serverUrl.trimEnd('/')}/health")
            val conn = url.openConnection() as java.net.HttpURLConnection
            conn.connectTimeout = timeoutMs
            conn.readTimeout    = timeoutMs
            conn.requestMethod  = "GET"
            val code = conn.responseCode
            conn.disconnect()
            code == 200
        } catch (_: Exception) {
            false
        }
    }

    // ── Exception types ───────────────────────────────────

    class OfflineException(message: String) : Exception(message)
    class ServerUnavailableException(message: String) : Exception(message)
}
