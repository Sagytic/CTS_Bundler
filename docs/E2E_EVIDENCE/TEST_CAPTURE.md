# pytest / vitest 테스트 증빙 캡처 가이드

과제·E2E 레포트에 **자동 테스트 실행 결과**를 올릴 때 사용합니다.

## 한 번에 실행 (권장)

레포 **루트**에서 PowerShell:

```powershell
.\scripts\capture-test-results.ps1
```

생성 위치: `docs/E2E_EVIDENCE/test-outputs/`

| 파일 | 내용 |
|------|------|
| `pytest-output.txt` | Django/pytest 전체 로그 |
| `vitest-output.txt` | 프론트 Vitest 전체 로그 |
| `pytest-report.html` | (선택) `pytest-html` 설치 시 |

## 스크린샷만 쓸 때

1. 위 스크립트 실행 후 터미널에서 **맨 아래 요약**(예: `34 passed`, `16 passed`)이 보이게 스크롤.
2. **Win + Shift + S**로 영역 캡처.
3. 글자가 작으면 터미널 폰트 크기 키운 뒤 다시 실행·캡처.

## HTML 리포트(선택)

```powershell
cd backend
.\venv\Scripts\python.exe -m pip install pytest-html
```

이후 `capture-test-results.ps1`가 `pytest-report.html`을 생성합니다. 브라우저에서 열고 전체 페이지 캡처 가능.

## CI(GitHub Actions)

`.github/workflows/ci.yml`가 돌면 **Actions 탭 → 해당 워크플로 → job 로그** 화면을 스크린샷해도 증빙으로 사용 가능.
