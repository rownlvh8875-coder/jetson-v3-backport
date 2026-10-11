# Cinque V3 Jetson — 1단계 조사 기준

조사일: 2026-10-11 (Asia/Seoul). 제품 코드 수정·장치 접속/변경·주행 없음.
현재 목표/제약은 [AGENTS.md](../AGENTS.md), 후속 작업은 [최소 변경계획](V3_JETSON_PLAN.md)을 따른다.
README/REPORT/GPT_PROMPT/설치 가이드의 과거 성공 문구는 아래의 현재 결과를 대체하지 않는다.

## 작업 기준점

| 항목 | 확인 결과 |
|---|---|
| 대화 시작 경로 | `C:\Users\user\Documents\Codex\2026-10-11\cinque-v3-jetson-1-cinque-v3` — 비어 있음, Git 저장소 아님 |
| 실제 개발 저장소 | 시작 경로 아래 `jetson-v3-backport`에 지정 원격을 새로 클론 |
| origin | `https://github.com/rownlvh8875-coder/jetson-v3-backport` |
| 최초 로컬 HEAD / 원격 main | `2519ad0bdbf6e796fa590063fc90d4d6461b6b8d` |
| 작업 브랜치 | `feature/cinque-v3-jetson` (main에서 생성) |
| 최초 차이 | `git rev-list --left-right --count HEAD...origin/main` → `0 0`, 미커밋 변경 없음 |
| 기존 이력 | 26 commits 보존. `3d315f92434657825673be7279f389e7ea1ea309` 안전성 테스트, `3794dd5bd6a1d9b8500f3e2b0ae28ace8b602a43` dtype seam, `7c8a67d310b6f2bd4742f788989079941ea92d3c` V3 patch/FP16 수정 등 |
| 기존 지침/진행 문서 | 이 저장소 및 적용되는 상위 경로에 AGENTS.md 없음. docs/ 두 파일도 없음. README, REPORT, SUMMARY_QA, GPT_PROMPT, JETSON_SETUP_GUIDE를 읽음 |

기존 개발 사본 검색 범위: Documents/Codex, Desktop, Downloads, `C:\openpilot`,
`D:\CyberPilot`, `D:\carrot-jetson-windows`. 대상 저장소 사본/개발 브랜치는 이 범위에서
발견하지 못했고, 원격 heads는 main 하나였다. 다른 사용자 작업/프로세스는 변경하지 않았다.
위 HEAD는 **제품 코드 조사·테스트 기준 SHA**다. 이후 문서 커밋의 HEAD/원격 상태는
최종 보고와 `git rev-parse HEAD`, `git ls-remote origin refs/heads/feature/cinque-v3-jetson`으로 확인한다.

## 고정 참고 코드

