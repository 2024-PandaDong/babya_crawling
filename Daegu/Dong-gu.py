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

babya_server = "http://동바오.site"
region = "104040"
current_list = list()
result_data = []

site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
response_data = site_url.json()
base_url = response_data["data"]["policySiteUrl"]
format_url = base_url.split("/main")[0]

collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
old_list = [item["pageId"] for item in collected_site_data.json()["data"]]

url = f"{format_url}/contents.do?mid=0408010101"
driver.get(url)
time.sleep(2)
soup = BeautifulSoup(driver.page_source, 'html.parser')

for i in soup.select("li > div.mnu-tit-type2 > a > span"):
    if i.text == "모자보건":
        parent_div = i.find_parent('li')
        for j in parent_div.select("ul.depth3 > li > ul.depth4 > li > div.mnu-tit > a"):
            id_item = j.get("href").split("mid=")[1]
            current_list.append(id_item)


page_list = set(current_list) - set(old_list)

for page_id in page_list:
    page_url = f"{format_url}/contents.do?mid={page_id}"
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
    menu_element = soup.select("div.tab_depth05")
    
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
        
    for title in soup.select("ul.list05 > li > a.on > strong > span"):
        data_dict["title"] = title.get_text()
    
    for content in soup.select("#conts"):        
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
                for menu in element.select("ul.list03 > li > a"):
                    id_item = menu.get("href").split("mid=")[1]
                    menu_url = f"{format_url}/contents.do?mid={id_item}"
                    driver.get(menu_url)
                    time.sleep(2)
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    for menu_comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                        menu_comment.extract()
                    
                    for menu_content in soup.select("#conts"):
                        content_add += re.sub(r'[\s\u00A0-\u00FF]+', " ", str(menu_content).replace('"', "'").replace("href='#'","href='"+menu_url+"'")) + "\n"
            
                content_add += "</div>"
                content_str = content_add
                
                
        else:
            content_str = re.sub(r'[\s\u00A0-\u00FF]+', " ", str(content).replace('"', "'"))
            
        head_content = f"<head>{styles_str}</head>"
        body_content = f"<body>{content_str}</body>"
        
        html_content = f"<!DOCTYPE html><html>{head_content}{body_content}</html>"
        data_dict["content"] = html_content
                
                    
    for edit_date in soup.select("div.pageInfo.mT50 > div.dataOffer.clFix > dl.date > dd"):
        data_dict["editDate"] = ' '.join(edit_date.get_text().split())
    
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

driver.close()
sys.exit()

while True:
    pass