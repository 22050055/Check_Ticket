package com.tourism.gate.ui

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import com.tourism.gate.R

class ResultActivity : AppCompatActivity() {

    private lateinit var ivIcon: ImageView
    private lateinit var tvResult: TextView
    private lateinit var tvMessage: TextView
    private lateinit var tvTicketType: TextView
    private lateinit var btnNext: TextView
    private lateinit var btnManual: TextView
    private lateinit var layoutResult: LinearLayout

    private val AUTO_BACK_DELAY_MS = 4000L   // Tự quay lại sau 4 giây

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_result)

        ivIcon       = findViewById(R.id.ivIcon)
        tvResult     = findViewById(R.id.tvResult)
        tvMessage    = findViewById(R.id.tvMessage)
        tvTicketType = findViewById(R.id.tvTicketType)
        btnNext      = findViewById(R.id.btnNext)
        btnManual    = findViewById(R.id.btnManual)
        layoutResult = findViewById(R.id.layoutResult)

        val success    = intent.getBooleanExtra("success", false)
        val message    = intent.getStringExtra("message")    ?: ""
        val ticketType = intent.getStringExtra("ticket_type") ?: ""

        renderResult(success, message, ticketType)

        // Tự động quay về Scan sau N giây
        Handler(Looper.getMainLooper()).postDelayed({
            if (!isFinishing) goToScan()
        }, AUTO_BACK_DELAY_MS)

        btnNext.setOnClickListener   { goToScan() }
        btnManual.setOnClickListener {
            startActivity(Intent(this, ManualSearchActivity::class.java))
            finish()
        }
    }

    private fun renderResult(success: Boolean, message: String, ticketType: String) {
        if (success) {
            layoutResult.setBackgroundColor(0xFF52C41A.toInt())  // xanh lá
            ivIcon.setImageResource(android.R.drawable.ic_dialog_info)
            tvResult.text      = "✅ HỢP LỆ"
            tvResult.setTextColor(Color.WHITE)
            tvMessage.text     = message
            tvTicketType.text  = if (ticketType.isNotEmpty()) "Loại vé: $ticketType" else ""
        } else {
            layoutResult.setBackgroundColor(0xFFF5222D.toInt())  // đỏ
            ivIcon.setImageResource(android.R.drawable.ic_dialog_alert)
            tvResult.text      = "❌ KHÔNG HỢP LỆ"
            tvResult.setTextColor(Color.WHITE)
            tvMessage.text     = message
            tvTicketType.text  = ""
        }
    }

    private fun goToScan() {
        startActivity(Intent(this, ScanActivity::class.java))
        finish()
    }

    // Không cho back về result cũ
    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        goToScan()
    }
}
