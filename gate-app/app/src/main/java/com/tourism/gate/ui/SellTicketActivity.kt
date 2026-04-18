package com.tourism.gate.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.TicketIssueRequest
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * SellTicketActivity — Nhân viên bán vé:
 *  1. Điền form phát hành vé
 *  2. Tùy chọn: đăng ký khuôn mặt opt-in
 *  3. POST /api/tickets → nhận QR
 *  4. Nếu bật face → chụp ảnh → POST /api/face/enroll
 */
class SellTicketActivity : AppCompatActivity() {

    companion object {
        private const val RC_FACE_ENROLL = 1001
    }

    private lateinit var btnBack:          TextView
    private lateinit var btnHome:          TextView
    private lateinit var etCustomerName:   EditText
    private lateinit var etPhone:          EditText
    private lateinit var spinnerType:      Spinner
    private lateinit var etPrice:          EditText
    private lateinit var etBookingId:      EditText
    private lateinit var switchFace:       android.widget.Switch
    private lateinit var btnIssue:         TextView
    private lateinit var progressBar:      ProgressBar
    private lateinit var tvError:          TextView

    // Lưu thông tin vé sau khi phát hành — dùng cho flow face enroll → QR
    private var issuedTicketId: String? = null
    private var issuedQrB64:   String? = null

    private val ticketTypes    = listOf("Người lớn", "Trẻ em", "Học sinh/SV", "Nhóm")
    private val ticketTypeKeys = listOf("adult", "child", "student", "group")
    private val defaultPrices  = listOf("150000", "80000", "100000", "500000")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_sell_ticket)

        btnBack        = findViewById(R.id.btnBack)
        btnHome        = findViewById(R.id.btnHome)
        etCustomerName = findViewById(R.id.etCustomerName)
        etPhone        = findViewById(R.id.etPhone)
        spinnerType    = findViewById(R.id.spinnerTicketType)
        etPrice        = findViewById(R.id.etPrice)
        switchFace     = findViewById(R.id.switchFace)
        btnIssue       = findViewById(R.id.btnIssue)
        progressBar    = findViewById(R.id.progressBar)
        tvError        = findViewById(R.id.tvError)

        setupSpinner()

        btnBack.setOnClickListener  { finish() }
        btnHome.setOnClickListener {
            val intent = Intent(this, RoleSelectActivity::class.java)
            intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)
            startActivity(intent)
        }
        btnIssue.setOnClickListener { issueTicket() }
    }

    private fun setupSpinner() {
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, ticketTypes)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spinnerType.adapter = adapter

        spinnerType.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) {
                etPrice.setText(defaultPrices[pos])
            }
            override fun onNothingSelected(p: AdapterView<*>?) {}
        }
    }

    // ── Phát hành vé ─────────────────────────────────────────────

    private fun issueTicket() {
        val name  = etCustomerName.text.toString().trim()
        val phone = etPhone.text.toString().trim()
        val price = etPrice.text.toString().toDoubleOrNull()

        if (name.isEmpty())              { showError("Vui lòng nhập tên khách"); return }
        if (price == null || price <= 0) { showError("Giá vé không hợp lệ");    return }

        tvError.visibility = View.GONE
        setLoading(true)

        val now      = System.currentTimeMillis()
        val endOfDay = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, 23)
            set(Calendar.MINUTE, 59)
            set(Calendar.SECOND, 59)
        }.timeInMillis
        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }

        val selectedType = ticketTypeKeys[spinnerType.selectedItemPosition]

        lifecycleScope.launch {
            try {
                val api = ApiClient.create(this@SellTicketActivity)
                val req = TicketIssueRequest(
                    customerName  = name,
                    customerPhone = phone.ifEmpty { null },
                    ticketType    = selectedType,
                    price         = price,
                    validFrom     = sdf.format(Date(now)),
                    validUntil    = sdf.format(Date(endOfDay)),
                    paymentMethod = "cash",
                    bookingId     = null   // Bỏ bookingId thủ công, hệ thống tự generate hoặc link logic khác
                )
                val ticket = api.issueTicket(req)

                // Lưu lại để dùng sau enroll
                issuedTicketId = ticket.ticketId
                issuedQrB64    = ticket.qrImageB64

                setLoading(false)

                if (switchFace.isChecked) {
                    showFaceEnrollDialog(ticket.ticketId, ticket.ticketType)
                } else {
                    showQrResult(ticket.ticketId, ticket.qrImageB64)
                }

            } catch (e: Exception) {
                setLoading(false)
                showError("Phát hành thất bại: ${e.message}")
            }
        }
    }

    // ── Hiển thị QR ──────────────────────────────────────────────

    private fun showQrResult(ticketId: String?, qrB64: String?) {
        if (ticketId.isNullOrEmpty()) return
        val intent = Intent(this, QrDisplayActivity::class.java).apply {
            putExtra("ticket_id",    ticketId)
            putExtra("qr_image_b64", qrB64)
        }
        startActivity(intent)
    }

    // ── Dialog face enroll ────────────────────────────────────────

    private fun showFaceEnrollDialog(ticketId: String, ticketType: String) {
        AlertDialog.Builder(this)
            .setTitle("Đăng ký khuôn mặt")
            .setMessage("Vé $ticketType đã tạo.\nChụp ảnh khuôn mặt khách để đăng ký xác thực 1:1 tại cổng.")
            .setPositiveButton("📷 Chụp ảnh") { _, _ ->
                val intent = Intent(this, FaceEnrollActivity::class.java).apply {
                    putExtra("ticket_id", ticketId)
                }
                @Suppress("DEPRECATION")
                startActivityForResult(intent, RC_FACE_ENROLL)
            }
            .setNegativeButton("Bỏ qua") { _, _ ->
                showQrResult(ticketId, issuedQrB64)
            }
            .setCancelable(false)
            .show()
    }

    // ── Sau khi FaceEnrollActivity finish() → mở QR ──────────────

    @Suppress("DEPRECATION")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == RC_FACE_ENROLL) {
            showQrResult(issuedTicketId ?: "", issuedQrB64)
        }
    }

    // ── Helpers ───────────────────────────────────────────────────

    private fun showError(msg: String) {
        tvError.text       = msg
        tvError.visibility = View.VISIBLE
    }

    private fun setLoading(loading: Boolean) {
        btnIssue.isEnabled     = !loading
        progressBar.visibility = if (loading) View.VISIBLE else View.GONE
    }
}
 