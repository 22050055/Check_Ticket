import logging
from typing import Dict, List, Any
from google import genai
from google.genai import types
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone, timedelta

from ..core.config import settings
from .report_service import ReportService
from ..api.tickets import _auto_cleanup_expired_tickets, _make_qr_token
import uuid

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
        
        # Kiểm tra tính hợp lệ của model_name, ưu tiên các dòng 2.5, 3.0, 3.1 và Gemma
        target_model = model_name or settings.AI_MODEL_NAME
        # Fallback về mặc định (3.1 Pro) nếu ID không chứa gemini hoặc gemma
        if not target_model or not any(x in target_model.lower() for x in ["gemini-", "gemma-"]):
            target_model = "gemini-3.1-pro-preview"
        
        self.model_name = target_model
        
        # 1. Khởi tạo Client mới (chuẩn v1.0+)
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        # 2. Định nghĩa System Instruction
        # Phân quyền rõ rệt trong Prompt và dặn AI thông minh hơn về ngữ cảnh
        perm_desc = ""
        if user_role in ["admin", "manager"]:
            perm_desc = "Bạn là Admin/Manager: Có quyền xem báo cáo doanh thu, lượt khách, dashboard và QUẢN LÝ vé."
        elif user_role in ["operator", "cashier"]:
            perm_desc = "Bạn là Nhân viên: Có quyền tra cứu trạng thái vé, thông tin cổng và BÁN vé."
        else:
            perm_desc = "Bạn là Khách hàng: Bạn có quyền xem vé của mình, MUA vé mới và HỦY vé chưa dùng."

        ict_timezone = timezone(timedelta(hours=7))
        current_time_str = datetime.now(ict_timezone).strftime("%A, ngày %d/%m/%Y, %H:%M")

        self.system_instruction = (
            "BẢN SẮC & BỐI CẢNH:\n"
            "1. Bạn là 'Sên' ✨ - Nhân viên tư vấn nhiệt huyết và chuyên nghiệp của Khu du lịch Tourism Gate.\n"
            f"2. Đối tượng đang hỗ trợ: {self.user_name} (Email: {user_email}, Vai trò: {user_role}).\n"
            f"3. Thời gian hiện tại: {current_time_str}.\n"
            f"4. QUYỀN HẠN: {perm_desc}\n\n"
            "PHONG CÁCH & QUY TẮC ỨNG XỬ (NHÂN VIÊN ƯU TÚ):\n"
            "1. THÁI ĐỘ: Luôn niềm nở, lịch sự và hiếu khách. Sử dụng các từ ngữ mang tính mời gọi và tích cực.\n"
            "2. TƯ VẤN NHIỆT TÌNH: Khi khách hỏi về khu du lịch, hãy giới thiệu những điểm mạnh nhất như: Hệ thống FaceID không chạm cực hiện đại, không gian xanh, trò chơi đa dạng.\n"
            "3. LUÔN NHẮC FACEID: Đây là niềm tự hào của dự án. Hãy dặn khách: 'Nhớ quét gương mặt nhé! ✨' để họ có trải nghiệm VIP tại cổng soát vé.\n"
            "4. CHÍNH XÁC: Cung cấp đúng giá vé và giờ mở cửa từ dữ liệu hệ thống.\n"
            "5. DUY TRÌ NGỮ CẢNH: Nhớ nội dung cuộc trò chuyện trước để trả lời câu hỏi ngắn.\n"
            "6. TRÌNH BÀY: Dùng Markdown, tạo bảng biểu khi liệt kê giá vé cho chuyên nghiệp.\n"
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
                        name="get_spending_analytics",
                        description="Phân tích tổng số tiền đã chi tiêu và số lượng vé đã mua của khách hàng.",
                    ),
                    types.FunctionDeclaration(
                        name="get_usage_timeline",
                        description="Tra cứu lịch sử vào/ra cổng (check-in/out) của khách hàng.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "ticket_id": {"type": "STRING", "description": "Mã vé cần tra (để trống nếu muốn xem tất cả)"}
                            },
                        },
                    ),
                    types.FunctionDeclaration(
                        name="cancel_ticket",
                        description="Hủy một vé chưa sử dụng của khách hàng.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "ticket_id": {"type": "STRING", "description": "Mã định danh duy nhất của vé cần hủy"}
                            },
                            "required": ["ticket_id"],
                        },
                    ),
                    types.FunctionDeclaration(
                        name="buy_ticket",
                        description="Thực hiện mua vé mới. Hỗ trợ mua hộ cho người khác qua Email.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "ticket_type": {"type": "STRING", "description": "Loại vé: 'adult' (Người lớn) hoặc 'child' (Trẻ em)"},
                                "customer_email": {"type": "STRING", "description": "Email người sở hữu vé (để trống nếu mua cho chính mình)"},
                                "quantity": {"type": "INTEGER", "description": "Số lượng vé (mặc định 1)"}
                            },
                            "required": ["ticket_type"],
                        },
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
            max_output_tokens=1000, 
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
        
        results = []
        for t in tickets:
            identity = await self.db["identities"].find_one({"ticket_id": str(t["_id"])})
            results.append({
                "ticket_id": str(t["_id"]),
                "type": t.get("ticket_type"),
                "status": t.get("status"),
                "valid_until": t.get("valid_until").isoformat() if t.get("valid_until") else None,
                "has_face": identity.get("has_face", False) if identity else False
            })
        return results

    async def get_spending_analytics(self) -> Dict[str, Any]:
        """Phân tích tổng quan chi tiêu của khách hàng hiện tại."""
        if not self.user_email:
            return {"error": "Không xác định được danh tính người dùng."}

        # Query tất cả ticket_id của user trước
        cursor = self.db["tickets"].find({"customer_email": self.user_email})
        user_ticket_ids = [str(t["_id"]) for t in await cursor.to_list(None)]
        
        if not user_ticket_ids:
            return {"total_spent": 0, "total_tickets": 0, "message": "Bạn chưa có giao dịch nào."}

        pipeline = [
            {"$match": {"ticket_id": {"$in": user_ticket_ids}}},
            {"$group": {
                "_id": None,
                "total_amount": {"$sum": "$amount"},
                "count": {"$sum": 1}
            }}
        ]
        results = await self.db["transactions"].aggregate(pipeline).to_list(1)
        data = results[0] if results else {"total_amount": 0, "count": 0}
        
        return {
            "total_spent": data["total_amount"],
            "total_tickets": data["count"],
            "currency": "VNĐ",
            "average_per_ticket": round(data["total_amount"] / data["count"]) if data["count"] > 0 else 0
        }

    async def get_usage_timeline(self, ticket_id: str = None) -> List[Dict[str, Any]]:
        """Tra cứu lịch sử vào/ra cổng."""
        if not self.user_email:
            return {"error": "Không xác định được danh tính người dùng."}

        query = {}
        if ticket_id:
            query["ticket_id"] = ticket_id
        else:
            # Lấy tất cả ticket_id của user
            cursor = self.db["tickets"].find({"customer_email": self.user_email})
            user_ticket_ids = [str(t["_id"]) for t in await cursor.to_list(None)]
            query["ticket_id"] = {"$in": user_ticket_ids}

        events = await self.db["gate_events"].find(query).sort("created_at", -1).limit(20).to_list(20)
        
        timeline = []
        for e in events:
            timeline.append({
                "time": e["created_at"].strftime("%H:%M:%S %d/%m/%Y"),
                "gate": e.get("gate_id", "Unknown"),
                "direction": "Vào (IN)" if e.get("direction") == "IN" else "Ra (OUT)",
                "result": "Thành công" if e.get("result") == "SUCCESS" else "Thất bại"
            })
        return timeline

    async def buy_ticket(self, ticket_type: str, customer_email: str = None, quantity: int = 1) -> Dict[str, Any]:
        """Thực hiện mua vé mới cho khách hàng."""
        # Email mặc định là email người đang chat
        email = customer_email or self.user_email
        if not email:
            return {"error": "Cần cung cấp Email để mua vé."}

        # Bảng giá demo
        PRICES = {"adult": 200000, "child": 120000}
        price = PRICES.get(ticket_type.lower(), 200000)
        
        vn_tz = timezone(timedelta(hours=7))
        now = datetime.now(vn_tz)
        valid_until = now + timedelta(days=1) # Hiệu lực 24h

        # Lấy/Tạo customer
        customer = await self.db["customers"].find_one({"email": email})
        customer_id = str(customer["_id"]) if customer else str(uuid.uuid4())
        if not customer:
            await self.db["customers"].insert_one({
                "_id": customer_id,
                "name": email.split("@")[0],
                "email": email,
                "created_at": now
            })

        issued_tickets = []
        for _ in range(quantity):
            tid = str(uuid.uuid4())
            # Lưu Ticket
            await self.db["tickets"].insert_one({
                "_id": tid,
                "customer_id": customer_id,
                "customer_email": email, # Thêm Email để dễ query
                "ticket_type": ticket_type,
                "price": price,
                "status": "active",
                "valid_until": valid_until,
                "venue_id": "default_gate",
                "issued_by_name": "Sên AI ✨",
                "created_at": now
            })
            # Lưu Identity (has_face default = False)
            await self.db["identities"].insert_one({
                "_id": str(uuid.uuid4()),
                "ticket_id": tid,
                "has_face": False,
                "created_at": now
            })
            issued_tickets.append(tid)

        return {
            "success": True,
            "message": f"Đã mua thành công {quantity} vé {ticket_type} cho {email}.",
            "ticket_ids": issued_tickets,
            "total_price": price * quantity,
            "instructions": "Vui lòng kiểm tra mục 'Vé của tôi' và ĐỪNG QUÊN quét gương mặt để hưởng ưu đãi FaceID nhé! ✨"
        }

    async def cancel_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Hủy vé chưa sử dụng."""
        ticket = await self.db["tickets"].find_one({"_id": ticket_id})
        if not ticket:
            return {"error": "Không tìm thấy mã vé này."}
        
        if ticket.get("status") != "active":
            return {"error": f"Không thể hủy vé đang ở trạng thái {ticket.get('status')}."}

        # Cập nhật status
        await self.db["tickets"].update_one(
            {"_id": ticket_id},
            {"$set": {"status": "revoked", "updated_at": datetime.now()}}
        )
        
        return {
            "success": True,
            "message": f"Vé {ticket_id} đã được hủy thành công. Chúc bạn một ngày tốt lành!"
        }

    async def get_park_info(self) -> Dict[str, Any]:
        """Lấy thông tin chi tiết về khu du lịch để tư vấn cho khách."""
        return {
            "name": "Khu du lịch Quốc tế Tourism Gate",
            "slogan": "Trải nghiệm không chạm - Đậm chất công nghệ 🚀",
            "opening_hours": "07:30 - 17:30 hàng ngày (kể cả lễ Tết)",
            "ticket_prices": [
                {"type": "Người lớn (Adult)", "price": "200.000 VNĐ", "notes": "Dành cho khách trên 1.4m"},
                {"type": "Trẻ em (Child)", "price": "120.000 VNĐ", "notes": "Dành cho khách từ 1m - 1.4m"},
                {"type": "Em bé", "price": "Miễn phí", "notes": "Dưới 1m được miễn phí hoàn toàn"}
            ],
            "zones": [
                {"name": "Safari Hoang Dã", "description": "Ngắm thú quý hiếm ở khoảng cách gần."},
                {"name": "Thế giới nước", "description": "Hệ thống ống trượt cảm giác mạnh hàng đầu."},
                {"name": "Khu phố ẩm thực", "description": "Hội tụ tinh hoa ẩm thực 3 miền Bắc - Trung - Nam."}
            ],
            "special_tech": "Hệ thống soát vé FaceID nhận diện khuôn mặt trong 0.5 giây, không cần xếp hàng đợi lâu.",
            "is_it_fun": "Cực kỳ vui và đáng tiền! Đây là khu du lịch đầu tiên tại Việt Nam áp dụng công nghệ kiểm soát vé thông minh hoàn toàn.",
            "safety": "Đội ngũ cứu hộ và an ninh trực 24/7, đảm bảo an toàn tuyệt đối cho gia đình bạn."
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
                        "get_spending_analytics": self.get_spending_analytics,
                        "get_usage_timeline":    self.get_usage_timeline,
                        "buy_ticket":            self.buy_ticket,
                        "cancel_ticket":         self.cancel_ticket,
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
