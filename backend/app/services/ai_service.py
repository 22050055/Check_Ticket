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
    Hỗ trợ đa vai trò: Admin/Staff tra cứu dashboard, Khách hàng tra cứu vé cá nhân.
    """

    def __init__(self, db: AsyncIOMotorDatabase, user_email: str = None, user_role: str = None):
        self.db = db
        self.report_service = ReportService(db)
        self.user_email = user_email
        self.user_role = user_role
        
        # Cấu hình Gemini
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        
        # Định nghĩa các Tools
        self.tools = [
            self.get_dashboard_summary,
            self.get_revenue_report,
            self.get_visitor_stats,
            self.check_ticket_status,
            self.list_gates_health,
            self.get_my_tickets,
            self.get_park_info
        ]
        
        # System Instruction thay đổi tùy theo vai trò
        role_desc = f"Bạn đang hỗ trợ người dùng có Email: {user_email} và Vai trò: {user_role}."
        instruction = (
            "Bạn là trợ lý ảo AI của Hệ thống Tourism Gate. "
            f"{role_desc} "
            "QUY TẮC BẢO MẬT: "
            "1. Nếu người dùng là 'customer', bạn CHỈ được gọi hàm get_my_tickets, get_park_info và check_ticket_status (nếu là vé của họ). "
            "KHÔNG ĐƯỢC trả lời về doanh thu, tổng số khách hoặc sức khỏe hệ thống cho khách hàng. "
            "2. Nếu người dùng là nhân viên (admin/manager/operator), bạn có quyền truy cập đầy đủ. "
            "3. Luôn trả lời bằng Tiếng Việt, thân thiện và chuyên nghiệp. Dùng bảng biểu khi cần."
        )

        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            tools=self.tools,
            system_instruction=instruction
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

    async def get_my_tickets(self) -> List[Dict[str, Any]]:
        """Lấy danh sách các vé mà khách hàng hiện tại đang sở hữu (dựa trên email)."""
        if not self.user_email:
            return {"error": "Không xác định được danh tính người dùng."}
            
        cursor = self.db["tickets"].find({"customer_email": self.user_email}).sort("created_at", -1)
        tickets = await cursor.to_list(length=50)
        
        return [
            {
                "ticket_id": str(t["_id"]),
                "type": t.get("ticket_type"),
                "status": t.get("status"),
                "valid_until": t.get("valid_until").isoformat() if t.get("valid_until") else None,
                "has_face": t.get("has_face", False)
            } for t in tickets
        ]

    async def get_park_info(self) -> Dict[str, Any]:
        """Lấy thông tin chung về khu du lịch: giờ mở cửa, các khu vực, và hướng dẫn sử dụng app."""
        return {
            "name": "Khu du lịch Tourism Gate",
            "opening_hours": "07:30 - 17:30 hàng ngày",
            "zones": ["Khu vui chơi cảm giác mạnh", "Vườn thú Safari", "Công viên nước", "Khu ẩm thực"],
            "features": "Hệ thống sử dụng vé điện tử (QR Code) và xác thực khuôn mặt (FaceID) tại cổng soát vé.",
            "instructions": [
                "1. Bạn có thể mua vé trực tiếp trên ứng dụng.",
                "2. Sau khi mua, hãy vào 'Vé của tôi' để lấy mã QR.",
                "3. Bạn nên đăng ký khuôn mặt để qua cổng nhanh hơn mà không cần đưa điện thoại."
            ]
        }

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
                    "get_my_tickets":        self.get_my_tickets,
                    "get_park_info":         self.get_park_info
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
