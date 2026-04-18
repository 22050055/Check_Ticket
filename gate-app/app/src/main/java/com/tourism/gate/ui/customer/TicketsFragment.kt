package com.tourism.gate.ui.customer

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.lifecycle.lifecycleScope
import com.google.gson.JsonParser
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.CustomerTicket
import com.tourism.gate.ui.QrDisplayActivity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class TicketsFragment : Fragment() {

    private lateinit var tvTicketCount:   TextView
    private lateinit var progressBar:     ProgressBar
    private lateinit var layoutEmpty:     View
    private lateinit var recyclerTickets: RecyclerView

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View? {
        val view = inflater.inflate(R.layout.fragment_tickets, container, false)
        
        tvTicketCount   = view.findViewById(R.id.tv_ticket_count)
        progressBar     = view.findViewById(R.id.progressBar)
        layoutEmpty     = view.findViewById(R.id.layout_empty)
        recyclerTickets = view.findViewById(R.id.recycler_tickets)

        recyclerTickets.layoutManager = LinearLayoutManager(requireContext())
        
        loadTickets()
        return view
    }

    private fun loadTickets() {
        showLoading(true)
        val api = ApiClient.create(requireContext())
        viewLifecycleOwner.lifecycleScope.launch {
            try {
                val tickets = withContext(Dispatchers.IO) { api.getCustomerTickets() }
                if (!isAdded) return@launch
                
                showLoading(false)
                if (tickets.isEmpty()) {
                    showEmpty(true)
                } else {
                    showEmpty(false)
                    tvTicketCount.text = "${tickets.size} vé đang sở hữu"
                    setupAdapter(tickets)
                }
            } catch (e: Exception) {
                if (!isAdded) return@launch
                showLoading(false)
                showEmpty(true)
                Toast.makeText(context, "Lỗi tải danh sách vé: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun setupAdapter(tickets: List<CustomerTicket>) {
        val adapter = CustomerTicketAdapter(
            context = requireContext(),
            tickets = tickets,
            onDownloadQr = { ticket -> downloadQr(ticket) },
            onEnrollFace = { ticket -> enrollFace(ticket) },
            onReview     = { ticket -> showReviewDialog(ticket) },
            onCancel     = { ticket -> showCancelConfirmation(ticket) }
        )
        recyclerTickets.adapter = adapter
        recyclerTickets.visibility = View.VISIBLE
    }

    private fun downloadQr(ticket: CustomerTicket) {
        Toast.makeText(context, "Đang tải mã QR vé #${ticket.ticketId.take(8)}...", Toast.LENGTH_SHORT).show()
        val api = ApiClient.create(requireContext())
        viewLifecycleOwner.lifecycleScope.launch {
            try {
                val response = withContext(Dispatchers.IO) { api.downloadCustomerQr(ticket.ticketId) }
                val qrBytes = response.bytes()
                if (!isAdded) return@launch
                
                val intent = Intent(requireContext(), QrDisplayActivity::class.java)
                intent.putExtra("qr_bytes", qrBytes)
                intent.putExtra("ticket_id", ticket.ticketId)
                startActivity(intent)
            } catch (e: Exception) {
                if (!isAdded) return@launch
                Toast.makeText(context, "Lỗi tải QR: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun enrollFace(ticket: CustomerTicket) {
        if (ticket.hasFace) {
            Toast.makeText(context, "Vé này đã đăng ký khuôn mặt rồi!", Toast.LENGTH_SHORT).show()
            return
        }
        val intent = Intent(requireContext(), com.tourism.gate.ui.FaceEnrollActivity::class.java)
        intent.putExtra("ticket_id", ticket.ticketId)
        intent.putExtra("mode", "customer")
        startActivity(intent)
    }

    private fun showReviewDialog(ticket: CustomerTicket) {
        val dialogView = layoutInflater.inflate(R.layout.dialog_review, null)
        val ratingBar = dialogView.findViewById<android.widget.RatingBar>(R.id.ratingBar)
        val edtComment = dialogView.findViewById<android.widget.EditText>(R.id.edt_comment)

        AlertDialog.Builder(requireContext())
            .setTitle("Đánh giá dịch vụ")
            .setView(dialogView)
            .setPositiveButton("Gửi đánh giá") { _, _ ->
                val rating = ratingBar.rating.toInt()
                val comment = edtComment.text.toString().trim()
                submitReview(ticket.ticketId, rating, comment)
            }
            .setNegativeButton("Bỏ qua", null)
            .show()
    }

    private fun submitReview(ticketId: String, rating: Int, comment: String) {
        if (rating == 0) {
            Toast.makeText(context, "Vui lòng chọn số sao!", Toast.LENGTH_SHORT).show()
            return
        }
        val api = ApiClient.create(requireContext())
        viewLifecycleOwner.lifecycleScope.launch {
            try {
                withContext(Dispatchers.IO) { 
                    api.reviewTicket(ticketId, com.tourism.gate.data.model.ReviewRequest(rating, comment))
                }
                if (!isAdded) return@launch
                
                Toast.makeText(context, "Cảm ơn bạn đã đánh giá!", Toast.LENGTH_SHORT).show()
                loadTickets()
            } catch (e: Exception) {
                if (!isAdded) return@launch
                val errorMsg = try {
                    if (e is retrofit2.HttpException) {
                        val errorBody = e.response()?.errorBody()?.string()
                        if (errorBody != null) {
                            val json = JsonParser.parseString(errorBody).asJsonObject
                            json.get("detail").asString
                        } else {
                            e.message ?: "Lỗi không xác định"
                        }
                    } else {
                        e.message ?: "Lỗi không xác định"
                    }
                } catch (ex: Exception) {
                    e.message ?: "Lỗi kết nối"
                }
                Toast.makeText(context, "Lỗi gửi đánh giá: $errorMsg", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun showCancelConfirmation(ticket: CustomerTicket) {
        AlertDialog.Builder(requireContext())
            .setTitle("Xác nhận hủy vé")
            .setMessage("Bạn có chắc chắn muốn hủy vé? Hệ thống chỉ có thể hoàn 50% số tiền.")
            .setPositiveButton("Chắc chắn hủy") { _, _ ->
                performCancelTicket(ticket.ticketId)
            }
            .setNegativeButton("Quay lại", null)
            .show()
    }

    private fun performCancelTicket(ticketId: String) {
        showLoading(true)
        val api = ApiClient.create(requireContext())
        viewLifecycleOwner.lifecycleScope.launch {
            try {
                withContext(Dispatchers.IO) { api.cancelTicket(ticketId) }
                if (!isAdded) return@launch
                
                showLoading(false)
                Toast.makeText(context, "Đã hủy vé thành công. Hoàn tiền 50% đang được xử lý.", Toast.LENGTH_LONG).show()
                loadTickets() // Tải lại danh sách
            } catch (e: Exception) {
                if (!isAdded) return@launch
                showLoading(false)
                Toast.makeText(context, "Lỗi hủy vé: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun showLoading(loading: Boolean) {
        progressBar.visibility = if (loading) View.VISIBLE else View.GONE
    }

    private fun showEmpty(empty: Boolean) {
        layoutEmpty.visibility     = if (empty) View.VISIBLE else View.GONE
        recyclerTickets.visibility = if (empty) View.GONE    else View.VISIBLE
    }
}
