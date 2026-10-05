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

---

# 2차 수정 — GPT 리뷰 18개 항목 반영 (2026-10-05)

외부 리뷰(GPT)가 지적한 fail-closed/state-consistency 문제들을 수정·재검증.
"동작한다"보다 상태 일관성과 실패 시 안전한 복귀를 우선.

## 1. 수정한 버그

### 1-A. [Critical] next_state finite 검증 누락
- 파일: `patches/session.py.new` (`_infer`, 구 771-776행 부근)
- 기존: `outputs`(18452개)만 finite 검사 후 `after_run()` 호출.
  `next_state_img_q/desire_q/feat_q`는 검사 없이 다음 프레임 state로 저장됨.
- 위험: `outputs`는 finite인데 `next_state_feat_q`가 NaN인 프레임이 통과하면
  다음 프레임의 recurrent state 전체가 오염됨. 이후 모든 프레임이 오염된
  state에서 추론 → 조향/가속 출력이 비정상.
- 수정: `_infer`에서 (1) `DRIVING_OUTPUT` 존재 확인 (없으면 `INFER_FAILED`),
  (2) `outputs` finite 확인, (3) `StatefulState.validate_next_states()`로
  next_state 3종의 존재·exact shape·dtype 호환성·finite를 전부 검증한 뒤에만
  `commit_next_states()`로 원자적 반영. 하나라도 실패하면 state를 건드리지
  않고 `NOT_FINITE`를 반환 → comma가 fallback 경로로 진입.
- 검증: `tests/test_stateful_safety.py` A/B/E (아래 3항 참조).

### 1-B. after_run 순차 복사의 mixed-generation 위험
- 파일: `jetlink/queues.py` (`StatefulState.after_run`, 구 259-268행)
- 기존: 3개 state를 순차 복사. 세 번째에서 오류 시 앞의 둘은 새 값,
  마지막은 옛 값인 mixed-generation state 발생 가능.
- 위험: 서로 다른 프레임 세대의 recurrent state가 섞여 추론 왜곡.
- 수정: `validate_next_states()` (1단계: 전부 검증, 변경 없음)와
  `commit_next_states()` (2단계: 전부 성공 시에만 반영)로 분리.
  검증 실패 시 `StateValidationError`가 전파되고 기존 state는 1바이트도
  변경되지 않음. `after_run()`은 두 단계를 순서대로 호출.
- 검증: 테스트 E (두 번째 state를 NaN으로 오염 → 3개 전부 불변 확인).

### 1-C. state_pairs 매칭이 너무 느슨함
- 파일: `jetlink/spec.py` (`state_pairs`, 구 69-80행)
- 기존: `next_+name`이 output에 있기만 하면 pair로 인정.
- 위험: shape가 다른 텐서가 우연히 이름만 맞으면 잘못된 pair로 state 오염.
- 수정: `state_pairs`는 exact shape tuple 일치 + (dtype 정보가 있으면)
  dtype 일치를 만족하는 pair만 인정. `validate_stateful()` 추가로
  stateful 스펙의 고아 `state_*`/`next_state_*`, 빈 pair 집합을
  `ValueError`로 명시적 실패 (조용한 무시 금지).
  `StatefulState.__init__`에서 `validate_stateful()` 호출로 fail-fast.
- 검증: 테스트 "3:" 4종 (v3 통과, orphan/shape-mismatch/dtype-mismatch 거부).

### 1-D. _check_shapes가 element 수만 비교
- 파일: `patches/session.py.new` (`_check_shapes`, 구 519-533행)
- 기존: `np.prod` 비교라 `(128,1,16384)` vs `(128,16384,1)`이 통과.
  output은 4개 중 1개만 검사.
- 위험: 차원 순서가 뒤바뀐 엔진이 로드되어 state 텐서 의미가 깨짐.
- 수정: 입력/출력 이름 집합 완전 일치 + 전 텐서 exact shape tuple 비교 +
  (spec에 dtype이 있으면) dtype 비교. 하나라도 어긋나면 engine load 실패.
- 검증: 테스트 C/D (transposed/missing/unexpected/dtype-mismatch 거부).

### 1-E. warm-up이 비결정적 state에서 시작
- 파일: `patches/session.py.new` (`EngineHost._warm`, 구 455-470행)
- 기존: `step_into` → `warm` → `reset` 순서. `step_into`는 `state_*`를
  건드리지 않으므로 warm (및 CUDA graph capture)이 pinned 버퍼의 쓰레기값에서
  시작할 수 있음.
- 위험: 비결정적 초기 state → 첫 프레임들 추론 불안정.
- 수정: stateful일 때 `reset()` → `step_into()` → `warm()` → `reset()` 순서로.
  warm 전후 모두 deterministic zero state 보장.
- 검증: 테스트 G (reset 후 step_into → 3종 state 전부 zero 확인).

