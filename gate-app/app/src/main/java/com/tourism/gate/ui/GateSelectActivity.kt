package com.tourism.gate.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.Gate
import kotlinx.coroutines.launch

class GateSelectActivity : AppCompatActivity() {

    private lateinit var spinnerGate: Spinner
    private lateinit var btnSelect: TextView
    private lateinit var btnLogout: TextView
    private lateinit var progressBar: ProgressBar
    private lateinit var tvWelcome: TextView
    private lateinit var tvError: TextView

    private var gates: List<Gate> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_gate_select)

        spinnerGate = findViewById(R.id.spinnerGate)
        btnSelect   = findViewById(R.id.btnSelect)
        btnLogout   = findViewById(R.id.btnLogout)
        progressBar = findViewById(R.id.progressBar)
        tvWelcome   = findViewById(R.id.tvWelcome)
        tvError     = findViewById(R.id.tvError)

        // Hiển thị tên nhân viên
        val prefs    = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val fullName = prefs.getString("full_name", "Nhân viên") ?: "Nhân viên"
        val role     = prefs.getString("role", "") ?: ""
        tvWelcome.text = "Xin chào, $fullName ($role)"

        // Nếu operator đã được gán cổng cố định → tự động chọn
        val assignedGateId = prefs.getString("gate_id", "") ?: ""

        btnLogout.setOnClickListener { doLogout() }

        btnSelect.setOnClickListener {
            val selected = gates.getOrNull(spinnerGate.selectedItemPosition)
            if (selected == null) {
                tvError.text = "Vui lòng chọn cổng"
                tvError.visibility = View.VISIBLE
                return@setOnClickListener
            }
            // Lưu cổng đã chọn
            prefs.edit().putString("selected_gate_id",   selected.gate_id)
                         .putString("selected_gate_code", selected.gate_code)
                         .putString("selected_gate_name", selected.name)
                         .apply()

            startActivity(Intent(this, SelectDirectionActivity::class.java))
        }

        loadGates(assignedGateId)
    }

    private fun loadGates(assignedGateId: String) {
        setLoading(true)
        lifecycleScope.launch {
            try {
                val api = ApiClient.create(this@GateSelectActivity)
                gates   = api.listGates()

                val labels = gates.map { "${it.gate_code} — ${it.name}" }
                val adapter = ArrayAdapter(
                    this@GateSelectActivity,
                    android.R.layout.simple_spinner_item,
                    labels
                ).also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
                spinnerGate.adapter = adapter

                // Chọn sẵn cổng được gán nếu có
                if (assignedGateId.isNotEmpty()) {
                    val idx = gates.indexOfFirst { it.gate_id == assignedGateId }
                    if (idx >= 0) spinnerGate.setSelection(idx)
                }

            } catch (e: Exception) {
                tvError.text = "Không tải được danh sách cổng: ${e.message}"
                tvError.visibility = View.VISIBLE
            } finally {
                setLoading(false)
            }
        }
    }

    private fun doLogout() {
        getSharedPreferences("gate_prefs", MODE_PRIVATE).edit().clear().apply()
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }

    private fun setLoading(loading: Boolean) {
        progressBar.visibility = if (loading) View.VISIBLE else View.GONE
        btnSelect.isEnabled    = !loading
    }
}
