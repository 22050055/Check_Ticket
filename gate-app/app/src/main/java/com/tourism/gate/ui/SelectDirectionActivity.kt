package com.tourism.gate.ui

import android.content.Intent
import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.tourism.gate.R

class SelectDirectionActivity : AppCompatActivity() {

    private lateinit var btnBack: TextView
    private lateinit var btnHome: TextView
    private lateinit var btnIn: TextView
    private lateinit var btnOut: TextView
    private lateinit var btnChangeGate: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_select_direction)

        btnBack       = findViewById(R.id.btnBack)
        btnHome       = findViewById(R.id.btnHome)
        btnIn         = findViewById(R.id.btnIn)
        btnOut        = findViewById(R.id.btnOut)
        btnChangeGate = findViewById(R.id.btnChangeGate)

        val prefs    = getSharedPreferences("gate_prefs", MODE_PRIVATE)

        btnBack.setOnClickListener { finish() }
        btnHome.setOnClickListener {
            val intent = Intent(this, RoleSelectActivity::class.java)
            intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)
            startActivity(intent)
        }

        btnIn.setOnClickListener {
            saveDirectionAndGo("IN")
        }

        btnOut.setOnClickListener {
            saveDirectionAndGo("OUT")
        }

        btnChangeGate.setOnClickListener {
            startActivity(Intent(this, GateSelectActivity::class.java))
            finish()
        }
    }

    private fun saveDirectionAndGo(direction: String) {
        getSharedPreferences("gate_prefs", MODE_PRIVATE)
            .edit().putString("direction", direction).apply()

        // Mở ScanActivity để quét QR
        startActivity(Intent(this, ScanActivity::class.java))
    }
}
 