| 저장소 | 시작 시 조회·고정한 전체 SHA | 개발용 사본 |
|---|---|---|
| [carrot-jetson](https://github.com/ajouatom/carrot-jetson/tree/d0dc96fa32410403dfb2fefff3e2909c11ec109b) | `d0dc96fa32410403dfb2fefff3e2909c11ec109b` | `../references/carrot-jetson` (detached) |
| [openpilot carrot-wip](https://github.com/ajouatom/openpilot/tree/029ab60eb19e7b9d4d76bfee1ce99a7521934511) | `029ab60eb19e7b9d4d76bfee1ce99a7521934511` | `../references/openpilot` (detached, 관련 경로 sparse checkout) |

`git ls-remote` 후 해당 SHA를 fetch/checkout했고 `git rev-parse HEAD`로 대조했다.
참고 사본에는 제품 변경이 없다. carrot-jetson의 `third_party/jetlink/UPSTREAM.md`는
vendoring 원본을 `194ff6dc71cd27282378fff155e94daa7770152b`로 기록한다.
그러나 현재 파일 상태는 각 고정 저장소 SHA로 판단한다.
실제 장치의 Git SHA, JetPack/L4T/CUDA/TensorRT 버전은 **미확인**이다.
과거 REPORT의 L4T 36.4.7 / TensorRT 10.3.0 / Carrot R2는 과거 기록일 뿐이다.

## V3 원본 확보 상태

- 명세 기록: SHA256 `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`, `766354845` bytes.
- `artifacts/big_driving_supercombo_v3.onnx`는 없다. 검색한 로컬 모델 후보도 모두 불일치했다.
  저장소/위 개발 폴더 외에 `.cache`, OneDrive, `C:\Temp`, `D:\CarrotLogs`, `D:\carrotlog`도 검색했다.
  전체 PC/오프라인 볼륨/NAS에 없다고 단정하지 않는다.
- 전체 파일 해시를 계산한 후보: `D:\CarrotLogs\주행모델\driving_supercombo.onnx`는
  `96618974` bytes / `d0caa7d771cf9b905fca9db471d3413eed1b8b0611413f84c0da964e5992126e`;
  CyberPilot의 두 개발 사본은 각각 `60792584` / `f73a9e535523d5e9acb9e642c64e33d631825dc8ba74123757d107cedd047bb5`,
  `60918562` / `65a08adc31d5c456219687d99b7bf5e44d61dae2d49ea67850e76105c7248cce`.
  다른 CarrotLogs 사본은 133-byte LFS pointer였다. 대체 모델로 사용하지 않았다.
- 기존 출처 [HF tree API](https://huggingface.co/api/models/commaai/openpilot_driving_models/tree/main/f78ed37d-afad-4dbc-8050-40ea885eedde/12864)에서
  `big_driving_supercombo.onnx`의 LFS oid/size가 위 기록과 일치했다.
  [기존 다운로드 주소](https://huggingface.co/commaai/openpilot_driving_models/resolve/main/f78ed37d-afad-4dbc-8050-40ea885eedde/12864/big_driving_supercombo.onnx)의
  TLS 검증을 유지한 HEAD는 HTTP 200, Content-Length `766354845`였다.
  본문 다운로드/전체 해시/실제 I/O 재파싱은 하지 않았다. 출처 응답은 확보 완료 증거가 아니다.

| 진행 항목 | 현재 상태 |
|---|---|
| V3 원본 확보·전체 해시·I/O 대조 | BLOCKED — 대상 로컬 원본 미확보, 출처 metadata/HEAD만 확인 |
| 소프트웨어 테스트 | 일부 PASS, FAIL/환경 제약/SKIP 있음 (아래 실행 기록) |
| 실제 Jetson 엔진 빌드·반복 추론 | BLOCKED — 원본/실제 장치 환경 미확인 |
| 원본 대비 수치 검증 | SKIP — 실제 ONNX/ORT/TRT 없음, 허용오차 미정 |
| 실제 comma 연결·성능·state·복귀/알림 | BLOCKED — 실제 장치 검증은 후속 단계 |
| 주행 검증 | 이번 범위 밖, 미실시 |

## 실제 검사 기록

Windows 11, Python `3.14.7`, NumPy `2.5.2`, pytest `9.1.1`.
onnx/onnxruntime/tensorrt/cuda 모듈 없음. 패키지 업그레이드 없음.
아래 명령의 `$PY`는 PowerShell에서 다음 실행 파일이다.

```powershell
$PY = 'C:/Users/user/AppData/Local/Python/pythoncore-3.14-64/python.exe'
```

기본 작업 디렉터리는 개발 저장소. `WIP`는 위 carrot-wip SHA의 개발용 사본,
`JETSON`은 위 carrot-jetson SHA의 사본이다. 로그와 일회성 CPU 재현 스크립트는
저장소 밖 `../evidence/`에 보존하며 Git에 포함하지 않는다.
`--noconftest -o addopts=`는 하드웨어/전체 런타임을 초기화·정리하는 저장소 공통 fixture와
미설치 전체 스위트 플러그인을 제외한 독립 단위 검사다. 테스트 본문/assertion은 변경하지 않았다.
전체 openpilot 스위트나 장치 테스트 통과로 해석하지 않는다.

| 명령 / 코드 기준 | 실제 결과·exit | 분류·근거 / 로컬 로그 |
|---|---|---|
| `& $PY tests/test_backport.py` / `2519ad0…` | 36 passed, 0 failed, exit 0 | PASS; JSON/합성 state/V2 회귀 및 실제 네트워크 pointer 조회. 원본 I/O 검사 한 구간 SKIP. `backport-py314.log` |
| `& $PY tests/test_stateful_safety.py` / `2519ad0…` | 30개 PASS 후 FileNotFoundError, exit 1 | FAIL; 525행 identity negative 검사가 원본을 무조건 열어 중단. 실제 모델 recurrent/patch parity 두 구간 SKIP. `safety-py314.log` |
| `& $PY -m compileall -q jetlink tools tests` / `2519ad0…` | exit 0 | PASS, 문법만 검사 (실제 실행 아님). 실제 호출은 대화 폴더에서 각 경로 앞에 `jetson-v3-backport/`를 붙임 |
| `& $PY tools/build_trt_v3.py --help` / `2519ad0…` | exit 0 | PASS, argparse만 검사. `build-help.log` |
| JETSON: `& $PY -m pytest --noconftest -o addopts= -q tools/jetlink/test_download_model.py` | 4 passed, exit 0 | PASS; 합성 bytes/monkeypatch 다운로드, 실제 V3 다운로드 아님. `carrot-jetson-download.log` |
| WIP: `& $PY -m pytest --noconftest -o addopts= -q tools/jetlink/test_stateful_protocol.py` | 2 passed, 9 failed, exit 1 | FAIL (개발 OS 제약); 9건은 Windows socket의 `sendmsg` 부재. Linux/USB/Jetson 결함으로 단정하지 않는다. `carrot-wip-stateful.log` |
| WIP: `& $PY -m pytest --noconftest -o addopts= -q openpilot/selfdrive/modeld/tests/test_jetlink.py` | 17 passed, 5 skipped, exit 0 | PASS/SKIP; 모의 warp·IPC 경계/명세·deadline, Windows AF_UNIX 부재로 5건 SKIP. `carrot-wip-joining-focused.log` |
| WIP: `& $PY -m pytest --noconftest -o addopts= -q tools/jetlink/test_app_models.py -k 'model_spec_round_trip_and_parser_shapes or joining_model_uses_selected_buffers_parser_and_recurrence'` | collection error, exit 2 | BLOCKED; `daemon.py`의 Linux `fcntl` 없음. V3 parser/복귀 본문은 미실행. `carrot-wip-app-focused.log` |
| `& $PY ../evidence/audit_checks.py` / 개발 저장소 + WIP SHA | exit 0, 결함 재현 assertion 충족 | CPU 합성/mock 재현; **제품 동작 PASS가 아님**. state narrowing Inf, builder layer 접근/반환, ORT NaN gate, protocol2 V3 차단. `audit-checks.log` |
| `git -C <참고사본> apply --check <각 원본 patch>` | 6개 모두 exit 1 | FAIL; Windows CRLF 영향도 존재. 원본/참고 코드 변경 없음 |
| LF 사본으로 `git -C <참고사본> apply --cached --check <patch.lf>` | Jetson 4개 exit 0, comma 2개 exit 1 | PASS/FAIL; index 대상 읽기 검사만, 실제 적용 없음. comma 문맥 불일치 확정. 정규화 사본은 `../evidence/*.patch.lf` |

최초 `python tests/...` 두 호출은 WindowsApps 실행 별칭 때문에 exit 9009였다.
실행 파일을 명시하여 위 결과를 얻었다. 초기 WIP 합동 collection은 sparse checkout의
`openpilot.common` 부재와 `fcntl`로 중단(exit 2); 직접 의존 common을 checkout한 뒤
단독 test_jetlink를 실행했다. 합동 시도는 `carrot-wip-joining.log`에 남아 있다.
Ubuntu/Ubuntu-24.04의 기존 Python에는 NumPy/pytest가 없었다.
Ubuntu-24.04에서 `/tmp/cinque-v3-phase1-20261011`에 개발용 venv 생성을 시도했지만
ensurepip/python3-venv 부재로 exit 1, 이어진 해당 venv pip도 모듈 부재로 실패했다.
패키지는 설치되지 않았으며 운영/시스템 패키지 변경으로 확장하지 않았다. Linux 재실행은 BLOCKED다.
pytest는 미설치 asyncio/cpp 플러그인 설정 3개의 warning도 보고했다.

## 기존 기능과 미수행 범용 작업의 처리

`jetlink/spec.py`, `queues.py`, `patches/session.py.new`의 stateful/검증/초기화 구현과
현재 carrot-wip의 전처리·동적 packed·출력 parser·복귀를 재사용한다.
과거 리뷰의 finite/shape/warm/BuilderFlag/API 지적은 코드에서 이미 반영된 부분과
현재 남은 문제를 [계획](V3_JETSON_PLAN.md)에 분리했다.
`jetlink/registry/catalog.py`와 LFS resolver 등 범용 성격의 기존 코드는 보존한다.
대상 원본의 identity/pointer 확인에 필요한 부분만 재사용하며 카탈로그/CLI 확장은 하지 않는다.
이 저장소 26개 이력/파일에서 별도 범용 변환기·MDM 구현계획은 확인되지 않았다.
다른 대화/위치의 미수행 범용 작업은 이번 사용자 지시로 현재 목표에서 제외한다.
