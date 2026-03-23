# 테스트 실행 결과 로그 (증빙용)

이 폴더의 `pytest-output.txt`, `vitest-output.txt`는 **레포에서 최신 테스트를 한 번 돌린 결과 예시**입니다. 과제 제출 시 **스크린샷**과 함께 쓰거나, 아래 스크립트로 **본인 PC에서 다시 생성**해 덮어쓰면 됩니다.

## 다시 생성하기 (권장)

레포 **루트**에서:

```powershell
.\scripts\capture-test-results.ps1
```

`pytest-output.txt`(백엔드 34 tests), `vitest-output.txt`(프론트 16 tests)가 갱신됩니다.

### HTML 리포트(선택)

`pip install pytest-html` 후 스크립트가 `pytest-report.html`도 생성합니다(미설치 시 건너뜀).

## 수동으로만 할 때

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest 2>&1 | Tee-Object -FilePath ..\docs\E2E_EVIDENCE\test-outputs\pytest-output.txt
cd ..\frontend
npm run test:run 2>&1 | Tee-Object -FilePath ..\docs\E2E_EVIDENCE\test-outputs\vitest-output.txt
```

## 스크린샷

터미널에서 `capture-test-results.ps1` 실행 후 **맨 아래 요약 줄**(passed/failed, 시간)이 보이게 찍으면 됩니다. 자세한 절차는 [`../TEST_CAPTURE.md`](../TEST_CAPTURE.md).
