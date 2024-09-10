import re
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
region = "104030"

response1 = requests.get(f"{babya_server}/policy/site", params={"region": region})
response_data = response1.json()
base_url = response_data["data"]["policySiteUrl"]

response2 = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
old_list = [item["pageId"] for item in response2.json()["data"]]

url_data = [f"{base_url}?menu_id=00002309", f"{base_url}?menu_id=00002318"]
current_list = list()

# 모자보건사업, 출산지원사업
for url in url_data:
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    for i in soup.select("#side .snb > li.open > ul"):
        for j in i.select("li > a"):
            id_item = j.get("href").split("menu_id=")[1]
            current_list.append(id_item)

page_list = set(current_list) - set(old_list)
result_data = []


for page_id in page_list:
    page_url = f"https://www.dalseong.daegu.kr/healthcenter/index.do?menu_id={page_id}"
    driver.get(page_url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # 외부 css 파일 다운로드
    # css_links = soup.find_all('link', rel='stylesheet')
    # css_urls = [urllib.parse.urljoin(url, link['href']) for link in css_links]
    
    # external_css = ""
    # for css_url in css_urls:
    #     css_response = requests.get(css_url)
    #     external_css += css_response.text + "\n"
        
    data_dict = {
        "title": None,
        "content": None,
        "editDate": None,
        "pageId": None,
        "site": None
    }

    # title 데이터
    for title in soup.select("#content > header.cont_head > h1.title"):
        data_dict["title"] = ' '.join(title.get_text().split())

    # content 데이터
    for content in soup.select("#content > div.cont_body"):
        # 이미지 처리
        for img in content.find_all('img'):
            img_url = img.get("src")
            img["src"] = urllib.parse.urljoin(base_url, img_url)
            
        # 파일 처리
        for a in content.find_all("a", href=True):
            file_url = a['href']
            a['href'] = urllib.parse.urljoin(base_url, file_url)
        
        # 내부 <style> 태그를 생성하고 외부 CSS를 추가
        # style_tag = soup.new_tag('style')
        # style_tag.string = external_css
        
        # content.insert(0, style_tag)
        data_dict["content"] = re.sub(r'[\s\u00A0-\u00FF]+', " ", str(content).replace('"', "'"))

    # editDate 데이터
    for date in soup.select("#content > footer.cont_foot > div.cont_manager > dl.update > dd"):
        edit_date = ' '.join(date.get_text().split())
        format_editDate = ""
        
        if "." in edit_date:
            format_editDate = edit_date.replace(".", "-")
            
        data_dict["editDate"] = format_editDate

    # pageID 데이터
    data_dict["pageId"] = page_id
    
    # site 데이터
    data_dict["site"] = base_url

    result_data.append(data_dict)

# 크롤링한 페이지 개수
print(f"크롤링한 페이지 수: {len(result_data)}")

if (len(result_data) > 0):
    response3 = requests.post(f"{babya_server}/policy", json=result_data)
    print(response3.status_code)
    print(response3.text)

driver.close()

while True:
    pass
