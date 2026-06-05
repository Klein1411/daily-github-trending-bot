import urllib.request
import json
import os
from google import genai
from datetime import datetime, timedelta

def get_yesterday():
    return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

def call_openrouter(prompt, api_key):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openrouter/free",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    req = urllib.request.Request(url, headers=headers, data=json.dumps(data).encode('utf-8'))
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"Lỗi OpenRouter: {e}")
        return None

def analyze_repos(repos_data):
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    
    prompt = """Bạn là một chuyên gia phân tích mã nguồn. Dưới đây là danh sách 5 kho lưu trữ GitHub có xu hướng phát triển nhanh nhất.
Hãy viết ra Ưu điểm (Pros) và Nhược điểm (Cons) một cách chi tiết, chuyên nghiệp cho TỪNG kho lưu trữ dựa trên thông tin của chúng.
Format trả về phải là một chuỗi JSON duy nhất, là một mảng (array) chứa các object. Mỗi object có 3 key: "name" (tên repo gốc), "pros" (ưu điểm chi tiết), "cons" (nhược điểm chi tiết).
Không trả về markdown, chỉ trả về chuỗi JSON thuần túy để parse.
Dữ liệu thô:
""" + json.dumps(repos_data)
    
    # 1. Thử gọi Gemini trước
    if gemini_key:
        client = genai.Client(api_key=gemini_key)
        models_to_try = [
            'gemini-3-flash-preview',
            'gemini-3.5-flash'
        ]
        
        for model_name in models_to_try:
            try:
                print(f"Đang thử Gemini model: {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                text = response.text
                start = text.find('[')
                end = text.rfind(']') + 1
                if start != -1 and end != -1:
                    json_str = text[start:end]
                    return json.loads(json_str), model_name
            except Exception as e:
                print(f"Lỗi khi dùng {model_name}: {e}")
                continue
    
    # 2. Nếu Gemini sập hoàn toàn, chuyển sang subagent OpenRouter
    if openrouter_key:
        print("Gemini sập, chuyển sang gọi subagent OpenRouter (openrouter/free)...")
        text = call_openrouter(prompt, openrouter_key)
        if text:
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end != -1:
                json_str = text[start:end]
                try:
                    return json.loads(json_str), "openrouter/free"
                except Exception as e:
                    print(f"Lỗi parse JSON từ OpenRouter: {e}")
    
    return None, None

def main():
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Lỗi: Chưa cài đặt DISCORD_WEBHOOK_URL.")
        return

    yesterday = get_yesterday()
    # Chuyển đổi query sang các repo ĐƯỢC PUSH HÔM QUA (pushed:>yesterday) để ra các repo bự/phổ biến nhất có update
    url = f"https://api.github.com/search/repositories?q=pushed:>{yesterday}&sort=stars&order=desc&per_page=5"
    
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
    ai_analysis, used_model = analyze_repos(repos_raw)

    fields = []
    for i, item in enumerate(repos_raw, 1):
        pros = "Không có phân tích (Hệ thống AI đang bảo trì)."
        cons = "Không có phân tích (Hệ thống AI đang bảo trì)."
        
        if ai_analysis:
            for ai_item in ai_analysis:
                if ai_item.get('name') == item['name']:
                    pros = ai_item.get('pros', pros)
                    cons = ai_item.get('cons', cons)
                    if len(pros) > 400: pros = pros[:397] + "..."
                    if len(cons) > 400: cons = cons[:397] + "..."
                    break
        
        value_text = f"**Ưu điểm (Pros):** {pros}\n**Nhược điểm (Cons):** {cons}\n[🔗 Mở Kho lưu trữ]({item['url']})"
        if len(value_text) > 1024:
            value_text = value_text[:1021] + "..."
            
        fields.append({
            "name": f"{i}. {item['name']} [⭐ {item['stars']}]",
            "value": value_text,
            "inline": False
        })

    footer_text = f"Powered by {used_model} & Bé Lilith 🪄" if used_model else "Powered by GitHub Search & Bé Lilith 🪄"

    embed = {
        "title": "🚀 BÁO CÁO GITHUB TRENDING (HOTTEST PUSHED REPOS)",
        "description": f"**Ngày:** {datetime.now().strftime('%d/%m/%Y')}\n**Tiêu chí:** Các kho lưu trữ được cập nhật (push) trong 24h qua và có lượng sao cao nhất.",
        "color": 2369870,
        "fields": fields,
        "footer": {
            "text": footer_text
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
