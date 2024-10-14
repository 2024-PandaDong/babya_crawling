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
    babya_server = "http://동바오.site"
    region = "101100"
    link_list = list()
    current_list = list()
    result_data = []

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]

    url = f"{base_url}Contents.asp?code=10005062"
    driver.get(url)
    time.sleep(10)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    for i in soup.select("ul.depth1 > li.on > a > span"):
        if i.text == "모자보건":
            parent_div = i.find_parent("li")
            for j in parent_div.select("ul.depth2 > li > a"):
                id_item = j.get("href")
                if id_item and "javascript:" not in id_item:  # 자바스크립트 호출 링크 제외
                    if "?code=" in id_item:
                        id_item = id_item.split("?code=")[1]
                        link_list.append(id_item)

        
    for link in link_list:
        driver.get(f"{base_url}Contents.asp?code={link}")
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        elements = soup.select("div.tab1")
        
        if elements:
            for element in elements:
                for i in element.select("ul > li > a"):
                    id_item = i.get("href")
                    if id_item and "javascript:" not in id_item:  # 자바스크립트 호출 링크 제외
                        if "?code=" in id_item:
                            id_item = id_item.split("?code=")[1]
                            current_list.append(id_item)
                    
        else:
            current_list.append(link)
                
                
    page_list = set(current_list) - set(collected_list)

    for page_id in page_list:
        page_url = f"{base_url}Contents.asp?code={page_id}"
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
        
        # HTML 코드 주석 삭제
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
                
        for title in soup.select("#s_contents > div.s_con_tit > h3"):
            data_dict["title"] = title.get_text()
            
        for content in soup.select("#mainCont > div.part > div > div.bul"):
            for img in content.find_all('img'):
                if img.get("alt") == "미리보기": 
                    img.extract()     # 미리보기가 js로 구현되어 있어서 제거
                    
                else:
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
            
        for edit_date in soup.select("#survey > div.dataPerson2 > ul > li > p"):
            if re.match(r'^\d{4}-\d{2}-\d{2}$', edit_date.get_text()):
                data_dict["editDate"] = edit_date.get_text()
            
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