package com.tourism.gate.data.api

import com.tourism.gate.data.model.*
import retrofit2.http.*

/**
 * ApiService — Retrofit interface cho tất cả endpoints.
 */
interface ApiService {

    // ── Auth ──────────────────────────────────────────────
    @POST("api/auth/login")
    suspend fun login(@Body req: LoginRequest): LoginResponse

    // ── Tickets ───────────────────────────────────────────
    @POST("api/tickets")
    suspend fun issueTicket(@Body req: TicketIssueRequest): TicketIssueResponse

    @GET("api/tickets/{id}")
    suspend fun getTicket(@Path("id") ticketId: String): TicketIssueResponse

    // ── Face ──────────────────────────────────────────────
    @POST("api/face/enroll")
    suspend fun enrollFace(@Body req: Map<String, @JvmSuppressWildcards Any>): FaceEnrollResponse

    // ── Check-in/out ──────────────────────────────────────
    @POST("api/checkin")
    suspend fun checkin(@Body req: CheckinRequest): CheckinResponse

    // ── Gates ─────────────────────────────────────────────
    @GET("api/gates")
    suspend fun listGates(): List<Gate>

    // ── Customer Mode ─────────────────────────────────────
    @POST("api/customer/register")
    suspend fun registerCustomer(@Body req: CustomerRegisterRequest): CustomerResponse

    @POST("api/customer/login")
    suspend fun loginCustomer(@Body req: CustomerLoginRequest): TokenResponse

    @GET("api/customer/tickets")
    suspend fun getCustomerTickets(): List<TicketIssueResponse>

    @POST("api/customer/tickets/{id}/enroll-face")
    suspend fun enrollCustomerFace(
        @Path("id") ticketId: String,
        @Body req: Map<String, @JvmSuppressWildcards Any>
    ): FaceEnrollResponse

}
