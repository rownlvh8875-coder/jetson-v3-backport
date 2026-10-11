# jetson-v3-backport

> **2026-10-11 현재 기준:** 이번 작업은 Cinque V3 한 모델의 Jetson 구동을 위한
> 승인된 4A–5A 서버·콤마 연결 소프트웨어와 오프라인 검사까지 진행했습니다. [현재 상태](docs/PROJECT_STATE.md)와
> [최소 변경계획](docs/V3_JETSON_PLAN.md)을 먼저 확인하세요.
> 대상 ONNX의 전체 해시·크기·I/O가 일치했습니다. ORT CPU 수치 측정과 실제 TRT/Jetson 검증을 구분합니다.
> 아래 2026-10-05 기록의 다운로드·테스트 성공·6개 패치 적용 문구는 과거 기록입니다.
> 적용물은 고정 소스용 `jetson-production-v3.patch` / `comma-integration-v3.patch`와 experimental manifest입니다.
> V2가 기본이며 `CARROT_JETLINK_V3=1`은 지정 V3만 선택하는 실험 기능입니다.
> 실제 TensorRT/Jetson·USB 검증과 활성화(5B)는 별도 현장 승인 대기이며 장치를 변경하지 않았습니다.

> Cinque v3 주행 모델을 Jetson Orin Nano에서 돌리기 위한 백포트 작업 저장소

## 이게 뭔가요?

내 차(comma 4 + Jetson Orin Nano Super)에서는 지금까지 **Cinque v2** 모델이 돌아가고 있어요.
한편 USB eGPU 쪽에는 이미 **Cinque v3**가 올라가서 실주행 중이고요.

이 저장소는 **v3를 Jetson에서도 돌릴 수 있게** 만드는 작업물을 모아둔 곳이에요.
쉽게 말하면 "eGPU에서 되던 새 모델을 Jetson용으로 이식하는 공사"의 기록입니다.

## 왜 필요한가요?

- v2와 v3는 모델이 기억을 다루는 방식이 다릅니다 (v2: queued / v3: stateful)
- Jetson 쪽 추론 서버(jetlink)는 v2 방식만 알던 상태라, v3를 이해하도록 코드를 손봐야 합니다
- 그 손본 내용 + v3 모델 정보 파일이 이 저장소에 들어있습니다

## 폴더 설명

| 폴더/파일 | 내용 |
|---|---|
| `docs/V3_JETSON_PLAN.md` | 현재 패치 적용/원복·검사 및 별도 승인이 필요한 현장 절차 |
| `JETSON_SETUP_GUIDE.md` | 과거 설치 기록; 현재 적용 입력으로 사용하지 않음 |
| `REPORT.md` | 작업 전체 보고서 (배경, 한 일, 검증 결과, 남은 일) |
| `GPT_PROMPT.md` | 다른 AI에게 작업을 인계할 때 쓰는 프롬프트 |
| `artifacts/cinque_v3.json` | v3 모델의 입출력 정보 파일 (실제 ONNX에서 추출, 날조 없음) |
| `tools/build_trt_v3.py` | Jetson에서 TensorRT 엔진을 만드는 스크립트 |
| `tools/gen_cinque_v3_json.py` | cinque_v3.json을 생성한 스크립트 |
| `tools/onnx_meta_light.py` | 766MB ONNX를 메모리 적게 쓰고 읽는 파서 |
| `patches/` | 통합 패치 2개, hash manifest와 라이선스; 부분 패치 중복 적용 금지 |
| `jetlink/` | 백포트 핵심 구현 (spec/queues/registry) |
| `tests/` | CPU 계약·실제 적용본·Linux loopback·기존 회귀 (최신 결과는 PROJECT_STATE) |

## 어디서부터 시작하나요?

**개발 사본의 실험 재현과 현장 승인 준비** → [`V3_JETSON_PLAN.md`](docs/V3_JETSON_PLAN.md)

**전체 맥락**을 알고 싶으면 → [`REPORT.md`](REPORT.md)

**이 백포트의 위치**(구 jetlink 끼워맞추기 vs 최신 upstream, A/B 선택지) →
[`REPORT.md` 9장](REPORT.md#9-이-백포트의-위치-force-fit-vs-최신-upstream-2026-10-05-정리)

## 현재 상태 (2026-10-05)

**된 것:**
- v3 ONNX 다운로드 + 무결성 확인 (sha256 일치)
- `cinque_v3.json` 생성 (실측값, 테스트 38개 통과)
- 패치 6개 작성 + 적용 검증 (클론 저장소 기준)
- TensorRT 빌드 스크립트 작성
- GitHub 푸시 완료

**안 된 것 (Jetson 실기 필요):**
- TensorRT 엔진 실제 빌드
- 정지 상태 추론 테스트
- 주행 검증

## 주의

- 이 코드는 주행에 직결되는 추론 서버 코드입니다
- v3가 정지·재출발 흔들림을 개선한다는 증거는 아직 없습니다
- 주행 테스트 전에는 반드시 정지 상태 테스트를 먼저 통과해야 합니다
- 현재 실험 opt-in은 `CARROT_JETLINK_V3`입니다. 해제/원복은 현재 계획의 절차와 현장 승인을 따릅니다
