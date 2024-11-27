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
    region = "112040"
    link_list = list()
    current_list = list()
    result_data = []

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]
    format_url = base_url.split("/kor")[0]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]
    
    url = f"{format_url}/menu.es?mid=a11209060401"
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    for i in soup.select("div.tab > div.tab_menu > div.tab_panel > ul.tab_list > li.tab_item > button > span"):
        if i.text == "모성관리사업" or i.text == "영유아보건사업":
            parent_element = i.find_parent("li")
            id_item = parent_element.get("onclick").split("?mid=")[1].split("'")[0]
            link_list.append(id_item)
            
    for link in link_list:
        driver.get(f"{format_url}/menu.es?mid={link}")
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        elements = soup.select("div.main_con_inner > div.tab > div.tab_menu > div.tab_panel")
        
        if elements:
            for element in elements:
                for i in element.select("ul.tab_list > li.tab_item"):
                    id_item = i.get("onclick").split("?mid=")[1].split("'")[0]
                    current_list.append(id_item)
                    
        else:
            current_list.append(link)
    

    page_list = set(current_list) - set(collected_list)

    for page_id in page_list:
        page_url = f"{format_url}/menu.es?mid={page_id}"
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
        
        styles = ["<style> #container { background-color: transparent !important; margin-top: 0 !important; } </style>"]
        
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
            
        for meta in soup.select("html > head > meta"):
            if meta.get("charset"):
                styles.append(str(meta))
            
        for link in soup.select("html > head > link"):
            if link.get("rel")[0] == "stylesheet":
                link_url = link.get("href")
                if "/health/layout.css" not in link_url:
                    link["href"] = urllib.parse.urljoin(base_url, link_url)
                    styles.append(str(link))
                
        for title in soup.select("div.main_con_inner > div.tab > div.tab_menu > div.tab_panel > ul.tab_list > li.active > button > span"):
            data_dict["title"] = title.get_text()
            
        for edit_date in soup.select("div.satisfy > div.leftCon > div.manager_info > ul.clearfix > li.n3"):
            for tag in edit_date.find_all("span"):
                tag.extract()
            
            editDate = edit_date.get_text().strip()
            match = re.match(r'(\d{4})년 (\d{2})월 (\d{2})일', editDate)
            if match:
                year, month, day = match.groups()
                formatted_date = f"{year}-{month}-{day}"
                data_dict["editDate"] = formatted_date
        
        for content in soup.select("#contents"):
            for tag in content.find_all("div", class_="satisfy"):
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
            body_content = f"<body><div id='container'>{content_str}</div></body>"
            
            html_content = f"<!DOCTYPE html><html>{head_content}{body_content}</html>"
            data_dict["content"] = html_content
        
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