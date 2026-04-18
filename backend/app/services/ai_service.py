import logging
import json
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone, timedelta

from ..core.config import settings
from .report_service import ReportService
from ..api.tickets import _auto_cleanup_expired_tickets

logger = logging.getLogger(__name__)

class AiService:
    """
    Dịch vụ Trợ lý ảo AI (Gemini) tích hợp RAG và Function Calling.
    Có khả năng truy vấn Database thông qua ReportService.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.report_service = ReportService(db)
        
        # Cấu hình Gemini
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        
        # Định nghĩa các Tools (Function Declarations)
        self.tools = [
            self.get_dashboard_summary,
            self.get_revenue_report,
            self.get_visitor_stats,
            self.check_ticket_status,
            self.list_gates_health
        ]
        
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            tools=self.tools,
            system_instruction=(
                "Bạn là trợ lý ảo AI của Hệ thống quản lý vé du lịch Tourism Gate. "
                "Hệ thống bao gồm Dashboard web, App cổng soát vé (Android) và App khách hàng. "
                "Bạn có quyền truy cập vào dữ liệu hệ thống để trả lời các câu hỏi về doanh thu, lượt khách, trạng thái vé và thiết bị cổng. "
                "Hãy trả lời chuyên nghiệp, ngắn gọn và hữu ích. "
                "Nếu bạn không chắc chắn hoặc không có tool cung cấp thông tin, hãy nói rõ. "
                "Luôn ưu tiên dùng bảng biểu (Markdown table) khi trả lời về số liệu."
            )
        )

    # ── Tools for Gemini ────────────────────────────────────────

    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Lấy thông số tổng quan của dashboard hôm nay (doanh thu, lượt khách, tỷ lệ lỗi)."""
        return await self.report_service.get_realtime_stats()

    async def get_revenue_report(self, days: int = 7) -> Dict[str, Any]:
        """Lấy báo cáo doanh thu trong số ngày gần đây (mặc định 7 ngày)."""
        now = datetime.now(timezone.utc)
        d_from = now - timedelta(days=days)
        return await self.report_service.get_revenue(d_from, now)

    async def get_visitor_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Lấy thống kê lượt khách vào/ra trong số giờ gần đây (mặc định 24h)."""
        now = datetime.now(timezone.utc)
        d_from = now - timedelta(hours=hours)
        return await self.report_service.get_visitors(d_from, now)

    async def check_ticket_status(self, ticket_id: str) -> Dict[str, Any]:
        """Kiểm tra chi tiết trạng thái của một mã vé cụ thể (active, expired, used, revoked)."""
        # Cleanup trước khi check
        await _auto_cleanup_expired_tickets(self.db)
        ticket = await self.db["tickets"].find_one({"_id": ticket_id})
        if not ticket:
            return {"error": "Không tìm thấy vé."}
        
        return {
            "ticket_id": str(ticket["_id"]),
            "status": ticket.get("status"),
            "type": ticket.get("ticket_type"),
            "valid_until": ticket.get("valid_until").isoformat() if ticket.get("valid_until") else None,
            "issued_by": ticket.get("issued_by_name")
        }

    async def list_gates_health(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả các cổng và trạng thái hoạt động gần nhất của chúng."""
        stats = await self.report_service.get_realtime_stats()
        return stats.get("gates_status", [])

    # ── Logic xử lý Chat ────────────────────────────────────────

    async def chat(self, user_message: str, history: List[Dict[str, str]] = None) -> str:
        """
        Xử lý tin nhắn từ người dùng, thực hiện function calling nếu cần.
        """
        chat = self.model.start_chat(history=history or [])
        
        try:
            # Gửi tin nhắn đầu tiên
            response = chat.send_message(user_message)
            
            # Xử lý Function Calling (nếu Gemini yêu cầu)
            # Gemini-python SDK tự động handle việc gọi hàm nếu model được khởi tạo với tools
            # và sử dụng helper `enable_automatic_function_calling=True` (hoặc mặc định trong start_chat)
            
            # Tuy nhiên, do chúng ta dùng async-motor, chúng ta sẽ handle thủ công 
            # hoặc đảm bảo các tool function là đồng bộ nếu model yêu cầu.
            # Trong FastAPI, chúng ta sẽ bắt các call part và thực hiện await.
            
            while response.parts[0].function_call:
                fc = response.parts[0].function_call
                fn_name = fc.name
                fn_args = fc.args
                
                logger.info(f"AI Assistant call function: {fn_name} with {fn_args}")
                
                # Ánh xạ hàm
                fn_map = {
                    "get_dashboard_summary": self.get_dashboard_summary,
                    "get_revenue_report":    self.get_revenue_report,
                    "get_visitor_stats":     self.get_visitor_stats,
                    "check_ticket_status":   self.check_ticket_status,
                    "list_gates_health":     self.list_gates_health,
                }
                
                if fn_name in fn_map:
                    # Gọi hàm async
                    result = await fn_map[fn_name](**fn_args)
                    # Gửi kết quả lại cho AI
                    response = chat.send_message(
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=fn_name,
                                    response={"result": result}
                                )
                            )]
                        )
                    )
                else:
                    break

            return response.text

        except Exception as e:
            logger.error(f"AiService.chat error: {e}")
            return f"Xin lỗi, tôi gặp lỗi hệ thống: {str(e)}"
