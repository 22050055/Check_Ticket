package com.tourism.gate.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.tourism.gate.R

/**
 * RoleSelectActivity — Màn hình chọn vai trò ca trực.
 * Hiển thị sau khi đăng nhập thành công.
 *
 * Roles:
 *   Bán vé (cashier)   → SellTicketActivity
 *   Nhân viên cổng     → GateSelectActivity → SelectDirectionActivity → ScanActivity
 */
class RoleSelectActivity : AppCompatActivity() {

    private lateinit var tvFullName:   TextView
    private lateinit var tvRole:       TextView
    private lateinit var tvShiftInfo:  TextView
    private lateinit var cardCashier:  LinearLayout
    private lateinit var cardOperator: LinearLayout
    private lateinit var btnLogout:    TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_role_select)

        tvFullName   = findViewById(R.id.tvFullName)
        tvRole       = findViewById(R.id.tvRole)
        tvShiftInfo  = findViewById(R.id.tvShiftInfo)
        cardCashier  = findViewById(R.id.cardCashier)
        cardOperator = findViewById(R.id.cardOperator)
        btnLogout    = findViewById(R.id.btnLogout)

        val prefs    = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val fullName = prefs.getString("full_name", "Nhân viên") ?: "Nhân viên"
        val role     = prefs.getString("role", "") ?: ""

        tvFullName.text = fullName
        tvRole.text     = role.replaceFirstChar { it.uppercase() }
        tvShiftInfo.text = "Ca trực: ${java.text.SimpleDateFormat("HH:mm dd/MM/yyyy").format(java.util.Date())}"

        // Ẩn card không phù hợp role
        when (role) {
            "cashier" -> {
                cardOperator.visibility = View.GONE
            }
            "operator" -> {
                cardCashier.visibility = View.GONE
            }
            // admin / manager thấy cả 2
        }

        cardCashier.setOnClickListener {
            prefs.edit().putString("session_role", "cashier").apply()
            startActivity(Intent(this, SellTicketActivity::class.java))
        }

        cardOperator.setOnClickListener {
            prefs.edit().putString("session_role", "operator").apply()
            startActivity(Intent(this, GateSelectActivity::class.java))
        }

        btnLogout.setOnClickListener {
            prefs.edit().clear().apply()
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }

    override fun onBackPressed() {
        // Không cho back về màn hình login sau khi đã đăng nhập
    }
}
 