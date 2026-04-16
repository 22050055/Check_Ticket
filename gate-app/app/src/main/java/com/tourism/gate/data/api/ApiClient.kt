package com.tourism.gate.data.api

import android.content.Context
import com.tourism.gate.BuildConfig
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * ApiClient — Retrofit singleton factory.
 *
 * Cấu hình:
 *  - Base URL đọc từ SharedPreferences (có thể đổi tại runtime)
 *  - JWT token tự động gắn vào mọi request qua AuthInterceptor
 *  - Timeout: connect 10s, read/write 30s (face verify cần lâu hơn)
 *  - Logging: chỉ bật ở DEBUG build
 */
object ApiClient {

    // URL mặc định — đọc từ BuildConfig (đã cấu hình trong build.gradle)
    private val DEFAULT_BASE_URL = BuildConfig.BASE_URL

    fun create(context: Context): ApiService {
        val prefs   = context.getSharedPreferences("gate_prefs", Context.MODE_PRIVATE)
        // Ép cứng đọc URL cấu hình từ BuildConfig, bỏ qua dữ liệu cũ bị kẹt trong máy:
        val baseUrl = DEFAULT_BASE_URL 
        // val baseUrl = prefs.getString("server_url", DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
        val token   = prefs.getString("token", null)

        val client = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)     // face verify có thể mất 5-10s
            .writeTimeout(30, TimeUnit.SECONDS)
            .addInterceptor(AuthInterceptor(token))
            .addInterceptor(buildLoggingInterceptor())
            .build()

        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }

    // ── Auth interceptor — tự động gắn JWT header ─────────

    private class AuthInterceptor(private val token: String?) : Interceptor {
        override fun intercept(chain: Interceptor.Chain): okhttp3.Response {
            val request = chain.request()
            if (token.isNullOrEmpty()) return chain.proceed(request)

            val authed = request.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
            return chain.proceed(authed)
        }
    }

    // ── Logging interceptor (chỉ DEBUG) ───────────────────

    private fun buildLoggingInterceptor(): HttpLoggingInterceptor {
        return HttpLoggingInterceptor().apply {
            level = if (android.util.Log.isLoggable("API", android.util.Log.DEBUG))
                HttpLoggingInterceptor.Level.BODY
            else
                HttpLoggingInterceptor.Level.NONE
        }
    }

    /**
     * Tạo ApiClient với token mới (sau khi refresh).
     * Gọi khi access_token hết hạn và đã refresh xong.
     */
    fun createWithToken(context: Context, token: String): ApiService {
        // Lưu token mới vào prefs rồi tạo lại client
        context.getSharedPreferences("gate_prefs", Context.MODE_PRIVATE)
            .edit().putString("token", token).apply()
        return create(context)
    }
}
