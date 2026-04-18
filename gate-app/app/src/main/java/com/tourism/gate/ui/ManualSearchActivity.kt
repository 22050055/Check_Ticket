package com.tourism.gate.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.CheckinRequest
import kotlinx.coroutines.launch

class ManualSearchActivity : AppCompatActivity() {

    private lateinit var rgSearchType: RadioGroup
    private lateinit var rbPhone: RadioButton
    private lateinit var rbBooking: RadioButton
    private lateinit var rbTicketId: RadioButton
    private lateinit var etSearch: EditText
    private lateinit var btnSearch: TextView
    private lateinit var progressBar: ProgressBar
    private lateinit var tvError: TextView
    private lateinit var tvDirection: TextView
    private lateinit var btnBack: TextView
    private lateinit var btnHome: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_manual_search)

        rgSearchType = findViewById(R.id.rgSearchType)
        rbPhone      = findViewById(R.id.rbPhone)
        rbBooking    = findViewById(R.id.rbBooking)
        rbTicketId   = findViewById(R.id.rbTicketId)
        etSearch     = findViewById(R.id.etSearch)
        btnSearch    = findViewById(R.id.btnSearch)
        progressBar  = findViewById(R.id.progressBar)
        tvError      = findViewById(R.id.tvError)
        tvDirection  = findViewById(R.id.tvDirection)
        btnBack      = findViewById(R.id.btnBack)
        btnHome      = findViewById(R.id.btnHome)

        val prefs     = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val direction = prefs.getString("direction", "IN") ?: "IN"
        tvDirection.text = "Chiều: $direction"

        // Cập nhật hint theo loại tìm kiếm
        rgSearchType.setOnCheckedChangeListener { _, checkedId ->
            etSearch.hint = when (checkedId) {
                R.id.rbPhone    -> "Nhập số điện thoại"
                R.id.rbBooking  -> "Nhập mã booking"
                R.id.rbTicketId -> "Nhập ticket ID"
                else            -> "Nhập thông tin tìm kiếm"
            }
        }
        rbPhone.isChecked = true   // mặc định tìm theo SĐT

        btnSearch.setOnClickListener { doSearch() }
        btnBack.setOnClickListener   { finish() }
        btnHome.setOnClickListener {
            val intent = Intent(this, RoleSelectActivity::class.java)
            intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)
            startActivity(intent)
        }
    }

    private fun doSearch() {
        val query = etSearch.text.toString().trim()
        if (query.isEmpty()) {
            tvError.text = "Vui lòng nhập thông tin tìm kiếm"
            tvError.visibility = View.VISIBLE
            return
        }

        tvError.visibility = View.GONE
        setLoading(true)

        val prefs     = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val gateId    = prefs.getString("selected_gate_id", "") ?: ""
        val direction = prefs.getString("direction", "IN") ?: "IN"

        // Xây dựng request theo loại tìm kiếm đã chọn
        val req = when (rgSearchType.checkedRadioButtonId) {
            R.id.rbPhone    -> CheckinRequest(
                gate_id   = gateId,
                direction = direction,
                channel   = "MANUAL",
                phone     = query
            )
            R.id.rbBooking  -> CheckinRequest(
                gate_id    = gateId,
                direction  = direction,
                channel    = "BOOKING",
                booking_id = query
            )
            R.id.rbTicketId -> CheckinRequest(
                gate_id   = gateId,
                direction = direction,
                channel   = "MANUAL",
                ticket_id = query
            )
            else -> return
        }

        lifecycleScope.launch {
            try {
                val api    = ApiClient.create(this@ManualSearchActivity)
                val result = api.checkin(req)

                val intent = Intent(this@ManualSearchActivity, ResultActivity::class.java).apply {
                    putExtra("success",     result.success)
                    putExtra("message",     result.message)
                    putExtra("ticket_type", result.ticket_type)
                }
                startActivity(intent)
                finish()

            } catch (e: Exception) {
                tvError.text = "Lỗi tìm kiếm: ${e.message}"
                tvError.visibility = View.VISIBLE
            } finally {
                setLoading(false)
            }
        }
    }

    private fun setLoading(loading: Boolean) {
        progressBar.visibility = if (loading) View.VISIBLE else View.GONE
        btnSearch.isEnabled    = !loading
    }
}
 