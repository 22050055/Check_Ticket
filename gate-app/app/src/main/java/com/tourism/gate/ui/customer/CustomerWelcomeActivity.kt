package com.tourism.gate.ui.customer

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity
import com.tourism.gate.R
import com.tourism.gate.ui.LoginActivity

class CustomerWelcomeActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_customer_welcome)

        findViewById<Button>(R.id.btn_customer_portal).setOnClickListener {
            // Chuyển tới màn hình đăng nhập (Dùng chung cho cả Staff và Customer)
            startActivity(Intent(this, LoginActivity::class.java))
        }

        findViewById<Button>(R.id.btn_staff_portal).setOnClickListener {
            // Chuyển tới màn hình đăng nhập (Dùng chung cho cả Staff và Customer)
            startActivity(Intent(this, LoginActivity::class.java))
        }
    }
}
