import insightface

# Đường dẫn tuyệt đối tới thư mục models trong đồ án của bạn
# Chữ 'r' ở đầu chuỗi giúp Python hiểu đúng các dấu gạch chéo (\) của Windows
thu_muc_luu = r"E:\Learn\Do_an_nganh\Check_ticket\ai-services\face_verification\models"

print("Đang tải mô hình, vui lòng đợi...")

# Thêm tham số root để ép insightface lưu vào đúng thư mục đồ án
model = insightface.model_zoo.get_model(
    'arcface_r100_v1', 
    root=thu_muc_luu
)

print(f"Đã tải mô hình thành công!")
print(f"Bạn có thể kiểm tra tại: {thu_muc_luu}") 