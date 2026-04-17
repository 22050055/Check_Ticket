package com.tourism.gate.utils

import android.util.Base64
import org.json.JSONObject

/**
 * QrParser — Parse và validate payload JWT từ mã QR.
 *
 * QR token là JWT RS256 có cấu trúc: header.payload.signature
 * Payload chứa:
 *   jti  — JWT ID (nonce, dùng anti-reuse)
 *   sub  — ticket_id
 *   tid  — ticket_type (adult | child | student | group)
 *   vid  — venue_id
 *   iat  — issued at (unix timestamp)
 *   exp  — expiry (unix timestamp)
 *
 * Lưu ý: QrParser KHÔNG verify chữ ký RS256 — việc đó do backend làm.
 * Parser chỉ decode để hiển thị thông tin nhanh hoặc check offline cơ bản.
 */
object QrParser {

    // ── Data class kết quả parse ──────────────────────────

    data class QrPayload(
        val jti:       String,          // JWT ID — nonce anti-reuse
        val ticketId:  String,          // sub — ticket_id trong DB
        val ticketType: String,         // tid — loại vé
        val venueId:   String,          // vid — khu du lịch
        val issuedAt:  Long,            // iat — unix seconds
        val expiry:    Long,            // exp — unix seconds
        val rawToken:  String           // JWT gốc để gửi lên server
    ) {
        /** Vé còn hạn theo thời gian client (không verify sig) */
        val isExpiredLocally: Boolean
            get() = System.currentTimeMillis() / 1000 > expiry

        /** Thời gian còn lại (giây) */
        val remainingSeconds: Long
            get() = maxOf(0, expiry - System.currentTimeMillis() / 1000)

        /** Label loại vé tiếng Việt */
        val ticketTypeLabel: String get() = when (ticketType) {
            "adult"   -> "Người lớn"
            "child"   -> "Trẻ em"
            "student" -> "Học sinh/SV"
            "group"   -> "Nhóm"
            else      -> ticketType
        }
    }

    sealed class ParseResult {
        data class Success(val payload: QrPayload) : ParseResult()
        data class Invalid(val reason: String)    : ParseResult()
    }

    // ── Parse ─────────────────────────────────────────────

    /**
     * Parse chuỗi QR — có thể là JWT hoặc plain text.
     *
     * @param rawValue  Giá trị thô từ ML Kit barcode scanner
     * @return ParseResult.Success hoặc ParseResult.Invalid
     */
    fun parse(rawValue: String): ParseResult {
        val trimmed = rawValue.trim()
        if (trimmed.isEmpty()) return ParseResult.Invalid("QR rỗng")

        // JWT phải có đúng 3 phần ngăn bởi dấu chấm
        val parts = trimmed.split(".")
        if (parts.size != 3) return ParseResult.Invalid("Không phải định dạng QR hợp lệ")

        return try {
            val payload = decodePayload(parts[1])
                ?: return ParseResult.Invalid("Không decode được payload")

            val jti       = payload.optString("jti")
            val ticketId  = payload.optString("sub")
            val ticketType = payload.optString("tid")
            val venueId   = payload.optString("vid", "tourism_default")
            val iat       = payload.optLong("iat", 0L)
            val exp       = payload.optLong("exp", 0L)

            if (jti.isEmpty())      return ParseResult.Invalid("Thiếu trường jti (nonce)")
            if (ticketId.isEmpty()) return ParseResult.Invalid("Thiếu trường sub (ticket_id)")
            if (exp == 0L)          return ParseResult.Invalid("Thiếu trường exp (expiry)")

            ParseResult.Success(
                QrPayload(
                    jti        = jti,
                    ticketId   = ticketId,
                    ticketType = ticketType.ifEmpty { "adult" },
                    venueId    = venueId,
                    issuedAt   = iat,
                    expiry     = exp,
                    rawToken   = trimmed
                )
            )
        } catch (e: Exception) {
            ParseResult.Invalid("Lỗi parse: ${e.message}")
        }
    }

    /**
     * Parse nhanh — trả null nếu không hợp lệ.
     * Dùng trong ScanViewModel để xử lý nhanh.
     */
    fun parseOrNull(rawValue: String): QrPayload? =
        (parse(rawValue) as? ParseResult.Success)?.payload

    // ── Field extractors (dùng trong ViewModel không cần full parse) ──

    fun extractJti(jwt: String): String       = extractField(jwt, "jti")
    fun extractTicketId(jwt: String): String  = extractField(jwt, "sub")
    fun extractTicketType(jwt: String): String = extractField(jwt, "tid")
    fun extractExpiry(jwt: String): Long {
        return try {
            val payload = decodePayload(jwt.split(".").getOrElse(1) { "" })
            payload?.optLong("exp", 0L) ?: 0L
        } catch (_: Exception) { 0L }
    }

    // ── Helpers ───────────────────────────────────────────

    private fun decodePayload(base64Segment: String): JSONObject? {
        return try {
            // Padding JWT base64url
            val padded  = base64Segment.padEnd((base64Segment.length + 3) / 4 * 4, '=')
            val decoded = Base64.decode(padded, Base64.URL_SAFE or Base64.NO_WRAP)
            JSONObject(String(decoded, Charsets.UTF_8))
        } catch (_: Exception) { null }
    }

    private fun extractField(jwt: String, field: String): String {
        val payload = decodePayload(jwt.split(".").getOrElse(1) { "" }) ?: return ""
        return payload.optString(field, "")
    }

    /**
     * Kiểm tra chuỗi có phải JWT hợp lệ (3 phần, phần giữa decode được).
     */
    fun isValidJwt(value: String): Boolean {
        val parts = value.trim().split(".")
        if (parts.size != 3) return false
        return decodePayload(parts[1]) != null
    }
}
 