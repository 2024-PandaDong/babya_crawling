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
    region = "111150"
    current_list = list()
    result_data = []

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]
    format_url = base_url.split("/main")[0]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]
    
    url = f"{format_url}/contents.do?mId=0807000000"
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    for i in soup.select("nav > ul.snb > li > a"):
        if i.text == "출산지원사업":
            parent_element = i.find_parent("li")
            for j in parent_element.select("li > ul > li > a"):
                if j.text != "아기예방접종시기" and j.text != "출산예정일 알아보기":
                    id_item = j.get("href").split("?mId=")[1]
                    current_list.append(id_item)
    

    page_list = set(current_list) - set(collected_list)

    for page_id in page_list:
        page_url = f"{format_url}/contents.do?mId={page_id}"
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
                
        for title in soup.select("#tit_wrap > h3"):
            data_dict["title"] = title.get_text()
        
        for content in soup.select("#conts"):
            for tag in content.find_all("p", class_="btnboxR"):
                tag.extract()
            
            for tag in content.find_all("ul", id="depth05Top"):
                tag.extract()
            
            for img in content.find_all('img'):
                img_url = img.get("src")
                if img_url:
                    img["src"] = urllib.parse.urljoin(base_url, img_url)
            
            for a in content.find_all("a", href=True):
                file_url = a['href']
                if file_url == "#":
                    path, filename = a.get("onclick").split("'")[3], a.get("onclick").split("'")[1]
                    a['href'] = f"{format_url.split('/health')[0]}/common/jsp/common/contentFileDownload.jsp?path={path}&file={filename}"
                
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