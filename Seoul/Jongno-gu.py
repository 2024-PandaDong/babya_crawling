import re
import sys
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup, Comment
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_experimental_option("detach", True)
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

try:
    babya_server = "http://babyaapi.xn--2q1b39m2ui.site"
    region = "101230"
    current_list = list()
    result_data = []

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]
    format_url = base_url.split("/healthMain")[0]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]

    url = f"{format_url}/Health.do?menuId=400836&menuNo=400836"
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    for i in soup.select("ul.lnb-depth1 > li > a.btn.btn-toggle.on > span"):
        if i.text == "모자보건 사업":
            parent_li = i.find_parent("li")
            for j in parent_li.select("li > ul > li > a"):
                id_item = j.get("href").split("menuId=")[1].split("&")[0]
                current_list.append(id_item)
                
                    
    page_list = set(current_list) - set(collected_list)

    for page_id in page_list:
        page_url = f"{format_url}/Health.do?menuId={page_id}&menuNo={page_id}"
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
            
        for title in soup.select("#content > div.content-head > h3"):
            data_dict["title"] = title.get_text()
            
        for content in soup.select("div.content-body > div.sub_main"):
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

        for edit_date in soup.select("#content > div.content-bottom > ul > li > p.con"):
            date_str = edit_date.get_text(strip=True).split('최종수정일: ')[-1].strip(')')
            match = re.match(r'(\d{4})년(\d{2})월(\d{2})일', date_str)
            if match:
                year, month, day = match.groups()
                formatted_date = f"{year}-{month}-{day}"
                data_dict["editDate"] = formatted_date
                
        data_dict["pageId"] = page_id
        data_dict["site"] = base_url
        
        # 딕셔너리의 값의 title, content 값이 None이 아닐때
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