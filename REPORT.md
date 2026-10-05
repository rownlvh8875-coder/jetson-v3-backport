# Jetson V3 (Cinque Terre V3) 백포트 — 구현 보고서

작성: 2026-10-05 / Muse
요청: "Jetson에서 V3 모델이 동작하도록 코딩해달라"
업데이트: 2026-10-05 — 하드 블로커 해소 (cinque_v3.json 생성), 6개 패치 전부 적용·검증,
  Jetson용 TRT 빌드 스크립트 작성.

## 결론

**하드 블로커였던 `cinque_v3.json`을 실제 v3 ONNX에서 생성했다 (날조 없음).
6개 패치 전부 적용·검증 완료. 남은 것은 Jetson 실기 작업뿐이다:
TRT 10.3 엔진 빌드 → 정지 상태 passive 추론 테스트 → 주행 검증.**

## 배경 (검증된 사실)

- Cinque Terre V3 = PR #38932의 Cinque v3와 동일 체크포인트 (`f78ed37d`).
  ref `bf3e3631b3f91d92a1020a5e0dd4298b93ff4244` ("Use f78ed37d for the precompiled eGPU driving model")
- v3 ONNX 실체: HuggingFace `commaai/openpilot_driving_models`의
  `f78ed37d-afad-4dbc-8050-40ea885eedde/12864/big_driving_supercombo.onnx`
  (oid `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`, 766,354,845 bytes)
- v2 = queued 계약 (서버가 history queue 유지), v3 = stateful 계약 (openpilot #38916,
  그래프가 history를 내부에 유지). 입력: `new_img` + `desire` + `state_<q>` 3종,
  출력: `outputs`(18452) + `next_state_<q>` 3종.
- 사용자 Jetson: Carrot R2, L4T 36.4.7, TRT 10.3, vendored jetlink 0.3.0a1
  (프로토콜 v2, queued 전용). Upstream은 프로토콜 v3 + Swift 서버로 갈아엎어짐.

## 구현 내용 (patches/)

| 패치 | 대상 저장소/파일 | 상태 |
|---|---|---|
| jetson-spec-stateful.patch | `ajouatom/carrot-jetson` `third_party/jetlink/jetlink/spec.py` | 구현+테스트 |
| jetson-queues-stateful.patch | `ajouatom/carrot-jetson` `third_party/jetlink/jetlink/queues.py` | 구현+테스트 |
| jetson-lfs-export-fallback.patch | `ajouatom/carrot-jetson` `third_party/jetlink/jetlink/registry/lfs.py` | 구현+테스트 |
| jetson-session-stateful.patch | `ajouatom/carrot-jetson` `third_party/jetlink/jetlink/server/session.py` | 적용+검증 (2026-10-05) |
| comma-link-model-select.patch | `ajouatom/openpilot` (carrot-wip) `openpilot/selfdrive/modeld/jetlink/link.py` | 적용+검증 (2026-10-05) |
| comma-model-stateful.patch | `ajouatom/openpilot` (carrot-wip) `openpilot/selfdrive/modeld/jetlink/model.py` | 적용+검증 (2026-10-05) |

적용 검증 방법 (2026-10-05, VM):
- 3개 patch 파일의 정합성: `.orig`+patch=`.new` 바이트 단위 일치 확인.
- 적용 기준점: `carrot-jetson` 최신, `openpilot` carrot-wip @ e6a6284의
  실제 파일과 `.orig` 바이트 단위 일치 확인 후 적용.
- `session.py`: import 성공, `EngineHost._warm`의 `StatefulState` 분기,
  `_infer`의 `outputs[DRIVING_OUTPUT]`+`after_run` 분기 확인.
  (단, `DRIVING_OUTPUT`은 spec.py 패치와 함께 적용되어야 import된다.)
- `link.py`: 모델 선택 로직 실행 테스트 — 기본값 v2 fail-closed,
  `CARROT_JETLINK_MODEL_JSON=cinque_v3.json` → v3 stateful 스펙 로드 확인.
- `model.py`: py_compile 통과. `'prev_feat' in self.views` 분기는
  런타임(실기)에서만 검증 가능.
- 전체 openpilot 테스트 스위트는 이 VM에서 실행 불가
  (cereal/tinygrad 등 openpilot 런타임 없음). 위의 단위 검증만 수행.

설계 원칙:
- 텐서 이름을 하드코딩하지 않음. `state_pairs`는 ONNX에서 유도 (`state_<q>` → `next_state_<q>`).
- stateful에서도 wire 포맷(프로토콜 v2)은 동일: newest frame + scalars → outputs.
  comma가 보내던 `prev_feat`만 없어짐 (서버가 state를 내부 유지).
