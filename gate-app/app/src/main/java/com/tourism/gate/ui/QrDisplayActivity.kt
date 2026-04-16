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

        findViewById<TextView>(R.id.tvTicketId).text = "Mã vé: $ticketId"

        // Hiển thị ảnh QR
        val ivQr = findViewById<ImageView>(R.id.ivQrCode)
        if (!qrB64.isNullOrEmpty()) {
            try {
                val raw  = if (qrB64.contains(",")) qrB64.substringAfter(",") else qrB64
                val bytes = Base64.decode(raw, Base64.DEFAULT)
                val bmp   = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                ivQr.setImageBitmap(bmp)
            } catch (_: Exception) {
                ivQr.visibility = View.GONE
                findViewById<TextView>(R.id.tvQrFallback).visibility = View.VISIBLE
            }
        } else {
            ivQr.visibility = View.GONE
            findViewById<TextView>(R.id.tvQrFallback).visibility = View.VISIBLE
        }

        // Nút "Phát hành vé mới"
        findViewById<TextView>(R.id.btnNewTicket).setOnClickListener {
            finish()
        }

        // Nút "Về trang chủ"
        findViewById<TextView>(R.id.btnHome).setOnClickListener {
            startActivity(Intent(this, RoleSelectActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            })
        }
    }
}
