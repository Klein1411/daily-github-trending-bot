import urllib.request
import json
import os
from datetime import datetime, timedelta

def get_yesterday():
    return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

def main():
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Lỗi: Chưa cài đặt biến môi trường DISCORD_WEBHOOK_URL.")
        return

    yesterday = get_yesterday()
    # Tìm kiếm các repository mới tạo có tốc độ sao tăng mạnh nhất
    url = f"https://api.github.com/search/repositories?q=created:>{yesterday}&sort=stars&order=desc&per_page=5"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu từ GitHub: {e}")
        return

    fields = []
    for i, item in enumerate(data.get('items', []), 1):
        desc = item.get('description') or "Không có mô tả chi tiết."
        lang = item.get('language') or "Không xác định"
        stars = item.get('stargazers_count')
        
        value_text = f"**Ngôn ngữ:** {lang}\n**Mô tả:** {desc}\n[🔗 Mở Kho lưu trữ]({item['html_url']})"
        
        fields.append({
            "name": f"{i}. {item['full_name']} [⭐ +{stars}]",
            "value": value_text,
            "inline": False
        })

    if not fields:
        fields.append({"name": "Không có dữ liệu", "value": "Hôm qua không có repo nổi bật nào.", "inline": False})

    embed = {
        "title": "🚀 BÁO CÁO GITHUB TRENDING HÀNG NGÀY",
        "description": f"**Ngày:** {datetime.now().strftime('%d/%m/%Y')}\n**Tiêu chí:** Các kho lưu trữ mới tạo có tốc độ tăng sao nhanh nhất trong 24h qua.",
        "color": 2369870,
        "fields": fields,
        "footer": {
            "text": "Automated by GitHub Actions & Bé Lilith 🪄"
        }
    }

    req_discord = urllib.request.Request(
        webhook_url, 
        data=json.dumps({"embeds": [embed]}).encode('utf-8'), 
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    
    try:
        urllib.request.urlopen(req_discord)
        print("Đã gửi báo cáo lên Discord thành công!")
    except Exception as e:
        print(f"Lỗi khi gửi Discord: {e}")

if __name__ == "__main__":
    main()
