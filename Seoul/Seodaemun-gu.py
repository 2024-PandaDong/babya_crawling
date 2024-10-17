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
    region = "101140"
    link_list = list()
    current_list = list()
    result_data = []

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]

    url = f"{base_url}/contents/healthbiz/maternal/maternalHealth"
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    for i in soup.select("ul.depth02 > li.active > ul.depth03 > li > a"):
        id_item = i.get("href").split("contents/")[1]
        link_list.append(id_item)
        
    for link in link_list:
        driver.get(f"{base_url}/contents/{link}")
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        elements = soup.select("ul.sub-tab.clearfix")
        
        if elements:
            for element in elements:
                for i in element.select("ul.sub-tab.clearfix > li > a"):
                    href = i.get("href")
                    if href == "#":
                        current_list.append(link)
                        
                    else:
                        id_item = i.get("href").split("contents/")[1]
                        current_list.append(id_item)
                    
        else:
            current_list.append(link)
        
                
    page_list = set(current_list) - set(collected_list)
    
    for page_id in page_list:
        page_url = f"{base_url}/contents/{page_id}"
        driver.get(page_url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        data_dict = {
            "title": None,
            "content": None,
            "editDate": None,
            "pageId": None,
            "site": None
        }
        
        styles = []
        link_data = ['<link rel="stylesheet" href="https://www.sdm.go.kr/health/static/css/swiper.min.css?v=20231124" />',
                '<link rel="stylesheet" href="https://www.sdm.go.kr/health/static/css/style.css?v=20231124" />',
                '<link rel="stylesheet" href="https://www.sdm.go.kr/health/static/css/mainN.css" />',
                '<link rel="stylesheet" href="https://www.sdm.go.kr/health/static/css/bootstrap.min.css"/>',
                '<link rel="stylesheet" href="https://www.sdm.go.kr/health/static/css/reset.css"/>',
                '<link rel="stylesheet" href="https://www.sdm.go.kr/health/static/fonts/font-awesome/css/all.min.css"/>',
                '<link rel="stylesheet" href="https://www.sdm.go.kr/health/static/fonts/font.css"/>']
        elements = soup.select("ul.sub-tab.clearfix")
        
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
            
        for meta in soup.select("html > head > meta"):
            if meta.get("charset"):
                styles.append(str(meta)) 
                
        for link in link_data:
            styles.append(link)
                
        if elements:
            for element in elements:
                for subTitle in element.select("ul.sub-tab.clearfix > li.active"):
                    data_dict["title"] = subTitle.get_text()
                    
        else:
            for title in soup.select("div.gnb-title > div > h3"):
                data_dict["title"] = title.get_text()
            
        for content in soup.select("div.contents_body"):
            for tag in content.find_all(['div', 'ul', 'div'], class_=['gnb-title', 'sub-tab', 'satisfaction']):
                tag.extract()
            
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