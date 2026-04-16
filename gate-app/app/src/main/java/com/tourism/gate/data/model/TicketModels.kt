package com.tourism.gate.data.model

import com.google.gson.annotations.SerializedName

// ── Ticket issue ──────────────────────────────────────────────

data class TicketIssueRequest(
    @SerializedName("customer_name")  val customerName:  String,
    @SerializedName("customer_phone") val customerPhone: String?,
    @SerializedName("ticket_type")    val ticketType:    String,
    @SerializedName("price")          val price:         Double,
    @SerializedName("valid_from")     val validFrom:     String,
    @SerializedName("valid_until")    val validUntil:    String,
    @SerializedName("payment_method") val paymentMethod: String = "cash",
    @SerializedName("booking_id")     val bookingId:     String? = null,
    @SerializedName("venue_id")       val venueId:       String = "tourism_default"
)

data class TicketIssueResponse(
    @SerializedName("ticket_id")    val ticketId:    String,
    @SerializedName("booking_id")   val bookingId:   String?,
    @SerializedName("ticket_type")  val ticketType:  String,
    @SerializedName("price")        val price:       Double,
    @SerializedName("status")       val status:      String,
    @SerializedName("has_face")     val hasFace:     Boolean,
    @SerializedName("qr_image_b64") val qrImageB64:  String?,
    @SerializedName("created_at")   val createdAt:   String
)

// ── Face enroll ───────────────────────────────────────────────

data class FaceEnrollResponse(
    @SerializedName("ticket_id")       val ticketId:      String,
    @SerializedName("embedding_dim")   val embeddingDim:  Int,
    @SerializedName("face_image_hash") val faceImageHash: String,
    @SerializedName("message")         val message:       String
)

// ── Ticket state ──────────────────────────────────────────────

/**
 * Trạng thái vé theo State Machine:
 *   OUTSIDE → Khách ở ngoài (mặc định khi phát hành)
 *   INSIDE  → Khách đang ở trong khu
 *   revoked → Vé bị thu hồi
 *   expired → Vé hết hạn
 */
object TicketStatus {
    const val OUTSIDE = "OUTSIDE"
    const val INSIDE  = "INSIDE"
    const val REVOKED = "revoked"
    const val EXPIRED = "expired"
}
