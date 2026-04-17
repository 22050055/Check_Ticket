package com.tourism.gate.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.google.gson.annotations.SerializedName

/**
 * Model vé điện tử — dùng cho cả API response lẫn Room local cache.
 * @SerializedName khớp với field từ backend FastAPI.
 */
@Entity(tableName = "tickets")
data class Ticket(
    @PrimaryKey
    @SerializedName("ticket_id")
    val ticketId: String,

    @SerializedName("booking_id")
    val bookingId: String? = null,

    @SerializedName("ticket_type")
    val ticketType: String,          // adult | child | student | group

    @SerializedName("price")
    val price: Double,

    @SerializedName("valid_from")
    val validFrom: String,           // ISO datetime string

    @SerializedName("valid_until")
    val validUntil: String,          // ISO datetime string

    @SerializedName("status")
    val status: String,              // active | used | revoked | expired

    @SerializedName("has_face")
    val hasFace: Boolean = false,

    @SerializedName("qr_image_b64")
    val qrImageB64: String? = null,  // chỉ có khi vừa phát hành

    @SerializedName("created_at")
    val createdAt: String? = null,

    // Cached locally — không có trên backend
    val cachedAt: Long = System.currentTimeMillis()
) {
    val isActive: Boolean get() = status == "active"
    val isExpired: Boolean get() = status == "expired"
    val isRevoked: Boolean get() = status == "revoked"

    /** Label hiển thị loại vé tiếng Việt */
    val ticketTypeLabel: String get() = when (ticketType) {
        "adult"   -> "Người lớn"
        "child"   -> "Trẻ em"
        "student" -> "Học sinh/SV"
        "group"   -> "Nhóm"
        else      -> ticketType
    }
}
 