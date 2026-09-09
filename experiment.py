import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
import os

# --- 설정 (Settings) ---
SERVER_URL = "http://localhost:8000"
IMAGE_PATH = "test_image.jpg" # 사진 파일명 맞는지 꼭 확인!
USER_PROMPT = "이 교구를 활용해서 5세 유아들이 할 수 있는 창의적인 놀이 활동을 추천해줘."
ITERATIONS = 10

# API 엔드포인트
API_EXTRACT = f"{SERVER_URL}/api/extract"
API_CARDS = f"{SERVER_URL}/api/cards"
API_LESSON = f"{SERVER_URL}/api/lesson"

def run_experiment():
    if not os.path.exists(IMAGE_PATH):
        print(f"🚨 오류: '{IMAGE_PATH}' 파일이 없습니다. 사진을 backend 폴더 안에 넣고 이름을 맞춰주세요.")
        return

    results = []
    print(f"🚀 Edu-Bridge 시스템 성능 평가 시작 (총 {ITERATIONS}회 반복)\n")

    for i in range(1, ITERATIONS + 1):
        print(f"--- [ {i}회차 측정 중... ] ---")
        
        try:
            # 1. 키워드 추출 단계
            start_total = time.time()
            start_stage1 = time.time()
            
            with open(IMAGE_PATH, "rb") as f:
                files = {"image": (IMAGE_PATH, f, "image/jpeg")}
                data = {"text": USER_PROMPT}
                resp1 = requests.post(API_EXTRACT, files=files, data=data)
            
            resp1.raise_for_status()
            extract_data = resp1.json()
            search_query = extract_data.get("search_query", "") 
            stage1_time = time.time() - start_stage1
            
            # 2. 다국가 카드 추천 단계
            start_stage2 = time.time()
            
            card_payload = {
                "search_query": search_query,
                "age": 5,                
                "duration": 30,          
                "offset": 0,             
                "total_pool_size": 10    
            }
            
            resp2 = requests.post(API_CARDS, json=card_payload)
            resp2.raise_for_status()
            
            cards_data = resp2.json()
            cards = cards_data.get("cards", []) if isinstance(cards_data, dict) else cards_data
            stage2_time = time.time() - start_stage2
            
            # 3. 지도안 생성 단계 (Stage F) 측정
            start_stage3 = time.time()
            
            # 💡 422 에러 해결: 2단계(resp2)의 응답 데이터를 활용해 필수 필드 구성
            cards_full_data = resp2.json()
            cards_list = cards_full_data.get("cards", [])
            
            # 첫 번째 카드를 선택했다고 가정하고 페이로드 구성
            lesson_payload = {
                "search_query": search_query,
                "age": 5,
                "duration": 30,
                "selected_card": cards_list[0] if cards_list else {},
                "retrieval_chunks": cards_full_data.get("retrieval_chunks", {})
            }
            
            resp3 = requests.post(API_LESSON, json=lesson_payload)
            resp3.raise_for_status()
            
            stage3_time = time.time() - start_stage3
            total_time = time.time() - start_total
            
            results.append({
                "Iteration": i,
                "Stage1_Extract(s)": round(stage1_time, 2),
                "Stage2_RAG(s)": round(stage2_time, 2),
                "Stage3_Lesson(s)": round(stage3_time, 2),
                "Total_Time(s)": round(total_time, 2)
            })
            
            print(f"✅ 완료 -> 추출: {stage1_time:.2f}초 | RAG검색: {stage2_time:.2f}초 | 생성: {stage3_time:.2f}초 | 총: {total_time:.2f}초")
            
            # 💡 500 에러(할당량 초과) 완벽 방어 파트! 25초 대기
            if i < ITERATIONS:
                print("⏳ Gemini 무료 버전 API 요청 제한 방지를 위해 25초 대기합니다...")
                time.sleep(25)
            
        except Exception as e:
            print(f"🚨 {i}회차 중 오류 발생: {e}")
            if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
                print(f"   🔍 서버 상세 에러: {e.response.text}")
            
            # 에러가 나도 다음 회차를 위해 25초 쉬어줍니다.
            print("⏳ 에러 발생, API 쿨타임을 위해 25초 대기 후 다음 회차 진행...")
            time.sleep(25)
            
    # --- 결과 저장 및 시각화 ---
    if not results:
        print("\n❌ 에러로 인해 저장할 결과가 없습니다.")
        return

    df = pd.DataFrame(results)
    df.to_csv("experiment_results.csv", index=False)
    print("\n✅ 전체 결과가 'experiment_results.csv'에 저장되었습니다.")
    
    mean_df = df.mean().round(2)
    print("\n📊 [ 평균 소요 시간 ]")
    print(mean_df)
    
    plt.rcParams['font.family'] = 'AppleGothic'
    plt.rcParams['axes.unicode_minus'] = False
    
    stages = ['키워드 추출', 'RAG 검색 및 추천', '지도안 자동생성']
    means = [mean_df['Stage1_Extract(s)'], mean_df['Stage2_RAG(s)'], mean_df['Stage3_Lesson(s)']]
    
    plt.figure(figsize=(8, 5))
    bars = plt.bar(stages, means, color=['#7f7fd5', '#86a8e7', '#91eae4']) # 논문용 차분한 색상
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.1, f"{yval}초", ha='center', va='bottom', fontweight='bold')
        
    plt.title('Edu-Bridge 단계별 평균 소요 시간 (10회 반복 측정)', fontsize=14, fontweight='bold')
    plt.ylabel('소요 시간 (초)', fontsize=12)
    plt.ylim(0, max(means) * 1.3)
    
    plt.tight_layout()
    plt.savefig('latency_chart.png', dpi=300)
    print("✅ 논문용 그래프가 'latency_chart.png'로 저장되었습니다.")

if __name__ == "__main__":
    run_experiment()