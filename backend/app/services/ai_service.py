import logging
from typing import Dict, List, Any
from google import genai
from google.genai import types
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

    def __init__(self, db: AsyncIOMotorDatabase, user_email: str = None, user_role: str = None, user_name: str = None, model_name: str = None):
        self.db = db
        self.report_service = ReportService(db)
        self.user_email = user_email
        self.user_role = user_role
        self.user_name = user_name or "người dùng"
        self.model_name = model_name or settings.AI_MODEL_NAME
        
        # 1. Khởi tạo Client mới (chuẩn v1.0+)
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        # 2. Định nghĩa System Instruction
        # Phân quyền rõ rệt trong Prompt và dặn AI thông minh hơn về ngữ cảnh
        perm_desc = ""
        if user_role in ["admin", "manager"]:
            perm_desc = "Bạn là Admin/Manager: Có quyền xem báo cáo doanh thu, lượt khách và dashboard."
        elif user_role in ["operator", "cashier"]:
            perm_desc = "Bạn là Nhân viên: Có quyền tra cứu trạng thái vé và thông tin cổng."
        else:
            perm_desc = "Bạn là Khách hàng: Chỉ được xem vé của chính mình. Tuyệt đối không xem dashboard."

        current_time_str = datetime.now().strftime("%A, ngày %d/%m/%Y, %H:%M")

        self.system_instruction = (
            "BẢN SẮC & BỐI CẢNH:\n"
            "1. Bạn tên là 'Sên' ✨, trợ lý ảo thông minh của Tourism Gate.\n"
            f"2. Người đang nói chuyện: {self.user_name} (Vai trò: {user_role}).\n"
            f"3. Thời gian hiện tại: {current_time_str}.\n"
            f"4. QUYỀN HẠN: {perm_desc}\n\n"
            "NGUYÊN TẮC 'THÔNG MINH':\n"
            "1. DUY TRÌ NGỮ CẢNH: Luôn ghi nhớ chủ đề của các câu hỏi trước. Nếu người dùng hỏi 'còn không?', 'thế còn ngày mai?', 'tốn bao nhiêu?' -> Phải hiểu họ đang hỏi tiếp về Vé hoặc Doanh thu từ câu trước.\n"
            "2. CHỦ ĐỘNG TRA CỨU: Thay vì hỏi lại 'Bạn muốn tra cứu gì?', hãy chủ động gọi hàm (Tool Use) để kiểm tra dữ liệu nếu câu hỏi có liên quan đến chức năng của bạn.\n"
            "3. XỬ LÝ LỖI: Nếu gọi hàm mà kết quả trống (ví dụ: không có vé), hãy thông báo nhẹ nhàng và gợi ý họ kiểm tra lại mã vé hoặc mua vé mới.\n"
            "4. PHONG CÁCH: Thân thiện, ngắn gọn, dùng Markdown để trình bày bảng biểu/danh sách. Luôn dùng Tiếng Việt."
        )

        # 3. Danh sách Tools (ánh xạ tên hàm)
        self.tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="get_dashboard_summary",
                        description="Lấy thông số tổng quan của dashboard hôm nay (doanh thu, lượt khách, tỷ lệ lỗi).",
                    ),
                    types.FunctionDeclaration(
                        name="get_revenue_report",
                        description="Lấy báo cáo doanh thu trong số ngày gần đây.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {"days": {"type": "INTEGER"}},
                        },
                    ),
                    types.FunctionDeclaration(
                        name="get_visitor_stats",
                        description="Lấy thống kê lượt khách vào/ra trong số giờ gần đây.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {"hours": {"type": "INTEGER"}},
                        },
                    ),
                    types.FunctionDeclaration(
                        name="check_ticket_status",
                        description="Kiểm tra chi tiết trạng thái của một mã vé cụ thể.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {"ticket_id": {"type": "STRING"}},
                            "required": ["ticket_id"],
                        },
                    ),
                    types.FunctionDeclaration(
                        name="list_gates_health",
                        description="Lấy danh sách tất cả các cổng và trạng thái hoạt động.",
                    ),
                    types.FunctionDeclaration(
                        name="get_my_tickets",
                        description="Lấy danh sách các vé mà khách hàng hiện tại đang sở hữu.",
                    ),
                    types.FunctionDeclaration(
                        name="get_park_info",
                        description="Lấy thông tin chung về khu du lịch và hướng dẫn sử dụng app.",
                    ),
                ]
            )
        ]

        # 4. Cấu hình sinh bản tin
        self.config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            tools=self.tools,
            temperature=0.7,
            max_output_tokens=400, # Giảm để phản hồi nhanh hơn
        )

    # ── Tools for Gemini ────────────────────────────────────────

    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Lấy thông số tổng quan của dashboard hôm nay (doanh thu, lượt khách, tỷ lệ lỗi)."""
        if self.user_role not in ["admin", "manager"]:
            return {"error": "Tính năng tra cứu dashboard chỉ dành cho Admin và Manager."}
            
        stats = await self.report_service.get_realtime_stats()
        return {
            "current_inside": stats.get("current_inside"),
            "checkins_today": stats.get("checkins_today"),
            "revenue_today": stats.get("revenue_today"),
            "error_rate_today": stats.get("error_rate_today")
        }

    async def get_revenue_report(self, days: int = 7) -> Dict[str, Any]:
        """Lấy báo cáo doanh thu trong số ngày gần đây (mặc định 7 ngày)."""
        if self.user_role not in ["admin", "manager"]:
            return {"error": "Bạn không có quyền truy cập báo cáo doanh thu."}
            
        now = datetime.now(timezone.utc)
        d_from = now - timedelta(days=days)
        data = await self.report_service.get_revenue(d_from, now)
        return {
            "total_revenue": data.get("total_revenue"),
            "total_tickets": data.get("total_tickets"),
            "by_type": data.get("by_type"),
            "period_days": days
        }

    async def get_visitor_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Lấy thống kê lượt khách vào/ra trong số giờ gần đây (mặc định 24h)."""
        if self.user_role not in ["admin", "manager"]:
            return {"error": "Bạn không có quyền truy cập thống kê lượt khách."}
            
        now = datetime.now(timezone.utc)
        d_from = now - timedelta(hours=hours)
        data = await self.report_service.get_visitors(d_from, now)
        return {
            "total_checkins": data.get("total_checkins"),
            "total_checkouts": data.get("total_checkouts"),
            "current_inside": data.get("current_inside"),
            "by_channel": data.get("by_channel"),
            "period_hours": hours
        }

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
        """Xử lý tin nhắn sử dụng google-genai SDK mới."""
        contents = []
        if history:
            for m in history:
                role = "user" if m.get("role") == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part(text=m.get("content", ""))]))
        
        # Thêm tin nhắn hiện tại
        contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

        try:
            # 1. LOG INPUT (Gửi gì cho AI)
            logger.info(f"--- AI INPUT (User: {self.user_email}) ---")
            logger.info(f"Message: {user_message}")
            if history:
                logger.info(f"History context: {len(history)} messages")

            # Gửi yêu cầu lên Gemini
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=self.config
            )

            # Vòng lặp xử lý Function Calling
            while True:
                # Đảm bảo có ứng viên (candidate)
                if not response.candidates:
                    break
                
                # Kiểm tra xem có part nào là function_call không (quét toàn bộ parts)
                current_parts = response.candidates[0].content.parts
                function_calls = [p.function_call for p in current_parts if p.function_call]
                
                # Nếu không có lệnh gọi hàm nào -> Kết thúc vòng lặp để trả về text
                if not function_calls:
                    break
                
                # Lưu lại content của model (bao gồm cả text và call) vào history để duy trì ngữ cảnh
                contents.append(response.candidates[0].content)
                
                # Xử lý tất cả các function calls được yêu cầu
                response_parts = []
                for fc in function_calls:
                    fn_name = fc.name
                    fn_args = fc.args or {}
                    
                    logger.info(f"==> AI REQUESTED TOOL: {fn_name} | Args: {fn_args}")

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
                        result = await fn_map[fn_name](**fn_args)
                        logger.info(f"==> TOOL RESULT: {str(result)[:200]}...")
                        
                        # Tạo phần phản hồi cho hàm này
                        response_parts.append(types.Part(
                            function_response=types.FunctionResponse(
                                name=fn_name,
                                response={"result": result}
                            )
                        ))
                    else:
                        logger.warning(f"Tool {fn_name} is not implemented.")
                        response_parts.append(types.Part(
                            function_response=types.FunctionResponse(
                                name=fn_name,
                                response={"result": {"error": "Hàm này chưa được cài đặt."}}
                            )
                        ))

                # Thêm tất cả kết quả hàm vào history
                contents.append(types.Content(role="user", parts=response_parts))
                
                # Gọi lại Gemini với kết quả mới để nó tổng hợp câu trả lời cuối cùng
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=self.config
                )

            # 2. LOG FULL RESPONSE (Dữ liệu thô từ Google)
            try:
                logger.info(f"--- FULL AI RESPONSE ---")
                logger.info(response.model_dump_json())
            except:
                logger.debug("Could not JSON dump response")

            # 3. TRÍCH XUẤT VĂN BẢN
            final_text = ""
            try:
                if response.text:
                    final_text = response.text
            except:
                pass

            if not final_text:
                for candidate in response.candidates:
                    for part in candidate.content.parts:
                        if part.text:
                            final_text += part.text
            
            final_text = final_text.strip()
            logger.info(f"--- FINAL TEXT TO USER ---")
            logger.info(f"Length: {len(final_text)} chars")
            
            if not final_text:
                return "Sên đã nhận được yêu cầu nhưng không thể trích xuất văn bản trả lời. Hãy thử hỏi câu khác nhé!"
                
            return final_text

        except Exception as e:
            logger.error(f"AiService Error: {str(e)}")
            return f"Sên rất tiếc, đã có lỗi xảy ra: {str(e)}"
