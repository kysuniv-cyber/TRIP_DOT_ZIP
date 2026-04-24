
# 🌍 TRIP\_DOT\_ZIP

## 사용자 맞춤형 실시간 여행 의사결정 지원 시스템 (AI Travel Agent)

## 📑 목차 (Table of Contents)

1.  [📌 프로젝트 개요](https://www.google.com/search?q=%231-%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8-%EA%B0%9C%EC%9A%94)
2.  [🖐🏻 팀 소개](https://www.google.com/search?q=%232-%ED%8C%80-%EC%86%8C%EA%B0%9C)
3.  [🛠 기술 스택](https://www.google.com/search?q=%233-%EA%B8%B0%EC%88%A0-%EC%8A%A4%ED%83%9D)
4.  [🧠 시스템 아키텍처](https://www.google.com/search?q=%234-%EC%8B%9C%EC%8A%A4%ED%85%9C-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98)
5.  [📈 주요 기능 및 화면](https://www.google.com/search?q=%235-%EC%A3%BC%EC%9A%94-%EA%B8%B0%EB%8A%A5-%EB%B0%8F-%ED%99%94%EB%A9%B4)
6.  [🎬 서비스 시나리오](https://www.google.com/search?q=%236-%EC%84%9C%EB%B9%84%EC%8A%A4-%EC%8B%9C%EB%82%98%EB%A6%AC%EC%98%A4)
7.  [📁 프로젝트 구조](https://www.google.com/search?q=%237-%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8-%EA%B5%AC%EC%A1%B0)

-----

## 1\. 📌 프로젝트 개요

### 📋 서비스 배경

  - **여행 계획의 피로도 해소**: 정보의 홍수 속에서 최적의 동선을 짜는 스트레스를 줄이고, 개인의 취향을 완벽히 반영한 일정을 제공하고자 합니다.
  - **정적 정보의 한계 극복**: 기존 챗봇은 미리 학습된 데이터나 고정된 리스트만 보여줍니다. 본 서비스는 \*\*실시간 외부 데이터(날씨, 영업 정보 등)\*\*를 반영하여 '지금 이 순간'에 가장 적합한 대안을 제시하는 **에이전트**형 서비스를 지향합니다.

### 🎯 핵심 목표

  - **LLM Function Calling 최적화**: 사용자의 의도를 분석해 날씨, 장소를 스스로 호출하는 지능형 로직 구현
  - **상황 적응형(Context-Aware) 추천**: 우천 시 실내 코스 자동 전환, 사용자 선호도 반영 등 유연한 의사결정 지원

### 💡 기대 효과

  - **의사결정 효율화**: 검색부터 동선 최적화까지 한 번에 해결하여 여행 준비 시간 단축
  - **여행 경험 최적화**: 실시간 변수(날씨 등)를 반영한 알맞은 장소를 추천하여 여행 만족도 극대화

-----

## 2\. 🖐🏻 팀 소개

## Team Trip Dot ZIP

여행의 모든 순간을 연결하는 다섯 마리의 똑똑한 땃쥐들입니다\!

| <img src="https://github.com/user-attachments/assets/dbf2ad25-c76b-413b-921c-253a754a2299" width="140" height="140"/> | <img src="https://github.com/user-attachments/assets/01ad856b-7ad4-48c2-b332-97bc1e2e266b" width="140" height="140"/> | <img src="https://github.com/user-attachments/assets/a9b311d2-8a04-4541-9a76-a4f54f4808ef" width="140" height="140"/> | <img src="https://github.com/user-attachments/assets/2639af6c-a878-452b-884f-cb58213a58e9" width="140" height="140"/> | <img src="https://github.com/user-attachments/assets/e452c87a-2a24-4f09-b9d2-73b51fdf7a0c" width="140" height="140"/>> |
|:---------------------------------------------------------------------------------------------------------------------:| :---: |:---------------------------------------------------------------------------------------------------------------------:| :---: |:----------------------------------------------------------------------------------------------------------------------:|
|                                                        **김이선**                                                        | **김지윤** |                                                        **박은지**                                                        | **위희찬** |                                                        **홍지윤**                                                         |
|                                                🛠️                 팀원                                                 | ✈️ 조장 |                                                         🌰 팀원                                                         | 🥜 대장 |                                                         🗺️ 팀원                                                         |
|                                            middleware 및 <br> streamlit 연동                                             | 프로젝트 총괄 <br> LLM 프롬프트 설계 |                                                 상세 업무 내용 <br> 업데이트 예정                                                 | 기술 아키텍처 설계 <br> 에이전트 로직 구현 |                                                 상세 업무 내용 <br> 업데이트 예정                                                  |
|                                      [GitHub](https://github.com/kysuniv-cyber)                                       | [GitHub](https://github.com/JiyounKim-EllyKim) |                                         [GitHub](https://github.com/lo1f0306)                                         | [GitHub](https://github.com/dnlgmlcks) |                                          [GitHub](https://github.com/jyh-skn)                                          |

-----

## 3\. 🛠 기술 스택

### **Core**

  - **LLM**: OpenAI GPT-4.1-mini (Function Calling 최적화 모델)
  - **Framework**: LangGraph (Agent & ReAct 로직 구현)

### **Data & API**

  - **External API**: OpenWeatherMap(날씨), Google Places(장소, 경로)
  - **Library**: Pandas (데이터 처리), Scikit-learn (장소 랭킹 알고리즘)

### **Frontend & Visualization**

  - **UI**: Streamlit (인터랙티브 웹 대시보드)
  - **Map**: Folium (경로 마커 및 시각화)

-----

## 4\. 🧠 시스템 아키텍처

1.  **사용자 입력**: 지역, 날짜, 날씨 조건 등 자연어 입력
2.  **LLM Planner**: 사용자의 의도를 분석하고 필요한 'Tool' 정의
3.  **Execution (Function Calling)**:
      - `get_weather()`: 실시간 기상 데이터 호출
      - `search_locations()`: 조건(실내/실외/예산)에 맞는 POI 검색
      - `get_real_travel_time()`: 이동시간 산출하여 동선 및 스케줄에 반영
4.  **Final Response**: 통합된 데이터 기반의 리포트 및 지도 시각화 출력

-----

## 5\. 📈 주요 기능 및 화면

### **1) 실시간 날씨 반응형 일정 생성**

  - 단순히 "추천해줘"가 아닌, 날씨 API 결과에 따라 `if Rain: indoor_mode=True` 로직을 수행하여 박물관, 실내 테마파크 위주의 동선 제공

### **2) 인터랙티브 경로 시각화**

  - 추천된 코스를 순서대로 지도 위에 표시하고, 장소별 상세 사유를 카드 형태로 제시

### **3) 사용자 선호도 반영**
    
  - 채팅 시작 전 페르소나 설정을 통해 사용자의 나이대, 동반인, 여행 취향 등을 반영하여 데이터 적재 및 맞춤 장소 추천

-----

## 6\. 🎬 서비스 시나리오

  - **상황**: "이번 주 토요일 강릉 당일치기, 예산 7만 원, 비 오면 실내 위주로 가고 싶어."
  - **에이전트 대응**:
    1.  사용자의 페르소나 확인
    2.  토요일 강릉 날씨 확인 (비 예보 감지)
    3.  강릉 내 평점 높은 실내 장소(아르떼뮤지엄 등) 검색
    4.  최단 거리 동선으로 일정표 및 지도 출력

-----

## 7\. 📁 데이터 플로우

```text
[User Input]
    ↓
[parse_user_input]
    ↓
[route_intent]
    ├── trip_plan
    │      ↓
    │ [extract_trip_requirements]
    │      ↓
    │ [check_missing_info]
    │      ├── missing 있음 → [ask_user_for_missing_info] → 사용자 응답 → [extract_trip_requirements]
    │      └── missing 없음
    │              ↓
    │      [decide_weather_need]
    │          ├── yes → [call_weather_tool]
    │          └── no
    │              ↓
    │      [search_places]
    │              ↓
    │      [evaluate_place_candidates]
    │          ├── 후보 부족 → [refine_place_search] → [search_places]
    │          ├── 후보 충분 + 선택 필요 → [present_place_options] → [collect_user_place_selection]
    │          └── 후보 충분 + 바로 진행
    │              ↓
    │      [generate_schedule]
    │              ↓
    │      [build_trip_response]
    │              ↓
    │             END
    │
    ├── weather_only
    │      ↓
    │ [extract_weather_query]
    │      ↓
    │ [call_weather_tool]
    │      ↓
    │ [build_weather_response]
    │      ↓
    │     END
    │
    ├── place_only
    │      ↓
    │ [extract_place_query]
    │      ↓
    │ [decide_weather_need_for_place]
    │      ├── yes → [call_weather_tool]
    │      └── no
    │      ↓
    │ [search_places]
    │      ↓
    │ [build_place_response]
    │      ↓
    │     END
    │
    ├── schedule_only
    │      ↓
    │ [extract_schedule_request]
    │      ↓
    │ [generate_schedule]
    │      ↓
    │ [build_schedule_response]
    │      ↓
    │     END
    │
    └── fallback_chat
           ↓
     [build_fallback_response]
           ↓
          END
```