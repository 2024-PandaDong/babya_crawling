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
    region = "105030"
    current_list = list()
    result_data = []

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]
    format_url = base_url.split("/index")[0]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]

    url = f"{format_url}/sub03_03_01_01.do"
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    for i in soup.select("#snb > li.n3.on > ul.depth3_ul > li > a"):
        id_item = i.get("href").split("health/")[1]
        current_list.append(id_item)
                
    
    page_list = set(current_list) - set(collected_list)

    for page_id in page_list:
        page_url = f"{format_url}/{page_id}"
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
        subPage_list = []
        elements = soup.select("ul.tab-ul > li:not(.on) > a")
        
        # subPage가 있을때 (menu)
        if elements:
            for element in elements:
                id_item = element.get("href").split("health/")[1]
                subPage_list.append(id_item)
        
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

        for title in soup.select("#location > h2.page__title"):
            data_dict["title"] = title.get_text()
            
        for content in soup.select("#txt"):
            for tag in content.find_all("ul", class_="tab-ul"):
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
            
        # 최근수정일 없음
        
        data_dict["pageId"] = page_id
        data_dict["site"] = base_url
        data_dict["page"] = page_url
        
        if all(data_dict[key] is not None for key in ["title", "content"]):
            result_data.append(data_dict)
        
            
        # 서브 페이지 (메뉴바 같은거)
        for subPage_id in subPage_list:
            subPage_url = f"{format_url}/{subPage_id}"
            driver.get(subPage_url)
            time.sleep(2)
            subSoup = BeautifulSoup(driver.page_source, 'html.parser')
            
            data_dict = {
                "title": None,
                "content": None,
                "editDate": None,
                "pageId": None,
                "site": None,
                "page": None
            }
            
            styles = []
            
            for comment in subSoup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            for meta in subSoup.select("html > head > meta"):
                if meta.get("charset"):
                    styles.append(str(meta))
                
            for link in subSoup.select("html > head > link"):
                if link.get("rel")[0] == "stylesheet":
                    link_url = link.get("href")
                    link["href"] = urllib.parse.urljoin(base_url, link_url)
                    styles.append(str(link))

            for subTitle in subSoup.select("#location > h2.page__title"):
                data_dict["title"] = subTitle.get_text()
                
            for subContent in subSoup.select("#txt"):
                for tag in subContent.find_all("ul", class_="tab-ul"):
                    tag.extract()
                
                for img in subContent.find_all('img'):
                    img_url = img.get("src")
                    if img_url:
                        img["src"] = urllib.parse.urljoin(base_url, img_url)
                    
                for a in subContent.find_all("a", href=True):
                    file_url = a['href']
                    a['href'] = urllib.parse.urljoin(base_url, file_url)
                    
                styles_str = "".join(styles)
                content_str = re.sub(r'[\s\u00A0-\u00FF]+', " ", str(subContent))
                
                head_content = f"<head>{styles_str}</head>"
                body_content = f"<body>{content_str}</body>"
                
                html_content = f"<!DOCTYPE html><html>{head_content}{body_content}</html>"
                data_dict["content"] = html_content
                
            # 최근수정일 없음
            
            data_dict["pageId"] = subPage_id
            data_dict["site"] = base_url
            data_dict["page"] = subPage_url
            
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