# Edu-Bridge

## 초코소라빵 RAG 백엔드

10개국 유아교육과정 RAG 시스템의 백엔드입니다.

---

## 프로젝트 구조

```text
Edu-Bridge/
├── backend/
│   ├── data/
│   │   ├── all_chunks.json
│   │   ├── all_countries.json
│   │   └── countries/
│   │
│   ├── db/
│   │   ├── load_data.py
│   │   └── quick_search_test.py
│   │
│   ├── services/
│   │   ├── retriever.py
│   │   ├── reranker.py
│   │   ├── card_generator.py
│   │   └── lesson_planner.py
│   │
│   ├── prompts/
│   │
│   ├── main.py
│   ├── requirements.txt
│   └── README.md
│
├── frontend/
│
├── .gitignore
└── README.md
