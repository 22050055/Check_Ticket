package com.tourism.gate.ui

import android.content.Intent
import android.graphics.BitmapFactory
import android.os.Bundle
import android.util.Base64
import android.view.View
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.tourism.gate.R

/**
 * QrDisplayActivity — Hiển thị mã QR sau khi phát hành vé thành công.
 * Nhân viên có thể in / chụp màn hình QR để đưa cho khách.
 */
class QrDisplayActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_qr_display)

        val ticketId  = intent.getStringExtra("ticket_id") ?: ""
        val qrB64     = intent.getStringExtra("qr_image_b64")
        val qrBytes   = intent.getByteArrayExtra("qr_bytes")  // từ màn hình khách

        findViewById<TextView>(R.id.tvTicketId).text = "Mã vé: $ticketId"

        // Hiển thị ảnh QR
        val ivQr = findViewById<ImageView>(R.id.ivQrCode)
        val bitmap = when {
            // Ưu tiên bytes trực tiếp (khách hàng tải về)
            qrBytes != null -> BitmapFactory.decodeByteArray(qrBytes, 0, qrBytes.size)
            // Fallback: base64 chuỗi từ nhân viên phát hành
            !qrB64.isNullOrEmpty() -> try {
                val raw = if (qrB64.contains(",")) qrB64.substringAfter(",") else qrB64
                val bytes = Base64.decode(raw, Base64.DEFAULT)
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            } catch (_: Exception) { null }
            else -> null
        }

        if (bitmap != null) {
            ivQr.setImageBitmap(bitmap)
        } else {
            ivQr.visibility = View.GONE
            findViewById<TextView>(R.id.tvQrFallback).visibility = View.VISIBLE
        }

        val prefs    = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val role     = prefs.getString("role", "") ?: ""
        val isCustomer = role.isEmpty()

        if (isCustomer) {
            findViewById<TextView>(R.id.tvToolbarTitle).text = "Mã vé điện tử"
            findViewById<TextView>(R.id.tvStatusBadge).text  = "MUA VÉ THÀNH CÔNG"
            findViewById<TextView>(R.id.tvHint).text         = "Xuất trình mã này tại cổng soát vé"
            findViewById<TextView>(R.id.btnNewTicket).text   = "🎫 Mua thêm vé mới"
            findViewById<TextView>(R.id.btnHome).text        = "Vé của tôi"
        }

        // Nút "Phát hành vé mới / Mua vé mới"
        findViewById<TextView>(R.id.btnNewTicket).setOnClickListener {
            if (isCustomer) {
                startActivity(Intent(this, com.tourism.gate.ui.customer.CustomerBuyTicketActivity::class.java))
            }
            finish()
        }

        // Nút "Về trang chủ"
        findViewById<TextView>(R.id.btnHome).setOnClickListener {
            val destActivity = if (isCustomer) {
                com.tourism.gate.ui.customer.CustomerDashboardActivity::class.java
            } else {
                RoleSelectActivity::class.java
            }

            startActivity(Intent(this, destActivity).apply {
                flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
                if (isCustomer) {
                    putExtra("open_tab", R.id.nav_tickets)
                }
            })
            finish()
        }
    }
}
 