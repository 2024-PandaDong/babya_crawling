import re
import os
import sys
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup, Comment
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import babya_server

chrome_options = Options()
chrome_options.add_experimental_option("detach", True)
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

try:
    region = "108050"
    current_list = list()
    result_data = []

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]

    url = f"{base_url}health/pregnant.jsp"
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    for i in soup.select("#lmenu > ul > li.select > ul > li > a"):
        id_item = i.get("href").split("health/")[1]
        current_list.append(id_item)
        
        
    page_list = set(current_list) - set(collected_list)

    for page_id in page_list:
        page_url = f"{base_url}health/{page_id}"
        driver.get(page_url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        data_dict = {
            "title": None,
            "content": None,
            "editDate": None,
            "pageId": None,
            "site": None,
            "page": None
        }
        
        styles = []
        link_data = ['<link href="https://www.icdonggu.go.kr/share/css/common.css"rel="stylesheet" />',
                     '<link href="https://www.icdonggu.go.kr/share/css/inc.css" rel="stylesheet" />',
                     '<link href="https://www.icdonggu.go.kr/share/css/program.css" rel="stylesheet" />',
                     '<link href="https://www.icdonggu.go.kr/share/css/tooltip.css" rel="stylesheet" type="text/css" />',
                     '<link href="https://www.icdonggu.go.kr/share/css/font/NSneo.css" rel="stylesheet" type="text/css" />',
                     '<link href="https://www.icdonggu.go.kr/share/css/font/Spoqa.css" rel="stylesheet" type="text/css" />',
                     '<link href="https://www.icdonggu.go.kr/clinic/css/inc.css" rel="stylesheet" />',
                     '<link href="https://www.icdonggu.go.kr/clinic/css/contents.css?v240822" rel="stylesheet" />',
                     '<link href="https://www.icdonggu.go.kr/clinic/css/sub.css" rel="stylesheet" />']
        elements = soup.select("#tab")
        
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
            
        for meta in soup.select("html > head > meta"):
            if meta.get("charset"):
                styles.append(str(meta))
            
        for link in link_data:
            styles.append(link)

        for title in soup.select("#con-tit > h3"):
            data_dict["title"] = title.get_text()
            
        for content in soup.select("#detail_con"):
            for img in content.find_all('img'):
                img_url = img.get("src")
                if img_url:
                    img["src"] = urllib.parse.urljoin(base_url, img_url)
                
            for a in content.find_all("a", href=True):
                file_url = a['href']
                a['href'] = urllib.parse.urljoin(base_url, file_url)
                
            styles_str = "".join(styles)
            content_str = re.sub(r'[\s\u00A0-\u00FF]+', " ", str(content))
            
            head_content = f"<head>{styles_str}</head>"
            body_content = f"<body>{content_str}</body>"
            
            html_content = f"<!DOCTYPE html><html>{head_content}{body_content}</html>"
            data_dict["content"] = html_content
            
        # 최근 수정일 없음
        
        data_dict["pageId"] = page_id
        data_dict["site"] = base_url
        data_dict["page"] = page_url
        
        if all(data_dict[key] is not None for key in ["title", "content"]):
            result_data.append(data_dict)
 
        
    if (len(result_data) > 0):
        print(f"크롤링한 페이지 개수: [{len(result_data)}]")
        policy = requests.post(f"{babya_server}/policy", json=result_data)
        print(policy.status_code)
        print(policy.text)
        
    else:
        print("아직 새로운 정책이 업데이트 되지 않았습니다.")

except Exception as e:
    print(f"Error: {e}")
    driver.close()
    sys.exit()

finally:
    driver.close()
    sys.exit()

while True:
    pass