import urllib.request
import json
import os
from google import genai
from datetime import datetime, timedelta

def get_yesterday():
    return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

def analyze_repos_with_gemini(repos_data):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    
    try:
        client = genai.Client(api_key=api_key)
        prompt = """Bạn là một chuyên gia phân tích mã nguồn. Dưới đây là danh sách 5 kho lưu trữ GitHub có tốc độ tăng sao nhanh nhất.
Hãy viết ra Ưu điểm (Pros) và Nhược điểm (Cons) một cách chi tiết, chuyên nghiệp cho TỪNG kho lưu trữ dựa trên thông tin của chúng.
Format trả về phải là một chuỗi JSON duy nhất, là một mảng (array) chứa các object. Mỗi object có 3 key: "name" (tên repo gốc), "pros" (ưu điểm chi tiết), "cons" (nhược điểm chi tiết).
Không trả về markdown, chỉ trả về chuỗi JSON thuần túy để parse.
Dữ liệu thô:
""" + json.dumps(repos_data)
        
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt
        )

        text = response.text
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != -1:
            json_str = text[start:end]
            return json.loads(json_str)
    except Exception as e:
        print(f"Gemini AI Error: {e}")
    return None

def main():
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Lỗi: Chưa cài đặt DISCORD_WEBHOOK_URL.")
        return

    yesterday = get_yesterday()
    url = f"https://api.github.com/search/repositories?q=created:>{yesterday}&sort=stars&order=desc&per_page=5"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu GitHub: {e}")
        return

    repos_raw = []
    for item in data.get('items', []):
        repos_raw.append({
            "name": item['full_name'],
            "description": item.get('description'),
            "url": item['html_url'],
            "stars": item.get('stargazers_count')
        })

    # Chạy AI phân tích
    ai_analysis = analyze_repos_with_gemini(repos_raw)

    fields = []
    for i, item in enumerate(repos_raw, 1):
        pros = "Không có phân tích (thiếu biến GEMINI_API_KEY trên GitHub Secrets)."
        cons = "Không có phân tích (thiếu biến GEMINI_API_KEY trên GitHub Secrets)."
        
        if ai_analysis:
            for ai_item in ai_analysis:
                if ai_item.get('name') == item['name']:
                    pros = ai_item.get('pros', pros)
                    cons = ai_item.get('cons', cons)
                    break
        
        value_text = f"**Ưu điểm (Pros):** {pros}\n**Nhược điểm (Cons):** {cons}\n[🔗 Mở Kho lưu trữ]({item['url']})"
        
        fields.append({
            "name": f"{i}. {item['name']} [⭐ +{item['stars']}]",
            "value": value_text,
            "inline": False
        })

    embed = {
        "title": "🚀 BÁO CÁO GITHUB TRENDING (AI ANALYZED)",
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
        print(f"Lỗi gửi Discord: {e}")

if __name__ == "__main__":
    main()
