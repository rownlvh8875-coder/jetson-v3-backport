# Jetson V3 (Cinque Terre V3) 백포트 — 구현 보고서

작성: 2026-10-05 / Muse
요청: "Jetson에서 V3 모델이 동작하도록 코딩해달라"

## 결론

**핵심 3개 파일은 구현 + 테스트 완료. 나머지 3개는 패치 작성 (미실행).
실차 적용을 막는 하드 블로커 1개가 남아 있다: `cinque_v3.json`은 실제 v3 ONNX에서
생성해야 하며, 날조할 수 없다.**

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
| jetson-session-stateful.patch | `ajouatom/carrot-jetson` `third_party/jetlink/jetlink/server/session.py` | 작성 (미실행) |
| comma-link-model-select.patch | `ajouatom/openpilot` (carrot-wip) `openpilot/selfdrive/modeld/jetlink/link.py` | 작성 (미실행) |
| comma-model-stateful.patch | `ajouatom/openpilot` (carrot-wip) `openpilot/selfdrive/modeld/jetlink/model.py` | 작성 (미실행) |

설계 원칙:
- 텐서 이름을 하드코딩하지 않음. `state_pairs`는 ONNX에서 유도 (`state_<q>` → `next_state_<q>`).
- stateful에서도 wire 포맷(프로토콜 v2)은 동일: newest frame + scalars → outputs.
  comma가 보내던 `prev_feat`만 없어짐 (서버가 state를 내부 유지).
- v2 경로는 바이트 단위로 동일하게 동작 (회귀 테스트 통과).
- 모델 선택은 fail-closed: 기본값 v2 유지. v3는 `CARROT_JETLINK_MODEL_JSON`/`CARROT_JETLINK_MODEL_LABEL`
  환경변수로만 선택 (운영 반영 시 Params 기반으로 교체 권장).

## 검증됨 (tests/test_backport.py — 24개 전부 통과)

1. `spec.py`: v2 실측 spec → stateful 아님, `prev_feat` 유지 (회귀).
   upstream `tiny_stateful.spec.json` → stateful 감지, state pair 3종 정확,
   packed에 `prev_feat` 없음, wire 크기 정상. `to_dict`/`from_dict` 왕복.
2. `queues.py` `StatefulState`: reset 0 초기화, `step_into`가 `new_img`/`desire` 기록,
   `after_run`이 `next_state_*` → `state_*` 피드백, 다음 프레임까지 유지.
   `PolicyQueues` 회귀 정상.
3. `registry/lfs.py`: 실측 네트워크 테스트 —
   v3 ref `bf3e3631` → oid `404a18cf…`, size 766354845 (HuggingFace 실측 일치).
   v2 ref → 기존 in-tree 경로 정상 (회귀).

## 검증 안 됨 (하드 블로커)

1. **`cinque_v3.json` 미생성 — 실차 적용의 하드 블로커.**
   comma의 `validate_spec()`이 서버 spec과 바이트 단위로 일치해야 해서,
   실제 v3 ONNX에서 `spec_from_onnx`로 생성해야 한다. 766MB 파일이 필요하며,
   이 환경에서는 받지 않았다. 날조 금지.
2. **TRT 10.3에서 v3 ONNX 빌드 미확인.** 빌더 코드는 버전에 구애받지 않으나,
   v3 ONNX의 opset이 TRT 10.3에서 파싱되는지는 Jetson 실측 필요.
3. **session.py / model.py / link.py 패치 미실행.** 하드웨어 없이 실행 불가.
   코드는 generic하게 작성됐으나, 첫 적용은 반드시 passive observation
   (정지 상태 추론값 finite 확인)부터.
4. **주행 검증 미실시.** v3가 흔들림을 개선한다는 증거 없음. 별개로 검증 필요.

## 남은 순서

1. Jetson에서 v3 ONNX 다운로드 (lfs.py 패치 적용 후 `fetch_pointer(bf3e3631…)`).
2. `spec_from_onnx`로 `cinque_v3.json` 생성 → comma `modeld/jetlink/`에 배치.
3. 6개 패치 적용 (Jetson 4 + comma 2).
4. Jetson에서 TRT 엔진 빌드 (약 160초 예상).
5. 정지 상태 passive 추론 테스트 (finite 출력 확인).
6. 이후 주행 검증은 별도 계획.

## 안전 주의

- 이 코드는 추론 서버 코드다. 버그는 주행에 직결된다.
- 실차 설정 변경·플래싱·자동 배포는 사용자 승인 없이 하지 않는다.
- v2를 기본값으로 유지 (fail-closed). v3는 명시적 선택 시에만.
