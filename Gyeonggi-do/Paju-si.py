
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
    region = "102470"
    link_list = list()
    current_list = list()
    result_data = []

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]
    format_url = base_url.split("/index")[0]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]
    
    url = f"{format_url}/clinic_03/clinic_03_11/clinic_03_11_01/clinic_03_11_01_01.jsp"
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    for i in soup.select("#sidebar > ul.snb-list > li.on > ul > li > a"):
        id_item = i.get("href").split("clinic_03_11/")[1]
        link_list.append(id_item)
        
    for link in link_list:
        driver.get(f"{format_url}/clinic_03/clinic_03_11/{link}")
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        elements = soup.select("nav.tab-menu")
        
        if elements:
            for element in elements:
                for i in element.select("ul.tab-list > li > a"):
                    id_item = i.get("href").split("clinic_03_11/")[1]
                    current_list.append(id_item)
                    
        else:
            current_list.append(link)


    page_list = set(current_list) - set(collected_list)

    for page_id in page_list:
        page_url = f"{format_url}/clinic_03/clinic_03_11/{page_id}"
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
        elements = soup.select("nav.tab-menu")
        
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
            
        for meta in soup.select("html > head > meta"):
            if meta.get("charset"):
                styles.append(str(meta))
            
        for link in soup.select("html > head > link"):
            if link.get("rel")[0] == "stylesheet":
                link_url = link.get("href")
                link["href"] = urllib.parse.urljoin(base_url, link_url)
                styles.append(str(link))
            
        if elements:
            for element in elements:
                for title in element.select("ul.tab-list > li.on > a > span"):
                    text = title.get_text(separator=" ").strip()
                    title_text = re.sub(r'\s+', ' ', text)
                    data_dict["title"] = title_text
            
        else:    
            for title in soup.select("div.content-header > h2.content-title"):
                data_dict["title"] = title.get_text().strip()
        
        for content in soup.select("div.content-body"):
            for tag in content.find_all("nav", class_="tab-menu"):
                tag.extract()
            
            for img in content.find_all('img'):
                img_url = img.get("src")
                if img_url:
                    img["src"] = urllib.parse.urljoin(base_url, img_url)
            
            for a in content.find_all("a", href=True):
                file_url = a['href']
                if file_url == "#":
                    fileId = a.get("onclick").split("'")[1]
                    a['href'] = f"{format_url}/common/file/download.do?atchFileId={fileId}&fileSn="
                
                else:
                    a['href'] = urllib.parse.urljoin(base_url, file_url)
                
            styles_str = "".join(styles)
            content_str = re.sub(r'[\s\u00A0-\u00FF]+', " ", str(content))
            
            head_content = f"<head>{styles_str}</head>"
            body_content = f"<body>{content_str}</body>"
            
            html_content = f"<!DOCTYPE html><html>{head_content}{body_content}</html>"
            data_dict["content"] = html_content
            
        # 최근수정일 없음
        
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