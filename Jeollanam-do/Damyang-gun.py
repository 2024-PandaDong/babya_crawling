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
    region = "112070"
    current_list = list()
    result_data = []

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]
    format_url = base_url.split("/health")[0]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]
    
    current_list.append("712&domainId=DOM_0000005&menuCd=DOM_000000503001000000")

    page_list = set(current_list) - set(collected_list)

    for page_id in page_list:
        page_url = f"{format_url}/menu/goToContentsPage?contentsSid={page_id}"
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
        
        styles = ["""<style> :root,
        :root[data-theme="light"] {
            --Default: #209f84;
            --Background: #f5f5f5;
            --Primary: #209f84;
            --Primary-darker: #1a8c84;
            --Primary-darken: #0d6c66;
            --Secondary: #f6ba33;
            --Secondary-light: #fec866;
            --Greyscale9: #292a2b;
            --Greyscale8: #363a3c;
            --Greyscale7: #4d5256;
            --Greyscale6: #878d91;
            --Greyscale5: #a9afb3;
            --Greyscale4: #ced3d6;
            --Greyscale3: #e1e4e6;
            --Greyscale2: #eaeeef;
            --Greyscale1: #f1f5f5;
            --Greyscale0: #f8fafb;
            --Error: #d32f2f;
            --Warning: #f9a825;
            --Success: #4caf50;
            --information: #0091ea;
      } .tabConItem { display: block !important; } </style>"""]
        
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
            
        for meta in soup.select("html > head > meta"):
            if meta.get("charset"):
                styles.append(str(meta))
            
        for link in soup.select("html > head > link"):
            if link.get("rel")[0] == "stylesheet":
                link_url = link.get("href")
                if "ezss_v0_2.css?v=230000" not in link_url:
                    link["href"] = urllib.parse.urljoin(base_url, link_url)
                    styles.append(str(link))
        
        for title in soup.select("#dev-pageTitle"):
            data_dict["title"] = title.get_text()
        
        for content in soup.select("div.tab-area > div.tabCon"):
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