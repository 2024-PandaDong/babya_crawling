import re
import sys
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_experimental_option("detach", True)
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

babya_server = "http://동바오.site"
region = "104080"
current_list = list()

site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
response_data = site_url.json()
base_url = response_data["data"]["policySiteUrl"]
format_url = base_url.split("/main")[0]

collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
old_list = [item["pageId"] for item in collected_site_data.json()["data"]]

class_data = ["898", "903"]

# 가끔씩 처음 페이지 들어갈 때 400에러 뜨는 버그
for class_id in class_data:
    driver.get(f"{format_url}/business/page.html?mc=0891")
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    for i in soup.select(f"ul.snb > li[class='{class_id}'] > ul > li > a"):
        id_item = i.get("href").split("mc=")[1]
        current_list.append(id_item)


page_list = set(current_list) - set(old_list)
result_data = []

for page_id in page_list:
    page_url = f"{format_url}/business/page.html?mc={page_id}"
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
    
    # HTML 코드 주석 삭제
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    # title
    for title in soup.select("#content > div.cont_head > h1.cont_tit"):
        data_dict["title"] = title.get_text()
        
    # content
    for content in soup.select("#content > div.con_wrap"):
        # 이미지 처리
        for img in content.find_all('img'):
            img_url = img.get("src")
            img["src"] = urllib.parse.urljoin(base_url, img_url)
            
        # 파일 처리
        for a in content.find_all("a", href=True):
            file_url = a['href']
            a['href'] = urllib.parse.urljoin(base_url, file_url)
          
        data_dict["content"] = re.sub(r'[\s\u00A0-\u00FF]+', " ", str(content).replace('"', "'"))
    
    # editDate
    for edit_date in soup.select_one("#content > div.cb_area > div.cb_head > div.info2 > span"):
        data_dict["editDate"] = edit_date.get_text().split(": ")[1].replace(".", "-")
    
    # pageId
    data_dict["pageId"] = page_id
    
    # site
    data_dict["site"] = base_url
    
    result_data.append(data_dict)


if (len(result_data) > 0):
    print(f"크롤링한 페이지 개수: [{len(result_data)}]")
    policy = requests.post(f"{babya_server}/policy", json=result_data)
    print(policy.status_code)
    print(policy.text)
    
else:
    print("아직 새로운 정책이 업데이트 되지 않았습니다.")


driver.close()
sys.exit()

while True:
    pass