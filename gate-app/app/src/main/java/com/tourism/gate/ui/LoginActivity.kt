package com.tourism.gate.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.CustomerLoginRequest
import com.tourism.gate.data.model.LoginRequest
import com.tourism.gate.ui.customer.CustomerDashboardActivity
import com.tourism.gate.ui.customer.CustomerRegisterActivity
import kotlinx.coroutines.launch
import retrofit2.HttpException

/**
 * LoginActivity — Đăng nhập hợp nhất cho cả Nhân viên và Khách hàng.
 * Ưu tiên gọi API đăng nhập Staff. Nếu 401 thì gọi API đăng nhập Customer.
 */
class LoginActivity : AppCompatActivity() {

    private lateinit var etUsername:  EditText
    private lateinit var etPassword:  EditText
    private lateinit var btnLogin:    TextView
    private lateinit var tvGotoRegister: TextView
    private lateinit var tvError:     TextView
    private lateinit var progressBar: ProgressBar

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        etUsername     = findViewById(R.id.etUsername)
        etPassword     = findViewById(R.id.etPassword)
        btnLogin       = findViewById(R.id.btnLogin)
        tvGotoRegister = findViewById(R.id.tv_goto_register)
        tvError        = findViewById(R.id.tvError)
        progressBar    = findViewById(R.id.progressBar)

        // Kiểm tra đã login chưa (tự động điều hướng)
        val prefs = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val token = prefs.getString("token", "")
        if (!token.isNullOrEmpty()) {
            val role = prefs.getString("role", "")
            if (role.isNullOrEmpty()) {
                // Khách hàng không có trường role hoặc role="customer"
                startActivity(Intent(this, CustomerDashboardActivity::class.java))
            } else {
                goToRoleSelect()
            }
            finish()
            return
        }

        // Chuyển sang màn hình đăng ký nếu là khách hàng chưa có tài khoản
        tvGotoRegister.setOnClickListener {
            startActivity(Intent(this, CustomerRegisterActivity::class.java))
        }

        btnLogin.setOnClickListener { doLogin() }

        // Enter key submit
        etPassword.setOnEditorActionListener { _, _, _ ->
            doLogin(); true
        }
    }

    private fun doLogin() {
        val username = etUsername.text.toString().trim()
        val password = etPassword.text.toString()

        if (username.isEmpty() || password.isEmpty()) {
            showError("Vui lòng nhập đầy đủ thông tin")
            return
        }

        tvError.visibility = View.GONE
        setLoading(true)

        lifecycleScope.launch {
            val api = ApiClient.create(this@LoginActivity)
            try {
                // 1. Thử đăng nhập Nhân Viên
                val resp = api.login(LoginRequest(username = username, password = password))

                getSharedPreferences("gate_prefs", MODE_PRIVATE).edit()
                    .putString("token",     resp.accessToken)
                    .putString("refresh",   resp.refreshToken)
                    .putString("role",      resp.role)
                    .putString("full_name", resp.fullName)
                    .putString("gate_id",   resp.gateId ?: "")
                    .apply()

                setLoading(false)
                Toast.makeText(this@LoginActivity, "Đăng nhập Nhân viên thành công!", Toast.LENGTH_SHORT).show()
                goToRoleSelect()

            } catch (e1: Exception) {
                if (e1 is HttpException && e1.code() == 401) {
                    // 2. Không phải nhân viên, thử đăng nhập Khách Hàng
                    try {
                        val customerResp = api.loginCustomer(CustomerLoginRequest(email = username, password = password))
                        
                        getSharedPreferences("gate_prefs", MODE_PRIVATE).edit()
                            .putString("token", customerResp.accessToken)
                            .remove("role") // Đảm bảo role rỗng/null cho khách hàng
                            .remove("full_name")
                            .apply()

                        setLoading(false)
                        Toast.makeText(this@LoginActivity, "Đăng nhập Khách hàng thành công!", Toast.LENGTH_SHORT).show()
                        startActivity(Intent(this@LoginActivity, CustomerDashboardActivity::class.java))
                        finish()
                    } catch (e2: Exception) {
                        setLoading(false)
                        if (e2 is HttpException && e2.code() == 401) {
                            showError("Sai tài khoản hoặc mật khẩu")
                        } else {
                            showError("Lỗi kết nối: ${e2.message}")
                        }
                    }
                } else {
                    // Lỗi mạng, mất Internet hoặc máy chủ ngỏm
                    setLoading(false)
                    showError("Lỗi mạng hoặc máy chủ không phản hồi: ${e1.message}")
                }
            }
        }
    }

    private fun goToRoleSelect() {
        startActivity(Intent(this, RoleSelectActivity::class.java))
        finish()
    }

    private fun showError(msg: String) {
        tvError.text = msg
        tvError.visibility = View.VISIBLE
    }

    private fun setLoading(loading: Boolean) {
        btnLogin.isEnabled     = !loading
        // Nếu layout gốc khóa bấm khi loading thì ẩn hiện progress
        progressBar.visibility = if (loading) View.VISIBLE else View.GONE
    }
}
