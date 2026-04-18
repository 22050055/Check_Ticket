package com.tourism.gate.ui.customer

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.CustomerBuyTicketRequest
import com.tourism.gate.ui.QrDisplayActivity
import kotlinx.coroutines.launch
import java.text.NumberFormat
import java.util.*

class BuyFragment : Fragment() {

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

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View? {
        val view = inflater.inflate(R.layout.fragment_buy, container, false)
        
        spinnerType  = view.findViewById(R.id.spinnerTicketType)
        tvTotalPrice = view.findViewById(R.id.tvTotalPrice)
        switchFace   = view.findViewById(R.id.switchFace)
        btnBuy       = view.findViewById(R.id.btnBuy)
        progressBar  = view.findViewById(R.id.progressBar)
        tvError      = view.findViewById(R.id.tvError)

        setupSpinner()
        btnBuy.setOnClickListener { performBuy() }
        
        return view
    }

    private fun setupSpinner() {
        val adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_item, ticketTypes)
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
                val api = ApiClient.create(requireContext())
                val req = CustomerBuyTicketRequest(
                    ticketType = selectedKey,
                    price = ticketPrices[pos].toDouble(),
                    validFrom = "",
                    validUntil = ""
                )
                
                val response = api.buyTicket(req)
                lastGeneratedTicketId = response.ticketId
                lastGeneratedQrB64    = response.qrImageB64
                setLoading(false)
                
                if (switchFace.isChecked) {
                    val intent = Intent(requireContext(), com.tourism.gate.ui.FaceEnrollActivity::class.java).apply {
                        putExtra("ticket_id", response.ticketId)
                    }
                    startActivityForResult(intent, 1002)
                } else {
                    Toast.makeText(context, "Mua vé thành công!", Toast.LENGTH_SHORT).show()
                    showQrResult(response.ticketId, response.qrImageB64)
                }
                
            } catch (e: Exception) {
                setLoading(false)
                showError("Giao dịch thất bại: ${e.message}")
            }
        }
    }

    private fun showQrResult(ticketId: String, qrB64: String?) {
        val intent = Intent(requireContext(), QrDisplayActivity::class.java).apply {
            putExtra("ticket_id",    ticketId)
            putExtra("qr_image_b64", qrB64)
        }
        startActivity(intent)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 1002) {
            showQrResult(lastGeneratedTicketId ?: "", lastGeneratedQrB64)
        }
    }

    private fun showError(msg: String?) {
        tvError.text = msg
        tvError.visibility = if (msg == null) View.GONE else View.VISIBLE
    }

    private fun setLoading(loading: Boolean) {
        btnBuy.isEnabled       = !loading
        spinnerType.isEnabled  = !loading
        progressBar.visibility = if (loading) View.VISIBLE else View.GONE
    }
}
