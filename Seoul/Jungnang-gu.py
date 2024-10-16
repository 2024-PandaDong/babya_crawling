import re
import sys
import time
import requests
import urllib.parse
from datetime import datetime
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
    region = "101250"
    current_list = list()
    result_data = []

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]
    format_url = base_url.split(".do")[0]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]
    
    url = f"{format_url}/contents.do?menuNo=400321"
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    for i in soup.select("ul.sub-menu > li.on > ul.sb-depth3 > li > ul.sb-depth4 > li > a"):
        id_item = i.get("href").split("menuNo=")[1]
        current_list.append(id_item)


    print(current_list)
    page_list = set(current_list) - set(collected_list)
    
    for page_id in page_list:
        page_url = f"{format_url}/contents.do?menuNo={page_id}"
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
                
        for title in soup.select("#center > h3"):
            data_dict["title"] = title.get_text()
            
        for edit_date in soup.select("div.sub-table1.mt60 > table > tbody > tr > td"):
            match = re.match(r'(\d{4})년(\d{2})월(\d{2})일', edit_date.get_text())
            if match:
                year, month, day = match.groups()
                formatted_date = datetime(int(year), int(month), int(day)).strftime('%Y-%m-%d')
                data_dict["editDate"] = formatted_date
            
        for content in soup.select("div.sub-center"):
            for tag in content.find_all(['div', 'form']):
                if tag.name == 'div' and tag.has_attr('class') and 'sub-table1' in tag['class'] and 'mt60' in tag['class']:
                    tag.extract()
                    
                elif tag.name == 'form' and tag.has_attr('id') and tag['id'] == 'satisfactionFrm':
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
            
            # print(data_dict["content"], "\n\n\n\n\n\n\n\n\n")
            
        data_dict["pageId"] = page_id
        data_dict["site"] = base_url
        
        if all(data_dict[key] is not None for key in ["title", "content"]):
            result_data.append(data_dict)
                

except Exception as e:
    print(f"Error: {e}")
    driver.close()
    sys.exit()

finally:
    driver.close()
    sys.exit()

while True:
    pass