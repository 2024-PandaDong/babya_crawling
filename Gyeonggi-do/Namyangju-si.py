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
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

# 네트워크 기능 활성화
driver.execute_cdp_cmd('Network.enable', {})
# 특정 URL 패턴을 기반으로 네트워크 요청 차단
driver.execute_cdp_cmd('Network.setBlockedURLs', {'urls': ['*jquery*']})


try:
    region = "102120"
    link_list = list()
    current_list = list()
    result_data = []

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]
    format_url = base_url.split("/index")[0]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]
    
    url = f"{format_url}/contents.do?key=416"
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    for i in soup.select("li.depth1_item > div.depth2 > ul.depth2_list > li.depth2_item > a.depth2_text"):
        if i.text == "모자보건사업":
            parent_element = i.find_parent("li")
            for j in parent_element.select("div.depth3 > ul.depth3_list > li.depth3_item > a.depth3_text"):
                id_item = j.get("href").split("?key=")[1]
                link_list.append(id_item)
    
    for link in link_list:
        driver.get(f"{format_url}/contents.do?key={link}")
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        elements = soup.select("div.tabmenubox")
        
        if elements:
            for element in elements:
                for i in element.select("div.tab_wrap > ul.tab_list > li.tab_item > a.tab_link"):
                    id_item = i.get("href").split("?key=")[1]
                    current_list.append(id_item)
                    
        else:
            current_list.append(link)

    page_list = set(current_list) - set(collected_list)

    for page_id in page_list:
        page_url = f"{format_url}/contents.do?key={page_id}"
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
            
        for title in soup.select("header.sub_head > div.sub_title > h2"):
            data_dict["title"] = title.get_text()
        
        for content in soup.select("#contents"):
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
            
        for edit_date in soup.select("footer.satisfaction > div.manager_info > ul.clearfix > li"):
            for tag in edit_date.find_all("span"):
                tag.extract()
                
            editDate = edit_date.get_text().strip()
            if re.match(r"^\d{4}.\d{2}.\d{2}$", editDate):
                data_dict["editDate"] = editDate.replace(".", "-")
        
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