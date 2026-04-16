package com.tourism.gate.ui.customer

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.CustomerBuyTicketRequest
import com.tourism.gate.ui.QrDisplayActivity
import kotlinx.coroutines.launch
import java.text.NumberFormat
import java.util.*

/**
 * CustomerBuyTicketActivity — Khách hàng tự mua vé online (giả lập).
 */
class CustomerBuyTicketActivity : AppCompatActivity() {

    private lateinit var btnBack:      TextView
    private lateinit var spinnerType:  Spinner
    private lateinit var tvTotalPrice: TextView
    private lateinit var btnBuy:       TextView
    private lateinit var progressBar:  ProgressBar
    private lateinit var tvError:      TextView

    private val ticketTypes    = listOf("🧑 Vé người lớn", "🧒 Vé trẻ em", "🎓 Vé học sinh/SV", "👥 Vé nhóm")
    private val ticketTypeKeys = listOf("adult", "child", "student", "group")
    private val ticketPrices   = listOf(150000L, 80000L, 100000L, 500000L)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_customer_buy_ticket)

        btnBack      = findViewById(R.id.btnBack)
        spinnerType  = findViewById(R.id.spinnerTicketType)
        tvTotalPrice = findViewById(R.id.tvTotalPrice)
        btnBuy       = findViewById(R.id.btnBuy)
        progressBar  = findViewById(R.id.progressBar)
        tvError      = findViewById(R.id.tvError)

        setupSpinner()

        btnBack.setOnClickListener { finish() }
        btnBuy.setOnClickListener  { performBuy() }
    }

    private fun setupSpinner() {
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, ticketTypes)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spinnerType.adapter = adapter

        spinnerType.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) {
                updatePriceDisplay(pos)
            }
            override fun onNothingSelected(p: AdapterView<*>?) {}
        }
    }

    private fun updatePriceDisplay(position: Int) {
        val price = ticketPrices[position]
        val formatted = NumberFormat.getNumberInstance(Locale("vi", "VN")).format(price)
        tvTotalPrice.text = "${formatted}đ"
    }

    private fun performBuy() {
        val pos = spinnerType.selectedItemPosition
        val selectedKey = ticketTypeKeys[pos]
        
        showError(null)
        setLoading(true)

        lifecycleScope.launch {
            try {
                val api = ApiClient.create(this@CustomerBuyTicketActivity)
                val req = CustomerBuyTicketRequest(
                    ticketType = selectedKey,
                    price = ticketPrices[pos].toDouble(),
                    validFrom = "", // Backend sẽ tự tính
                    validUntil = "" // Backend sẽ tự tính
                )
                
                val response = api.buyTicket(req)
                
                setLoading(false)
                Toast.makeText(this@CustomerBuyTicketActivity, "Mua vé thành công!", Toast.LENGTH_SHORT).show()
                
                // Mở màn hình hiển thị QR
                val intent = Intent(this@CustomerBuyTicketActivity, QrDisplayActivity::class.java).apply {
                    putExtra("ticket_id",    response.ticketId)
                    putExtra("qr_image_b64", response.qrImageB64)
                    flags = Intent.FLAG_ACTIVITY_FORWARD_RESULT
                }
                startActivity(intent)
                finish()
                
            } catch (e: Exception) {
                setLoading(false)
                showError("Giao dịch thất bại: ${e.message}")
            }
        }
    }

    private fun showError(msg: String?) {
        if (msg == null) {
            tvError.visibility = View.GONE
        } else {
            tvError.text = msg
            tvError.visibility = View.VISIBLE
        }
    }

    private fun setLoading(loading: Boolean) {
        btnBuy.isEnabled       = !loading
        spinnerType.isEnabled  = !loading
        progressBar.visibility = if (loading) View.VISIBLE else View.GONE
    }
}
