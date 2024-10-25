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
    region = "108080"
    current_list = list()
    result_data = []

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]

    url = f"{base_url}health/mathernal_child/mother_sign.asp"
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    for i in soup.select("#leftmenu > ul.mb_hidden > li.right_bar.select.sublink > ul > li > a"):
        id_item = i.get("href").split("mathernal_child/")[1]
        current_list.append(id_item)
            
        
    page_list = set(current_list) - set(collected_list)

    for page_id in page_list:
        page_url = f"{base_url}health/mathernal_child/{page_id}"
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
        menu_element = soup.select("#tab")
        
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
                
        if menu_element:
            for title in soup.select("#leftmenu > ul.mb_hidden > li.right_bar.select.sublink > ul > li.select > a"):
                data_dict["title"] = title.get_text()
                    
        else:
            for title in soup.select("#contents > div.sub_title > h3"):
                data_dict["title"] = title.get_text().strip()

        for content in soup.select("#detail_con"):        
            for img in content.find_all('img'):
                img_url = img.get("src")
                if img_url:
                    img["src"] = urllib.parse.urljoin(base_url, img_url)
                
            for a in content.find_all("a", href=True):
                file_url = a['href']
                a['href'] = urllib.parse.urljoin(base_url, file_url)
            
            styles_str = "".join(styles)
            content_str = ""
            
            if menu_element:
                for element in menu_element:
                    content_add = "<div>\n"
                    for menu in element.select("ul.col2 > li > p > a"):
                        id_item = menu.get("href").split("mathernal_child/")[1]
                        menu_url = f"{base_url}health/mathernal_child/{id_item}"
                        driver.get(menu_url)
                        time.sleep(2)
                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        
                        for menu_comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                            menu_comment.extract()
                        
                        for menu_content in soup.select("#detail_con"):
                            content_add += re.sub(r'[\s\u00A0-\u00FF]+', " ", str(menu_content).replace("href='#'","href='"+menu_url+"'")) + "\n"
                
                    content_add += "</div>"
                    content_str = content_add
                    
                    
            else:
                content_str = re.sub(r'[\s\u00A0-\u00FF]+', " ", str(content))
                
            head_content = f"<head>{styles_str}</head>"
            body_content = f"<body>{content_str}</body>"
            
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