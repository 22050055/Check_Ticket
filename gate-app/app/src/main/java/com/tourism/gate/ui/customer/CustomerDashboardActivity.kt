package com.tourism.gate.ui.customer

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class CustomerDashboardActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // val recyclerView = findViewById<RecyclerView>(R.id.recycler_tickets)
        // ... (Tiến hành map layout)
        
        loadTickets()
    }

    private fun loadTickets() {
        val api = ApiClient.create(this)
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val tickets = api.getCustomerTickets()
                withContext(Dispatchers.Main) {
                    if (tickets.isEmpty()) {
                        Toast.makeText(this@CustomerDashboardActivity, "Bạn chưa mua vé nào.", Toast.LENGTH_SHORT).show()
                    } else {
                        Toast.makeText(this@CustomerDashboardActivity, "Tải thành công ${tickets.size} vé", Toast.LENGTH_SHORT).show()
                        // Update Adapter
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@CustomerDashboardActivity, "Lỗi tải vé: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }
}
