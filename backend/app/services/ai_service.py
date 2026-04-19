import logging
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

    def __init__(self, db: AsyncIOMotorDatabase, user_email: str = None, user_role: str = None):
        self.db = db
        self.report_service = ReportService(db)
        self.user_email = user_email
        self.user_role = user_role
        
        # 1. Khởi tạo Client mới (chuẩn v1.0+)
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        # 2. Định nghĩa System Instruction
        role_desc = f"Bạn đang hỗ trợ người dùng có Email: {user_email} và Vai trò: {user_role}."
        self.system_instruction = (
            "BẢN SẮC: Bạn là 'Sên', trợ lý ảo AI chính thức của Tourism Gate. "
            f"{role_desc} "
            "PHONG CÁCH: Trả lời ngắn gọn, trực diện, chuyên nghiệp. "
            "QUY TẮC: 1. Ưu tiên giải quyết yêu cầu trước. "
            "2. Nhấn mạnh ưu điểm FaceID. "
            "3. BẢO MẬT: Khách CHỈ xem vé của mình. "
            "4. TRÌNH BÀY: Markdown súc tích. "
            "5. NGÔN NGỮ: Tiếng Việt."
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
        stats = await self.report_service.get_realtime_stats()
        # Tối ưu Token: Loại bỏ danh sách sự kiện chi tiết và trạng thái cổng chi tiết
        # AI chỉ cần các con số tổng hợp để trả lời nhanh.
        return {
            "current_inside": stats.get("current_inside"),
            "checkins_today": stats.get("checkins_today"),
            "revenue_today": stats.get("revenue_today"),
            "error_rate_today": stats.get("error_rate_today")
        }

    async def get_revenue_report(self, days: int = 7) -> Dict[str, Any]:
        """Lấy báo cáo doanh thu trong số ngày gần đây (mặc định 7 ngày)."""
        now = datetime.now(timezone.utc)
        d_from = now - timedelta(days=days)
        data = await self.report_service.get_revenue(d_from, now)
        # Tối ưu Token: Loại bỏ danh sách 'by_date' quá dài
        return {
            "total_revenue": data.get("total_revenue"),
            "total_tickets": data.get("total_tickets"),
            "by_type": data.get("by_type"),
            "period_days": days
        }

    async def get_visitor_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Lấy thống kê lượt khách vào/ra trong số giờ gần đây (mặc định 24h)."""
        now = datetime.now(timezone.utc)
        d_from = now - timedelta(hours=hours)
        data = await self.report_service.get_visitors(d_from, now)
        # Tối ưu Token: Chỉ giữ lại các chỉ số quan trọng nhất
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
            # Gửi yêu cầu lên Gemini
            response = self.client.models.generate_content(
                model='gemini-flash-latest',
                contents=contents,
                config=self.config
            )

            # Vòng lặp xử lý Function Calling
            while True:
                # Trích xuất part đầu tiên
                first_part = response.candidates[0].content.parts[0]
                
                # Nếu là Function Call -> Gọi hàm
                if first_part.function_call:
                    fc = first_part.function_call
                    fn_name = fc.name
                    fn_args = fc.args
                    
                    logger.info(f"Sên call function: {fn_name} | Args: {fn_args}")

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
                        
                        # Thêm chính cái Call vừa rồi vào lịch sử
                        contents.append(response.candidates[0].content)
                        
                        # Gửi kết quả hàm (SDK mới dùng role='user' hoặc 'tool' tùy cấu hình, 
                        # nhưng quan trọng là cấu trúc FunctionResponse)
                        contents.append(types.Content(
                            role="user", # Trong SDK python-genai, kết quả tool gửi lại bằng role user hoặc tool
                            parts=[types.Part(
                                function_response=types.FunctionResponse(
                                    name=fn_name,
                                    response={"result": result}
                                )
                            )]
                        ))
                        
                        # Gọi lại Gemini để lấy câu trả lời cuối cùng dựa trên kết quả hàm
                        response = self.client.models.generate_content(
                            model='gemini-flash-latest',
                            contents=contents,
                            config=self.config
                        )
                    else:
                        break
                else:
                    # Nếu không còn function call -> Kết thúc vòng lặp
                    break

            # LOG CHI TIẾT ĐỂ GỠ RỐI (CHỈ DÙNG TRONG ĐỒ ÁN)
            try:
                logger.info(f"--- FULL AI RESPONSE ---")
                logger.info(response.model_dump_json())
            except:
                logger.info(f"AI response received but could not dump to JSON: {response}")

            # TRÍCH XUẤT VĂN BẢN CUỐI CÙNG: 
            final_text = ""
            
            # SDK mới đôi khi trả về text trực tiếp ở cấp độ response
            try:
                if response.text:
                    final_text = response.text
            except:
                pass

            # Nếu không có, quét từng part trong candidate đầu tiên
            if not final_text:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.text:
                                final_text += part.text
            
            # Làm sạch khoảng trắng
            final_text = final_text.strip()
            
            logger.info(f"Sên FINAL TEXT extracted: '{final_text}'")
            
            if not final_text:
                return "Sên đã nghe thấy bạn, nhưng hệ thống AI chưa trả về phản hồi văn bản rõ ràng. Bạn hãy thử hỏi lại nhé!"
                
            return final_text

        except Exception as e:
            logger.error(f"AiService Error: {str(e)}")
            return f"Sên rất tiếc, đã có lỗi xảy ra: {str(e)}"
