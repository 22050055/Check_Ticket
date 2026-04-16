package com.tourism.gate

import android.app.Application
import com.tourism.gate.utils.NetworkUtils

/**
 * GateApplication — Application class, khởi chạy 1 lần khi app start.
 * Đăng ký network listener để theo dõi mạng toàn app.
 */
class GateApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        // Đăng ký network callback — theo dõi online/offline toàn app
        NetworkUtils.registerNetworkCallback(this)
    }
}
