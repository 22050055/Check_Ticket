package com.tourism.gate.data.model

import com.google.gson.annotations.SerializedName

data class CustomerRegisterRequest(
    @SerializedName("name") val name: String,
    @SerializedName("email") val email: String,
    @SerializedName("password") val password: String
)

data class CustomerLoginRequest(
    @SerializedName("email") val email: String,
    @SerializedName("password") val password: String
)

data class CustomerResponse(
    @SerializedName("id") val id: String,
    @SerializedName("name") val name: String,
    @SerializedName("email") val email: String
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String
)

data class CustomerBuyTicketRequest(
    @SerializedName("ticket_type") val ticketType: String,
    @SerializedName("price") val price: Double,
    @SerializedName("valid_from") val validFrom: String,
    @SerializedName("valid_until") val validUntil: String
)

// Response từ GET /api/customer/tickets
data class CustomerTicket(
    @SerializedName("ticket_id")   val ticketId:   String,
    @SerializedName("booking_id")  val bookingId:  String?,
    @SerializedName("ticket_type") val ticketType: String,
    @SerializedName("price")       val price:      Double,
    @SerializedName("valid_from")  val validFrom:  String?,
    @SerializedName("valid_until") val validUntil: String?,
    @SerializedName("status")      val status:     String,
    @SerializedName("venue_id")    val venueId:    String?,
    @SerializedName("has_face")    val hasFace:    Boolean,
    @SerializedName("created_at")  val createdAt:  String?
)