### 1-F. 패치 파일이 `patch -p1`로 적용 불가 (부수 발견)
- 파일: `patches/*.patch` 6개 전부
- 기존: 헤더가 `patches/*.orig` 또는 절대경로(`/home/hatch/...`)라
  `patch -p1` 실행 시 파일을 찾지 못하고 프롬프트에 걸림.
  `JETSON_SETUP_GUIDE.md`의 적용 절차가 실제로 동작하지 않았음.
- 수정: 6개 전부 `a/<repo-root 기준 경로>` / `b/<...>` 헤더로 재생성.
  (carrot-jetson용 4개: `third_party/jetlink/jetlink/...`,
  openpilot용 2개: `openpilot/selfdrive/modeld/jetlink/...`)
- 검증: pristine `.orig`에 `patch -p1 --dry-run` + 실제 적용 후
  `.new`와 바이트 단위 일치 확인 (6개 전부).

### 1-G. build_trt_v3.py의 TRT 10.x API 오류
- 파일: `tools/build_trt_v3.py` (구 122행)
- 기존: `context.execute_v3(bindings)` — TRT 10.x named tensor API와 맞지 않음
  (positional bindings + 구 실행 API).
- 수정: `set_tensor_address` + 명시적 pycuda stream으로
  H2D → `execute_async_v3(stream.handle)` → D2H → `synchronize` 순서.
  `bindings` 리스트 제거.
- 검증: **Jetson 실기에서만 검증 가능** (이 VM에 TensorRT 없음).
  여기서는 `py_compile` + argparse 동작만 확인.

### 1-H. build 전 ONNX identity 검증 누락
- 파일: `tools/build_trt_v3.py` (신규 `check_onnx_identity`)
- 기존: spec의 sha256/nbytes와 실제 ONNX를 비교하지 않고 빌드.
- 위험: 잘못된 ONNX + 올바른 JSON 조합으로 엔진 빌드 가능.
- 수정: 빌드 전 `sha256 == spec["sha256"]` and `size == spec["nbytes"]`
  확인. 불일치 시 `SystemExit`으로 빌드 거부.
- 검증: 정상 파일 통과 + 변조 파일 거부 확인 (VM에서 실행).

### 1-I. parity가 출력만 하고 gate가 아님
- 파일: `tools/build_trt_v3.py` (`verify_engine`)
- 기존: `max abs diff` 출력만. 차이가 커도 성공 종료.
- 수정: 출력 4종(`outputs` + `next_state_*` 3종) 각각에 대해
  max abs err / mean abs err / finite를 계산.
  `--require-max-abs-err`를 주면 pass/fail gate로 동작.
  임의 threshold는 만들지 않음: 값을 주지 않으면 측정값만 보고하고
  "허용오차 기준 미확정"으로 표시. (기존 코드베이스에서 채택 가능한
  TRT↔ORT parity 기준을 찾지 못함 — onnx_patch.py의 0.0021/0.0003 언급은
  Apple Neural Engine 문맥이라 부적합.)
- `--frames N` 추가로 N-frame recurrent loop 검증
  (next_state_* → state_* 피드백) 지원.
- 검증: gate 로직은 **Jetson 실기에서만 검증 가능**.

### 수정하지 않은 것 (리뷰가 유지 판정한 항목)
- `patches/model.py.new:146-149`의 `prev_feat` 분기: v2 queued에서 필요하고
  v3 stateful에서는 없어야 하는 게 맞음. 손대지 않음.
- `patches/model.py.new:133-136`의 desire rising-edge pulse 로직:
  upstream #38916과 일치. `desire`라는 이름 때문에 continuous vector로
  바꾸지 않음.

## 2. 변경 파일 목록

| 파일 | 변경 목적 |
|---|---|
| `jetlink/spec.py` | dtype 필드 추가, `state_pairs` exact 매칭, `validate_stateful()` 신설 (항목 3) |
| `jetlink/queues.py` | `StateValidationError`, `validate_next_states`/`commit_next_states` 분리, 원자적 `after_run` (항목 2) |
| `patches/session.py.new` | `_warm` 순서 수정, `_check_shapes` exact화, `_infer` state 검증 게이트 (항목 1, 4, 5) |
| `patches/*.patch` (6개) | `.orig`→`.new` diff 재생성 + `patch -p1` 적용 가능 헤더로 수정 (항목 1-F) |
| `tools/gen_cinque_v3_json.py` | pair별 dtype 일치 assert + `validate_stateful()` 호출 (항목 8) |
| `artifacts/cinque_v3.json` | 재생성: `input_dtypes`/`output_dtypes` 포함 (항목 8) |
| `tools/build_trt_v3.py` | TRT 10.x API, ONNX identity gate, parity gate 구조, `--frames` (항목 9, 10, 11) |
| `tests/test_stateful_safety.py` | 신규: negative A~G + 항목 3 + 항목 12 multi-frame (항목 12, 13) |

## 3. 테스트 결과

`tests/test_backport.py`: **38 passed, 0 failed** (회귀 없음).
`tests/test_stateful_safety.py` (신규): **25 passed, 0 failed**.

