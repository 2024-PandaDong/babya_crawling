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
    region = "104030"
    current_list = list()

    site_url = requests.get(f"{babya_server}/policy/site", params={"region": region})
    response_data = site_url.json()
    base_url = response_data["data"]["policySiteUrl"]

    collected_site_data = requests.get(f"{babya_server}/policy/catalog", params={"site": base_url})
    collected_list = [item["pageId"] for item in collected_site_data.json()["data"]]

    url_data = [f"{base_url}?menu_id=00002309", f"{base_url}?menu_id=00002318"]

    # 모자보건사업, 출산지원사업
    for url in url_data:
        driver.get(url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        for i in soup.select("#side .snb > li.open > ul"):
            for j in i.select("li > a"):
                id_item = j.get("href").split("menu_id=")[1]
                current_list.append(id_item)

    page_list = set(current_list) - set(collected_list)
    result_data = []


    for page_id in page_list:
        page_url = f"https://www.dalseong.daegu.kr/healthcenter/index.do?menu_id={page_id}"
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
        
        styles = [] # link 태그 리스트
        
        # HTML 코드 주석 삭제
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
            
        # 해당 문서의 문자 인코딩 방식 가져오기
        for meta in soup.select("html > head > meta"):
            if meta.get("charset"):
                styles.append(str(meta))
            
        # 외부 스타일 시트와 연결된 link 태그 가져오기
        for link in soup.select("html > head > link"):
            if link.get("rel")[0] == "stylesheet":
                link_url = link.get("href")
                link["href"] = urllib.parse.urljoin(base_url, link_url) # 상대 경로를 절대 경로로 수정
                styles.append(str(link))

        # title 데이터
        for title in soup.select("#content > header.cont_head > h1.title"):
            data_dict["title"] = ' '.join(title.get_text().split())

        # content 데이터
        for content in soup.select("#content > div.cont_body"):
            # 이미지 처리
            for img in content.find_all('img'):
                img_url = img.get("src")
                if img_url:
                    img["src"] = urllib.parse.urljoin(base_url, img_url)
                
            # 파일 처리
            for a in content.find_all("a", href=True):
                file_url = a['href']
                a['href'] = urllib.parse.urljoin(base_url, file_url)
            
            styles_str = "".join(styles)
            content_str = re.sub(r'[\s\u00A0-\u00FF]+', " ", str(content).replace('"', "'"))
            
            head_content = f"<head>{styles_str}</head>"
            body_content = f"<body>{content_str}</body>"
            
            html_content = f"<!DOCTYPE html><html>{head_content}{body_content}</html>"
            data_dict["content"] = html_content
            
        # editDate 데이터
        for date in soup.select("#content > footer.cont_foot > div.cont_manager > dl.update > dd"):            
            data_dict["editDate"] = ' '.join(date.get_text().split()).replace(".", "-")

        # pageID 데이터
        data_dict["pageId"] = page_id
        
        # site 데이터
        data_dict["site"] = base_url

        # 딕셔너리의 값의 title, content 값이 None이 아닐때만 서버로 보낼 데이터 값 삽입
        if all(data_dict[key] is not None for key in ["title", "content"]):
            result_data.append(data_dict)
        

    if (len(result_data) > 0):
        # 크롤링한 페이지 개수
        print(f"크롤링한 페이지 수: [{len(result_data)}]")
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
