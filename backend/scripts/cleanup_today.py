import os
from datetime import datetime, time, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB  = os.getenv("MONGO_DB", "tourism_db")

def cleanup_today():
    if not MONGO_URI:
        print("Error: MONGO_URI not found in .env file.")
        return

    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]

    # Xác định khoảng thời gian "hôm nay" (theo UTC để khớp với DB)
    now = datetime.now(timezone.utc)
    start_of_today = datetime.combine(now.date(), time.min).replace(tzinfo=timezone.utc)
    end_of_today   = datetime.combine(now.date(), time.max).replace(tzinfo=timezone.utc)

    print(f"--- Cleanup Tickets from {start_of_today} to {end_of_today} ---")

    # 1. Tìm IDs của các vé tạo trong hôm nay
    query = {"created_at": {"$gte": start_of_today, "$lte": end_of_today}}
    tickets_to_delete = list(db["tickets"].find(query, {"_id": 1}))
    ticket_ids = [t["_id"] for t in tickets_to_delete]

    if not ticket_ids:
        print("Không tìm thấy vé nào được tạo trong hôm nay.")
        return

    print(f"Tìm thấy {len(ticket_ids)} vé để xóa.")

    # 2. Xóa Tickets
    res_tickets = db["tickets"].delete_many({"_id": {"$in": ticket_ids}})
    print(f"- Đã xóa {res_tickets.deleted_count} vé.")

    # 3. Xóa Identities liên quan
    res_idents = db["identities"].delete_many({"ticket_id": {"$in": ticket_ids}})
    print(f"- Đã xóa {res_idents.deleted_count} thông tin khuôn mặt/định danh.")

    # 4. Xóa Transactions liên quan
    res_trans = db["transactions"].delete_many({"ticket_id": {"$in": ticket_ids}})
    print(f"- Đã xóa {res_trans.deleted_count} giao dịch.")

    # 5. Xóa Audit Logs liên quan (nếu có lưu resource là ticket_id)
    res_logs = db["audit_logs"].delete_many({"resource": {"$in": ticket_ids}})
    print(f"- Đã xóa {res_logs.deleted_count} nhật ký thao tác liên quan.")

    print("\n--- Hoàn tất dọn dẹp dữ liệu hôm nay! ---")

if __name__ == "__main__":
    confirm = input("Bạn có chắc chắn muốn xóa TẤT CẢ vé được tạo trong hôm nay không? (y/n): ")
    if confirm.lower() == 'y':
        cleanup_today()
    else:
        print("Đã hủy bỏ.")
