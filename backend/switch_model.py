import os
import sys

# Danh sách các mô hình phổ biến và an toàn cho dự án
MODELS = [
    ("Gemini 1.5 Flash (Cân bằng, khuyên dùng)", "gemini-1.5-flash"),
    ("Gemini 1.5 Flash-8B (Siêu nhẹ, tiết kiệm nhất)", "gemini-1.5-flash-8b"),
    ("Gemini 2.0 Flash (Thử nghiệm, cực nhanh)", "gemini-2.0-flash-exp"),
    ("Gemini Flash Latest (Bản bạn vừa hết lượt)", "gemini-flash-latest"),
]

ENV_FILE = ".env"

def main():
    print("="*50)
    print("CHƯƠNG TRÌNH CHUYỂN ĐỔI MÔ HÌNH AI - TOURISM GATE")
    print("="*50)
    print("Chọn mô hình bạn muốn dùng:")
    
    for i, (desc, name) in enumerate(MODELS, 1):
        print(f"{i}. {desc} -> [{name}]")
    
    print(f"{len(MODELS) + 1}. Tự nhập tên mô hình khác...")
    
    try:
        choice = input("\nNhập số (1-5): ").strip()
        
        if choice == str(len(MODELS) + 1):
            model_name = input("Nhập chính xác mã model: ").strip()
        else:
            idx = int(choice) - 1
            if 0 <= idx < len(MODELS):
                model_name = MODELS[idx][1]
            else:
                print("Lựa chọn không hợp lệ!")
                return
        
        # Đọc file .env
        if not os.path.exists(ENV_FILE):
            lines = []
        else:
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        
        # Cập nhật hoặc thêm mới AI_MODEL_NAME
        found = False
        new_line = f"AI_MODEL_NAME={model_name}\n"
        
        for i, line in enumerate(lines):
            if line.startswith("AI_MODEL_NAME="):
                lines[i] = new_line
                found = True
                break
        
        if not found:
            # Thêm vào cuối file nếu chưa có
            if lines and not lines[-1].endswith('\n'):
                lines.append('\n')
            lines.append(f"\n# --- AI Configuration ---\n")
            lines.append(new_line)
            
        # Ghi lại file
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
        print("\n" + "!"*50)
        print(f"THÀNH CÔNG: Đã đổi sang mô hình [{model_name}]")
        print("LƯU Ý: Bạn cần KHỞI ĐỘNG LẠI BACKEND để thay đổi có hiệu lực.")
        print("!"*50)
        
    except ValueError:
        print("Vui lòng nhập một con số!")
    except Exception as e:
        print(f"Lỗi: {e}")

if __name__ == "__main__":
    main()
