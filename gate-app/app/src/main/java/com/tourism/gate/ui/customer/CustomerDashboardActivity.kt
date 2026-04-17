package com.tourism.gate.ui.customer

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.CustomerTicket
import com.tourism.gate.ui.LoginActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * CustomerDashboardActivity — Màn hình chính cho Khách hàng.
 * Hiển thị danh sách vé đã được nhân viên phát hành.
 * Khách có thể tải QR và đăng ký khuôn mặt cho từng vé.
 */
class CustomerDashboardActivity : AppCompatActivity() {

    private lateinit var tvCustomerName:  TextView
    private lateinit var tvCustomerEmail: TextView
    private lateinit var tvTicketCount:   TextView
    private lateinit var btnLogout:       TextView
    private lateinit var progressBar:     ProgressBar
    private lateinit var layoutEmpty:     View
    private lateinit var recyclerTickets: RecyclerView
    private lateinit var fabBuyTicket:   View

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_customer_dashboard)

        // Bind views
        tvCustomerName  = findViewById(R.id.tv_customer_name)
        tvCustomerEmail = findViewById(R.id.tv_customer_email)
        tvTicketCount   = findViewById(R.id.tv_ticket_count)
        btnLogout       = findViewById(R.id.btn_logout)
        progressBar     = findViewById(R.id.progressBar)
        layoutEmpty     = findViewById(R.id.layout_empty)
        recyclerTickets = findViewById(R.id.recycler_tickets)
        fabBuyTicket    = findViewById(R.id.fab_buy_ticket)

        recyclerTickets.layoutManager = LinearLayoutManager(this)

        // Hiển thị thông tin cơ bản từ SharedPreferences
        val prefs = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val email = prefs.getString("customer_email", "") ?: ""
        tvCustomerEmail.text = email.ifBlank { "Khách hàng" }

        // Xử lý nút đăng xuất
        btnLogout.setOnClickListener { confirmLogout() }

        // Xử lý nút mua vé
        fabBuyTicket.setOnClickListener {
            startActivity(Intent(this, CustomerBuyTicketActivity::class.java))
        }

        loadTickets()
    }

    private fun loadTickets() {
        showLoading(true)
        val api = ApiClient.create(this)
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val tickets = api.getCustomerTickets()
                withContext(Dispatchers.Main) {
                    showLoading(false)
                    if (tickets.isEmpty()) {
                        showEmpty(true)
                    } else {
                        showEmpty(false)
                        tvTicketCount.text = "${tickets.size} vé"
                        // Lấy tên từ vé đầu tiên nếu có
                        setupAdapter(tickets)
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    showLoading(false)
                    showEmpty(true)
                    Toast.makeText(
                        this@CustomerDashboardActivity,
                        "Lỗi tải danh sách vé: ${e.message}",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }
    }

    private fun setupAdapter(tickets: List<CustomerTicket>) {
        val adapter = CustomerTicketAdapter(
            context = this,
            tickets = tickets,
            onDownloadQr = { ticket -> downloadQr(ticket) },
            onEnrollFace = { ticket -> enrollFace(ticket) }
        )
        recyclerTickets.adapter = adapter
        recyclerTickets.visibility = View.VISIBLE
    }

    // ── Tải ảnh QR về và hiển thị ──────────────────────────────
    private fun downloadQr(ticket: CustomerTicket) {
        Toast.makeText(this, "Đang tải mã QR vé #${ticket.ticketId.take(8)}…", Toast.LENGTH_SHORT).show()
        val api = ApiClient.create(this)
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Gọi endpoint tải QR (trả về bytes PNG)
                val response = api.downloadCustomerQr(ticket.ticketId)
                val qrBytes = response.bytes()
                withContext(Dispatchers.Main) {
                    // Mở QrDisplayActivity với ảnh byte[]
                    val intent = Intent(this@CustomerDashboardActivity, com.tourism.gate.ui.QrDisplayActivity::class.java)
                    intent.putExtra("qr_bytes", qrBytes)
                    intent.putExtra("ticket_id", ticket.ticketId)
                    startActivity(intent)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@CustomerDashboardActivity, "Lỗi tải QR: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    // ── Đăng ký khuôn mặt cho vé ───────────────────────────────
    private fun enrollFace(ticket: CustomerTicket) {
        if (ticket.hasFace) {
            Toast.makeText(this, "Vé này đã đăng ký khuôn mặt rồi!", Toast.LENGTH_SHORT).show()
            return
        }
        val intent = Intent(this, com.tourism.gate.ui.FaceEnrollActivity::class.java)
        intent.putExtra("ticket_id", ticket.ticketId)
        intent.putExtra("mode", "customer") // phân biệt với chế độ nhân viên
        startActivity(intent)
    }

    // ── Xác nhận đăng xuất ─────────────────────────────────────
    private fun confirmLogout() {
        AlertDialog.Builder(this)
            .setTitle("Đăng xuất")
            .setMessage("Bạn có chắc muốn đăng xuất không?")
            .setPositiveButton("Đăng xuất") { _, _ -> doLogout() }
            .setNegativeButton("Huỷ", null)
            .show()
    }

    private fun doLogout() {
        getSharedPreferences("gate_prefs", MODE_PRIVATE).edit().clear().apply()
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }

    // ── Helpers ────────────────────────────────────────────────
    private fun showLoading(loading: Boolean) {
        progressBar.visibility = if (loading) View.VISIBLE else View.GONE
    }

    private fun showEmpty(empty: Boolean) {
        layoutEmpty.visibility     = if (empty) View.VISIBLE else View.GONE
        recyclerTickets.visibility = if (empty) View.GONE    else View.VISIBLE
    }
}
 