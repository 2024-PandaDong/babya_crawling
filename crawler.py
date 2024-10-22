import os
import subprocess

def run_crawlers_in_subfolders():
    # 현재 디렉토리 (루트 폴더) 가져옴
    root_folder = os.path.dirname(os.path.abspath(__file__))

    # 루트 폴더의 모든 하위 폴더 탐색
    for dirpath, dirnames, filenames in os.walk(root_folder):
        # 현재 폴더에서 실행 파일 찾기
        for filename in filenames:
            if filename == '_crawler.py':
                crawler_script_path = os.path.join(dirpath, filename)
                print(f"{crawler_script_path} 실행 중...\n\n\n")
                result = subprocess.run(["python3", crawler_script_path], capture_output=True, text=True)
                print(result.stdout)  # 출력 결과 확인
                if result.returncode != 0:
                    print(f"Error running {crawler_script_path}: {result.stderr}")
                else:
                    print(f"\n\n\n{crawler_script_path} 실행 완료\n\n\n\n\n")
                    print("--------------------------------------------------------------------------\n\n")

if __name__ == "__main__":
    run_crawlers_in_subfolders()
