import os
import subprocess

# Sejong 폴더 경로 가져옴
folder_path = os.path.dirname(os.path.abspath(__file__))

# Sejong 폴더 안의 모든 .py 파일을 리스트에 추가
script_list = [file for file in os.listdir(folder_path) if file.endswith('.py') and file != os.path.basename(__file__)]

def run_crawlers():
    print("지역: 세종\n\n")
    for script in script_list:
        print("행정 구역:", script.split(".")[0] + "\n")
        print(f"{script} 크롤링 하는 중...")
        result = subprocess.run(["python3", os.path.join(folder_path, script)], capture_output=True, text=True)
        print(result.stdout)  # 각 스크립트의 출력 결과를 확인
        if result.returncode != 0:
            print(f"Error running {script}: {result.stderr}")
        else:
            print(f"{script} 실행 완료")
            print("------------------------------------------------------")

if __name__ == "__main__":
    run_crawlers()