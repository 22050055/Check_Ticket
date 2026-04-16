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

    companion object {
        private const val RC_FACE_ENROLL = 1002
    }

    private lateinit var btnBack:      TextView
    private lateinit var spinnerType:  Spinner
    private lateinit var tvTotalPrice: TextView
    private lateinit var switchFace:   android.widget.Switch
    private lateinit var btnBuy:       TextView
    private lateinit var progressBar:  ProgressBar
    private lateinit var tvError:      TextView

    private var lastGeneratedTicketId: String? = null
    private var lastGeneratedQrB64:   String? = null

    private val ticketTypes    = listOf("🧑 Vé người lớn", "🧒 Vé trẻ em", "🎓 Vé học sinh/SV", "👥 Vé nhóm")
    private val ticketTypeKeys = listOf("adult", "child", "student", "group")
    private val ticketPrices   = listOf(150000L, 80000L, 100000L, 500000L)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_customer_buy_ticket)

        btnBack      = findViewById(R.id.btnBack)
        spinnerType  = findViewById(R.id.spinnerTicketType)
        tvTotalPrice = findViewById(R.id.tvTotalPrice)
        switchFace   = findViewById(R.id.switchFace)
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
                
                lastGeneratedTicketId = response.ticketId
                lastGeneratedQrB64    = response.qrImageB64
                
                setLoading(false)
                
                if (switchFace.isChecked) {
                    // Chuyển sang quét mặt
                    val intent = Intent(this@CustomerBuyTicketActivity, com.tourism.gate.ui.FaceEnrollActivity::class.java).apply {
                        putExtra("ticket_id", response.ticketId)
                    }
                    @Suppress("DEPRECATION")
                    startActivityForResult(intent, RC_FACE_ENROLL)
                } else {
                    Toast.makeText(this@CustomerBuyTicketActivity, "Mua vé thành công!", Toast.LENGTH_SHORT).show()
                    showQrResult(response.ticketId, response.qrImageB64)
                    finish()
                }
                
            } catch (e: Exception) {
                setLoading(false)
                showError("Giao dịch thất bại: ${e.message}")
            }
        }
    }

    private fun showQrResult(ticketId: String, qrB64: String?) {
        val intent = Intent(this, QrDisplayActivity::class.java).apply {
            putExtra("ticket_id",    ticketId)
            putExtra("qr_image_b64", qrB64)
        }
        startActivity(intent)
    }

    @Suppress("DEPRECATION")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == RC_FACE_ENROLL) {
            Toast.makeText(this, "Mua vé và đăng ký mặt thành công!", Toast.LENGTH_SHORT).show()
            showQrResult(lastGeneratedTicketId ?: "", lastGeneratedQrB64)
            finish()
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
