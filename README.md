# jetson-v3-backport

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
| `JETSON_SETUP_GUIDE.md` | **Jetson에서 직접 따라하는 단계별 가이드** (이것부터 보세요) |
| `REPORT.md` | 작업 전체 보고서 (배경, 한 일, 검증 결과, 남은 일) |
| `GPT_PROMPT.md` | 다른 AI에게 작업을 인계할 때 쓰는 프롬프트 |
| `artifacts/cinque_v3.json` | v3 모델의 입출력 정보 파일 (실제 ONNX에서 추출, 날조 없음) |
| `tools/build_trt_v3.py` | Jetson에서 TensorRT 엔진을 만드는 스크립트 |
| `tools/gen_cinque_v3_json.py` | cinque_v3.json을 생성한 스크립트 |
| `tools/onnx_meta_light.py` | 766MB ONNX를 메모리 적게 쓰고 읽는 파서 |
| `patches/` | Jetson 4개 + comma 2개, 총 6개의 패치 파일 |
| `jetlink/` | 백포트 핵심 구현 (spec/queues/registry) |
| `tests/` | 테스트 코드 (38개, 전부 통과) |

## 어디서부터 시작하나요?

**Jetson 실기 작업**을 하려면 → [`JETSON_SETUP_GUIDE.md`](JETSON_SETUP_GUIDE.md)

**전체 맥락**을 알고 싶으면 → [`REPORT.md`](REPORT.md)

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
- 이상 시 `CARROT_JETLINK_MODEL_JSON` 환경변수를 지우면 v2로 복귀합니다 (fail-closed)
