import requests
from bs4 import BeautifulSoup

def get_trending():
    url = "https://github.com/trending"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    repos = []
    for article in soup.find_all('article', class_='Box-row'):
        h2 = article.find('h2', class_='h3 lh-condensed')
        if not h2: continue
        a_tag = h2.find('a')
        if not a_tag: continue
        name = a_tag['href'].strip('/')
        
        # stars today
        span_stars = article.find('span', class_='d-inline-block float-sm-right')
        stars_today = span_stars.text.strip() if span_stars else "Unknown"
        
        repos.append({'name': name, 'stars_today': stars_today})
        
    print(repos[:5])

get_trending()
