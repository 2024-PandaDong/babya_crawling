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
region = "104050"
current_list = list()
result_data = []

site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
response_data = site_url.json()
base_url = response_data["data"]["policySiteUrl"]

collected_site = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
old_list = [item["pageId"] for item in collected_site.json()["data"]]

url = f"{base_url}?menu_id=00000621"
driver.get(url)
time.sleep(2)
soup = BeautifulSoup(driver.page_source, 'html.parser')

for i in soup.select("#mobile_first_li_00000550 > div.depth02 > ul > li"):
    is_chlid_element = i.find("ul")
    if is_chlid_element:
        for j in i.select("ul.clearfix > li > a"):
            id_item = j.get("href").split("menu_id=")[1]
            current_list.append(id_item)
            
    else: 
        for j in i.select("a"):
            id_item = j.get("href").split("menu_id=")[1]
            current_list.append(id_item)
        
page_list = set(current_list) - set(old_list)

for page_id in current_list:
    page_url = f"{base_url}?menu_id={page_id}"
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
    
    for title in soup.select("#content-item > #page-title"):
        data_dict["title"] = title.get_text()
        
    for content in soup.select("#content-item > #content-body"):
        for img in content.find_all('img'):
            img_url = img.get("src")
            img["src"] = urllib.parse.urljoin(base_url, img_url)
            
        for a in content.find_all("a", href=True):
            file_url = a['href']
            a['href'] = urllib.parse.urljoin(base_url, file_url)
            
        data_dict["content"] = re.sub(r'[\s\u00A0-\u00FF]+', " ", str(content).replace('"', "'"))
        
    data_dict["pageId"] = page_id
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