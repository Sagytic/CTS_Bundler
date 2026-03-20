# TR 오브젝트 사용처 분석 설계

- **구현**: `api/views/analyze.py` (LangGraph 배포 심의 워크플로 내 `node_fetch_and_score`, `node_report_generator`).
- **AI/워크플로 기술 전반**: [`AI_TECH.md`](./AI_TECH.md) 참고.

## 1. 단계 결정: 배포 요청 레포트에 통합

- **선택**: 별도 "테스트 요청 단계"를 두지 않고 **배포 요청 레포트 단계**에서 한 번에 진행.
- **이유**: (1) 사용처 데이터가 배포 리스크 레포트와 한눈에 보이는 것이 유리 (2) 한 번의 요청으로 TR + 사용처 + 모듈 검토 + 테스트 권장까지 완결 (3) 필요 시 나중에 "테스트 범위만 먼저 보기" 탭 추가 가능.

## 2. SAP SICF 응답 스펙 (action=object_usage)

- **요청**: `action=object_usage`, `trkorr=EDAK901372`
- **응답 JSON** (플랫 리스트, 오브젝트별로 Django에서 그룹핑):
```json
{
  "trkorr": "EDAK901372",
  "usages": [
    { "pgmid": "R3TR", "object": "ZMMR0030", "obj_type": "PROG", "caller": "ZMM_MAIN", "caller_type": "PROG", "operation": "CALL" },
    { "pgmid": "R3TR", "object": "EKKO", "obj_type": "TABL", "caller": "ZMMR0030", "caller_type": "PROG", "operation": "MODIFY" },
    { "pgmid": "R3TR", "object": "EKKO", "obj_type": "TABL", "caller": "ZMMR0030", "caller_type": "PROG", "operation": "SELECT" }
  ]
}
```

- **operation** 값: `CALL`, `SUBMIT`, `MODIFY`, `UPDATE`, `INSERT`, `DELETE`, `APPEND`, `SELECT`, `TABLE_REF`(테이블 참조만 구분 불가 시).

## 3. Django 플로우

1. **node_fetch_and_score**  
   - TR 목록·리스크 산출 후, **selected_trs** 각각에 대해 `fetch_object_usage_via_http(trkorr)` 호출.  
   - 결과를 리스트로 합쳐 **state["object_usage_data"]**에 저장. (실패 시 빈 리스트)

2. **node_report_generator (아키텍트)**  
   - **state["object_usage_data"]**를 프롬프트에 포함.  
   - 보고서에 **### 4. TR 오브젝트 사용처 및 테스트 권장** 섹션 추가:  
     - 오브젝트별로 (호출/SUBMIT/MODIFY/UPDATE/INSERT/DELETE/APPEND/SELECT) 사용처와 **테스트 권장 프로그램**을 나열.  
   - 이후 기존 4→5(수석 요약), 5→6(최종 결론).

## 4. 레포트 문구 구조 (아키텍트 지시)

- "아래 [TR 오브젝트 사용처] 데이터를 반드시 반영하세요."
- "각 오브젝트에 대해 **어디서(프로그램/클래스)** **어떤 연산(호출/SUBMIT/MODIFY/UPDATE/INSERT/DELETE/APPEND/SELECT)**으로 사용되는지** 요약하고, **그 프로그램들에 대한 테스트가 필요함**을 명시하세요."