| 테스트 | 결과 | 근거 |
|---|---|---|
| A: next_state_feat_q NaN 주입 | PASS | `StateValidationError` 발생, 3종 state 불변 |
| B: next_state_img_q Inf 주입 | PASS | `StateValidationError` 발생, 3종 state 불변 |
| C: (128,16384,1) transposed shape | PASS | `_check_shapes`가 `ValueError`로 engine load 거부 |
| D: next_state_desire_q 누락 | PASS | `validate_next_states` + `_check_shapes` 모두 거부 |
| E: 2번째 state만 invalid 시 원자성 | PASS | 3종 state 전부 이전 값 그대로 유지 |
| F: reset 후 zero | PASS | 3종 state 전부 all-zero |
| G: warm 직전 zero | PASS | reset→step_into 후 3종 state 전부 zero |
| 3: orphan/shape/dtype mismatch pair | PASS | `validate_stateful()`이 3가지 경우 모두 거부, v3는 통과 |
| 12: 5-frame recurrent (실제 ONNX) | PASS | 매 프레임 finite, state가 실제로 진화, commit된 state == 모델의 next_state |
| C/D 추가: unexpected/dtype mismatch | PASS | `_check_shapes`가 거부 |

## 4. 아직 실기 검증이 필요한 항목 (소프트웨어 테스트와 구분)

**소프트웨어(VM)에서 검증 완료:**
위 63개 테스트 전부. 특히 recurrent state의 원자적 유지, finite 게이트,
exact shape 계약은 실제 766MB ONNX + onnxruntime(CPU)으로 검증됨.

**Jetson 실기에서만 검증 가능:**
1. TRT 10.3 엔진 빌드 (onnx 파서가 v3 opset을 받는지)
2. `build_trt_v3.py`의 `execute_async_v3` 경로 (이 VM에 TRT 없음)
3. TRT ↔ ONNX Runtime multi-frame parity 수치 (허용오차 기준 미확정)
4. 정지 상태 passive inference (finite/latency/state continuity)
5. `onnx_patch.py`의 v3 대응 필요 여부 (아래 5항 참조)
6. 제한적 실주행 (위 1-4 전부 통과 후에만)

## 5. 확인 필요 (추측으로 수정하지 않음)

**항목 14 — new_img dtype / ONNX head 구조 / onnx_patch.py 대응:**
실제 v3 ONNX 그래프를 측정함 (tools/onnx_meta_light.py 확장):
- `new_img` dtype = **uint8** (float 아님)
- head 구조: `new_img` → **Unsqueeze** → **Concat** → `next_state_img_q`.
  즉 head Cast가 없음. recurrent state 업데이트(rolling buffer)가
  그래프 내부 Concat으로 구현되어 있음.
- `state_img_q`/`next_state_img_q`도 **uint8**. uint8 텐서가
  Unsqueeze→Concat→Gather→Slice→Reshape를 그대로 통과한 뒤 하류에서
  변환됨.
- production `onnx_patch.py` 현황: `IMG_INPUTS = ('img', 'big_img')`만
  처리하고, head Cast를 찾아 retype하는 구조. v3 ONNX에는
  (a) `new_img`가 목록에 없고, (b) head Cast 자체가 없으며,
  (c) `state_img_q`도 uint8 input이므로, **현재 patcher는 v3 ONNX에
  그대로 적용 불가** (`ValueError` 발생 예상).
- TRT 10.3 파서가 uint8 graph input을 직접 받는지, patcher에 v3 경로가
  필요한지는 **Jetson 실측 없이는 확정 불가**. 추측으로 수정하지 않고
  "확인 필요"로 남김.

**항목 15 — production build path 일치 검토:**
`tools/build_trt_v3.py`는 독립 빌더. production 경로
(`onnx_patch.py` → workspace 계산 → FP16 config → timing cache →
production engine loader)는 v2 전용으로 짜여 있고, 위 항목 14의 이유로
v3는 현재 production patcher를 통과하지 못함.
결론: production builder를 v2/v3 공용으로 만드는 것은 Jetson 실측
(특히 uint8 input 처리) 후에 설계해야 함. 당장은 별도 스크립트 유지,
v2 동작에는 영향을 주지 않음. "검토 완료, 구현은 실측 후"로 기록.

## 6. fail-closed 최종 기준 체크리스트 (항목 16)

- [x] Model identity: ONNX sha256/size를 spec과 대조 후 빌드 (소프트웨어 검증됨)
- [x] Engine contract: 입출력 이름 집합 + exact shape + dtype 일치 (소프트웨어 검증됨)
- [x] Runtime: outputs finite + next_state 3종 finite + state update atomic (소프트웨어 검증됨)
- [x] Failure: 오류 시 state 미변경 + 실패 Status → comma fallback (소프트웨어 검증됨)
- [ ] Jetson 실측: 위 4항의 TRT 엔진 기준 재확인 (미실시)
- [ ] 정지 상태 passive inference (미실시)
- [ ] 제한적 실주행 (미실시 — 위 전부 통과 후에만)

## 7. GitHub 반영

- 저장소: `rownlvh8875-coder/jetson-v3-backport`, branch `main`
- (푸시 후 SHA 기록)
