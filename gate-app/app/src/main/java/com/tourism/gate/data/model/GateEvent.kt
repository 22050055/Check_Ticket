package com.tourism.gate.data.model

import com.google.gson.annotations.SerializedName

/**
 * Model sự kiện check-in/out — tương ứng collection gate_events trên MongoDB.
 */
data class GateEvent(
    @SerializedName("event_id")
    val eventId: String,

    @SerializedName("ticket_id")
    val ticketId: String? = null,

    @SerializedName("ticket_type")
    val ticketType: String? = null,

    @SerializedName("gate_id")
    val gateId: String,

    @SerializedName("direction")
    val direction: String,            // IN | OUT

    @SerializedName("channel")
    val channel: String,              // QR | QR_FACE | ID | BOOKING | MANUAL

    @SerializedName("result")
    val result: String,               // SUCCESS | FAIL

    @SerializedName("fail_reason")
    val failReason: String? = null,

    @SerializedName("face_score")
    val faceScore: Double? = null,    // Cosine similarity — chỉ có khi QR_FACE

    @SerializedName("created_at")
    val createdAt: String
) {
    val isSuccess: Boolean get() = result == "SUCCESS"
    val isIn: Boolean      get() = direction == "IN"

    /** Label kênh hiển thị */
    val channelLabel: String get() = when (channel) {
        "QR"      -> "Mã QR"
        "QR_FACE" -> "QR + Khuôn mặt"
        "ID"      -> "CCCD/ID"
        "BOOKING" -> "Booking ID"
        "MANUAL"  -> "Thủ công"
        else      -> channel
    }
}

/** Response từ GET /api/gates/{id}/events */
data class GateEventsResponse(
    @SerializedName("gate_id") val gateId: String,
    @SerializedName("count")   val count: Int,
    @SerializedName("events")  val events: List<GateEvent>
)

/** Model cổng ra/vào */
data class Gate(
    @SerializedName("gate_id")   val gate_id: String,
    @SerializedName("gate_code") val gate_code: String,
    @SerializedName("name")      val name: String,
    @SerializedName("location")  val location: String? = null,
    @SerializedName("is_active") val isActive: Boolean = true
)
