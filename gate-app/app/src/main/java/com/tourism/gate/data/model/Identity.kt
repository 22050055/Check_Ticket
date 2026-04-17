package com.tourism.gate.data.model

import com.google.gson.annotations.SerializedName

/**
 * Model định danh — mapping 1 vé ↔ các kênh xác thực.
 * Backend không trả về CCCD gốc hay ảnh mặt — chỉ trả hash và flag.
 */
data class Identity(
    @SerializedName("ticket_id")
    val ticketId: String,

    @SerializedName("booking_id")
    val bookingId: String? = null,

    @SerializedName("has_face")
    val hasFace: Boolean = false,     // Đã đăng ký khuôn mặt opt-in chưa

    @SerializedName("created_at")
    val createdAt: String? = null
)
 