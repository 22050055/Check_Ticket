package com.tourism.gate.ui.customer

import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.tourism.gate.R
import com.tourism.gate.data.model.CustomerTicket
import java.text.NumberFormat
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

class CustomerTicketAdapter(
    private val context: Context,
    private val tickets: List<CustomerTicket>,
    private val onDownloadQr: (ticket: CustomerTicket) -> Unit,
    private val onEnrollFace: (ticket: CustomerTicket) -> Unit,
    private val onReview: (ticket: CustomerTicket) -> Unit,
    private val onCancel: (ticket: CustomerTicket) -> Unit
) : RecyclerView.Adapter<CustomerTicketAdapter.TicketViewHolder>() {

    inner class TicketViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvTicketType: TextView  = view.findViewById(R.id.tv_ticket_type)
        val tvBookingId: TextView   = view.findViewById(R.id.tv_booking_id)
        val tvStatus: TextView      = view.findViewById(R.id.tv_status)
        val tvValidFrom: TextView   = view.findViewById(R.id.tv_valid_from)
        val tvValidUntil: TextView  = view.findViewById(R.id.tv_valid_until)
        val tvPrice: TextView       = view.findViewById(R.id.tv_price)
        val btnDownloadQr: TextView = view.findViewById(R.id.btn_download_qr)
        val btnEnrollFace: TextView = view.findViewById(R.id.btn_enroll_face)
        val btnCancelTicket: TextView = view.findViewById(R.id.btn_cancel_ticket)
        val btnReview: TextView     = view.findViewById(R.id.btn_review)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): TicketViewHolder {
        val view = LayoutInflater.from(context).inflate(R.layout.item_customer_ticket, parent, false)
        return TicketViewHolder(view)
    }

    override fun onBindViewHolder(holder: TicketViewHolder, position: Int) {
        val ticket = tickets[position]

        // Loại vé (viết hoa chữ đầu)
        holder.tvTicketType.text = when (ticket.ticketType.lowercase()) {
            "adult"   -> "🧑 Vé người lớn"
            "child"   -> "🧒 Vé trẻ em"
            "student" -> "🎓 Vé học sinh"
            "senior"  -> "👴 Vé người cao tuổi"
            "vip"     -> "⭐ Vé VIP"
            else      -> "🎫 ${ticket.ticketType}"
        }

        // Booking ID
        holder.tvBookingId.text = if (!ticket.bookingId.isNullOrBlank())
            "#${ticket.bookingId}" else "#${ticket.ticketId.take(8).uppercase()}"

        // Trạng thái
        when (ticket.status.lowercase()) {
            "active"  -> {
                holder.tvStatus.text = "Còn hiệu lực"
                holder.tvStatus.setBackgroundResource(R.drawable.bg_badge_active)
            }
            "used", "inside", "outside" -> {
                holder.tvStatus.text = "Đã sử dụng"
                holder.tvStatus.setBackgroundResource(R.drawable.bg_badge_used)
            }
            "revoked" -> {
                holder.tvStatus.text = "Đã hủy (Hoàn 50%)"
                holder.tvStatus.setBackgroundResource(R.drawable.bg_badge_revoked)
            }
            "expired" -> {
                val dateStr = formatDate(ticket.validUntil)
                holder.tvStatus.text = "Hết hạn ngày $dateStr"
                holder.tvStatus.setBackgroundResource(R.drawable.bg_badge_revoked)
            }
            else -> holder.tvStatus.text = ticket.status
        }

        // Ngày tháng
        holder.tvValidFrom.text  = formatDate(ticket.validFrom)
        holder.tvValidUntil.text = formatDate(ticket.validUntil)

        // Giá tiền
        val priceFormatted = NumberFormat.getNumberInstance(Locale("vi", "VN"))
            .format(ticket.price.toLong())
        holder.tvPrice.text = "${priceFormatted}đ"

        // Nút đăng ký mặt: ẩn hiện phù hợp
        if (ticket.hasFace) {
            holder.btnEnrollFace.text = "✅  Đã đăng ký mặt"
            holder.btnEnrollFace.alpha = 0.6f
        } else {
            holder.btnEnrollFace.text = "🤳  Đăng ký mặt"
            holder.btnEnrollFace.alpha = 1.0f
        }

        // ── Logic Đánh giá ──
        val isUsedOrExpired = ticket.status.lowercase() in listOf("used", "inside", "outside", "expired")
        if (isUsedOrExpired) {
            holder.btnReview.visibility     = View.VISIBLE
            holder.btnDownloadQr.visibility = View.GONE
            holder.btnEnrollFace.visibility = View.GONE
        } else {
            holder.btnReview.visibility     = View.GONE
            holder.btnDownloadQr.visibility = View.VISIBLE
            holder.btnEnrollFace.visibility = View.VISIBLE
            
            // Chỉ cho phép hủy nếu là vé "active" (chưa dùng)
            if (ticket.status.lowercase() == "active") {
                holder.btnCancelTicket.visibility = View.VISIBLE
            } else {
                holder.btnCancelTicket.visibility = View.GONE
            }
        }

        // Sự kiện bấm nút
        holder.btnDownloadQr.setOnClickListener { onDownloadQr(ticket) }
        holder.btnEnrollFace.setOnClickListener  { onEnrollFace(ticket) }
        holder.btnCancelTicket.setOnClickListener { onCancel(ticket) }
        holder.btnReview.setOnClickListener     { onReview(ticket) }
    }

    override fun getItemCount() = tickets.size

    // ── Format ISO datetime → "dd/MM/yyyy" ──────────────────────
    private fun formatDate(iso: String?): String {
        if (iso.isNullOrBlank()) return "-"
        return try {
            val isoFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
            isoFormat.timeZone = TimeZone.getTimeZone("UTC")
            val date = isoFormat.parse(iso) ?: return iso.take(10)
            SimpleDateFormat("dd/MM/yyyy", Locale.getDefault()).format(date)
        } catch (e: Exception) {
            iso.take(10)  // fallback: lấy 10 ký tự đầu "yyyy-MM-dd"
        }
    }
}
 