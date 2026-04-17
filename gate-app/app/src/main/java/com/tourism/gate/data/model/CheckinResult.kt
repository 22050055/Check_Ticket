package com.tourism.gate.data.model

import com.google.gson.annotations.SerializedName

/**
 * Request gửi lên POST /api/checkin — endpoint thống nhất mọi kênh.
 * Gate App gửi channel tương ứng, backend tự route.
 */
data class CheckinRequest(
    @SerializedName("gate_id")         val gate_id: String,
    @SerializedName("direction")       val direction: String,      // IN | OUT
    @SerializedName("channel")         val channel: String,        // QR | QR_FACE | ID | BOOKING | MANUAL

    // Kênh QR
    @SerializedName("qr_token")        val qr_token: String? = null,

    // Kênh QR_FACE
    @SerializedName("probe_image_b64") val probe_image_b64: String? = null,

    // Kênh ID
    @SerializedName("id_number")       val id_number: String? = null,

    // Kênh BOOKING
    @SerializedName("booking_id")      val booking_id: String? = null,

    // Kênh MANUAL
    @SerializedName("phone")           val phone: String? = null,
    @SerializedName("ticket_id")       val ticket_id: String? = null,
)

/**
 * Response từ POST /api/checkin — kết quả check-in/out.
 * Gate App dùng để hiển thị ResultActivity.
 */
data class CheckinResponse(
    @SerializedName("success")
    val success: Boolean,

    @SerializedName("direction")
    val direction: String,

    @SerializedName("channel")
    val channel: String,

    @SerializedName("ticket_id")
    val ticket_id: String? = null,

    @SerializedName("ticket_type")
    val ticket_type: String? = null,

    @SerializedName("customer_name")
    val customer_name: String? = null,

    @SerializedName("face_score")
    val face_score: Double? = null,   // Chỉ có khi channel = QR_FACE

    @SerializedName("message")
    val message: String,

    @SerializedName("event_id")
    val event_id: String? = null      // _id gate_event đã lưu
)

/** Request gửi lên POST /api/auth/login */
data class LoginRequest(
    @SerializedName("username") val username: String,
    @SerializedName("password") val password: String
)

/** Response từ POST /api/auth/login */
data class LoginResponse(
    @SerializedName("access_token")  val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String,
    @SerializedName("token_type")    val tokenType: String = "bearer",
    @SerializedName("role")          val role: String,
    @SerializedName("full_name")     val fullName: String,
    @SerializedName("gate_id")       val gateId: String? = null
)
 