- v2 경로는 바이트 단위로 동일하게 동작 (회귀 테스트 통과).
- 모델 선택은 fail-closed: 기본값 v2 유지. v3는 `CARROT_JETLINK_MODEL_JSON`/`CARROT_JETLINK_MODEL_LABEL`
  환경변수로만 선택 (운영 반영 시 Params 기반으로 교체 권장).

## 검증됨 (tests/test_backport.py — 38개 전부 통과, 2026-10-05)

1. `spec.py`: v2 실측 spec → stateful 아님, `prev_feat` 유지 (회귀).
   upstream `tiny_stateful.spec.json` → stateful 감지, state pair 3종 정확,
   packed에 `prev_feat` 없음, wire 크기 정상. `to_dict`/`from_dict` 왕복.
2. `queues.py` `StatefulState`: reset 0 초기화, `step_into`가 `new_img`/`desire` 기록,
   `after_run`이 `next_state_*` → `state_*` 피드백, 다음 프레임까지 유지.
   `PolicyQueues` 회귀 정상.
3. `registry/lfs.py`: 실측 네트워크 테스트 —
   v3 ref `bf3e3631` → oid `404a18cf…`, size 766354845 (HuggingFace 실측 일치).
   v2 ref → 기존 in-tree 경로 정상 (회귀).
4. **`cinque_v3.json` (신규, 하드 블로커 해소)**:
   실제 v3 ONNX(766MB, sha256 `404a18cf…` 검증됨)에서 `tools/gen_cinque_v3_json.py`로 생성.
   stateful 확인, state pair 3종 정확, `outputs` 18452, packed에 `prev_feat` 없음,
   `model_hw` (128, 256), checkpoint에 `f78ed37d` 포함.
   **결정적 검증**: ONNX 그래프를 직접 재파싱해서 JSON의 모든 입출력 텐서
   이름·shape이 바이트 단위로 일치함을 확인 (날조 없음).
   실측 특이사항: v3의 `output_slices`는 v2와 동일 레이아웃
   (`hidden_state` 2066..18450 포함). 출력 텐서 구조는 그대로고,
   comma가 피드백하지 않을 뿐이다.
5. 패치 적용 검증 (위 "적용 검증 방법" 참조).

## 검증 안 됨 (Jetson 실기 필요)

1. **TRT 10.3에서 v3 ONNX 빌드 미확인.** `tools/build_trt_v3.py` 작성됨
   (Jetson 전용, 이 VM에서 실행한 적 없음 — 스크립트 상단에 명시).
   v3 ONNX의 opset이 TRT 10.3에서 파싱되는지는 Jetson 실측 필요.
2. **정지 상태 passive 추론 테스트 미실시.** finite 출력 확인, 프레임 시간 측정 필요.
   통과 전까지 주행 테스트 금지.
3. **주행 검증 미실시.** v3가 흔들림을 개선한다는 증거 없음. 별개로 검증 필요.

## 남은 순서 (사용자가 Jetson에서 할 일)

1. 이 저장소를 Jetson에 클론 (또는 파일 복사).
2. v3 ONNX 다운로드: `artifacts/`에 `big_driving_supercombo_v3.onnx` 배치
   (HuggingFace `commaai/openpilot_driving_models`의
   `f78ed37d-afad-4dbc-8050-40ea885eedde/12864/big_driving_supercombo.onnx`,
   sha256 `404a18cf…` 확인).
3. `artifacts/cinque_v3.json`을 comma의 `openpilot/selfdrive/modeld/jetlink/`에 배치.
4. 6개 패치 적용 (Jetson 4 + comma 2). `patches/*.patch` 사용.
5. Jetson에서 TRT 엔진 빌드: `python3 tools/build_trt_v3.py --onnx ... --spec ... --out ... --verify`
   (약 160초 예상).
6. `CARROT_JETLINK_MODEL_JSON=cinque_v3.json CARROT_JETLINK_MODEL_LABEL='Cinque v3'`
   환경변수로 v3 선택 후 정지 상태 passive 추론 테스트 (finite 출력 확인).
7. 이후 주행 검증은 별도 계획.

## 안전 주의

- 이 코드는 추론 서버 코드다. 버그는 주행에 직결된다.
- 실차 설정 변경·플래싱·자동 배포는 사용자 승인 없이 하지 않는다.
- v2를 기본값으로 유지 (fail-closed). v3는 명시적 선택 시에만.
