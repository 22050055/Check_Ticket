package com.tourism.gate.ui.customer

import android.content.Intent
import android.os.Bundle
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.CustomerRegisterRequest
import com.tourism.gate.ui.LoginActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class CustomerRegisterActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_customer_register)

        val editName = findViewById<EditText>(R.id.edit_name)
        val editEmail = findViewById<EditText>(R.id.edit_email)
        val editPassword = findViewById<EditText>(R.id.edit_password)
        val btnRegister = findViewById<TextView>(R.id.btn_register)
        val tvGotoLogin = findViewById<TextView>(R.id.tv_login)

        tvGotoLogin.setOnClickListener {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }

        btnRegister.setOnClickListener {
            val name = editName.text.toString().trim()
            val email = editEmail.text.toString().trim()
            val pass = editPassword.text.toString().trim()

            if (name.isEmpty() || email.isEmpty() || pass.isEmpty()) {
                Toast.makeText(this, "Vui lòng nhập đủ thông tin", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            btnRegister.isEnabled = false
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val api = ApiClient.create(this@CustomerRegisterActivity)
                    api.registerCustomer(CustomerRegisterRequest(name, email, pass))
                    withContext(Dispatchers.Main) {
                        Toast.makeText(this@CustomerRegisterActivity, "Đăng ký thành công! Vui lòng đăng nhập.", Toast.LENGTH_SHORT).show()
                        startActivity(Intent(this@CustomerRegisterActivity, LoginActivity::class.java))
                        finish()
                    }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) {
                        btnRegister.isEnabled = true
                        Toast.makeText(this@CustomerRegisterActivity, "Lỗi đăng ký: ${e.message}", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }
    }
}
 