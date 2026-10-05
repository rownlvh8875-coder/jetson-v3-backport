# GPT 인계 프롬프트 (그대로 붙여넣기용)

당신은 openpilot/Carrot 차량 주행 스택을 다루는 시니어 엔지니어다.
아래 작업을 이어받아 완성하라. 추측·날조 금지, 검증된 것만 사실로 말한다.

## 목표

Jetson Orin Nano Super에서 Cinque Terre V3 모델이 동작하도록,
현재 queued(v2) 전용인 Jetson 추론 스택에 stateful(v3) 지원을 백포트한다.

## 환경 (사실)

- 차량: comma 4 + `ajouatom/openpilot` 브랜치 `carrot-wip` + Jetson Orin Nano Super 8GB
- Jetson: Carrot R2 이미지, L4T 36.4.7, TensorRT 10.3.0, SSH 계정 `jetlink` (키 인증)
- Jetson 저장소: `ajouatom/carrot-jetson`
  - `third_party/jetlink/` = `zoompilot/jetlink` @ `194ff6dc` (0.3.0a1) 무수정 vendoring (프로토콜 v2)
  - `openpilot/selfdrive/modeld/jetlink/cinque_v2.json` 에 v2 스펙 고정
- Comma 저장소: `ajouatom/openpilot` 브랜치 `carrot-wip` (2026-10-05 기준 e6a6284)
  - `openpilot/selfdrive/modeld/jetlink/` : `model.py`(JoiningModel), `link.py`(SPEC+IPC Client),
    `daemon.py`(USB gadget owner), `warp.py`, `cinque_v2.json`
  - `link.py:14`에서 `cinque_v2.json`을 SPEC으로 로드, `validate_spec()`으로 서버 spec과
    바이트 단위 일치를 강제 (불일치 시 추론 거부 — 안전 인터록)
  - `model.py:146`에서 매 프레임 `result[hidden_state]`를 `prev_feat`로 피드백 (queued 전용)

## 모델 (검증된 사실 — 그대로 사용)

- Cinque Terre V3 = comma PR #38932의 Cinque v3와 동일 학습 체크포인트.
  ref `bf3e3631b3f91d92a1020a5e0dd4298b93ff4244` = "Use f78ed37d for the precompiled eGPU driving model"
- v3 ONNX (HuggingFace `commaai/openpilot_driving_models`):
  `f78ed37d-afad-4dbc-8050-40ea885eedde/12864/big_driving_supercombo.onnx`,
  LFS oid `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`,
  size 766354845 bytes. (실측 확인됨)
- 계약 차이 (openpilot #38916, upstream `jetlink/spec.py` 독스트링 "Cinque Terre V3 onwards"):
  - v2 (queued): 입력 `img, big_img, desire_pulse[1,33,8], traffic_convention, action_t,
    features_buffer[1,32,32,512]`. 서버가 queue 유지, comma가 `prev_feat` 피드백.
  - v3 (stateful): 입력 `new_img(2,6,H,W)` + `desire` + `traffic_convention` + `action_t`
    + `state_img_q, state_desire_q, state_feat_q`. 출력 `outputs`(18452) +
    `next_state_img_q, next_state_desire_q, next_state_feat_q`. history는 그래프 내부 유지.
- Upstream 최신(HEAD)은 프로토콜 v3 + Swift 서버로 완전히 갈아엎어졌고 JetPack 7.2.1/TRT 10.16
  기준이다. **사용자 환경과 OS 레벨이 다르므로 전체 이식은 금지.** 0.3.0a1에 백포트한다.

## 이미 완료된 작업 (검증됨 — 재작업 금지, 그대로 사용)

`~/workspace/jetson-v3-backport/` (또는 사용자가 전달하는 동일 디렉토리)에 있다:

1. `jetlink/spec.py` — stateful 감지(`new_img`), `state_pairs` ONNX 유도,
   stateful packed(`desire,tc,at`, `prev_feat` 없음). 테스트 13개 통과
   (실측 `cinque_v2.json` 회귀 + upstream fixture).
2. `jetlink/queues.py` — `StatefulState` 신규: state를 엔진 pinned 입력 버퍼에 유지,
   `step_into`/`after_run`/`reset`. 합성 데이터 테스트 통과.
3. `jetlink/registry/lfs.py` — precompiled-pkl 커밋용 export fallback 추가.
   실측 네트워크 테스트 통과 (v3 ref → 위 oid/size, v3 ref는 in-tree 404 후 HF로 폴백).
4. `patches/` — 6개 unified diff:
   - `jetson-spec-stateful.patch`, `jetlink-queues-stateful.patch`,
     `jetson-lfs-export-fallback.patch` (위 1~3의 diff)
   - `jetson-session-stateful.patch` (`session.py`: `_warm`에서 stateful 분기,
     `_infer`에서 `outputs['outputs']` 명시 + `after_run` 피드백)
   - `comma-link-model-select.patch` (`link.py`: `CARROT_JETLINK_MODEL_JSON`/`_LABEL`
     환경변수로 모델 선택, 기본값 v2 fail-closed)
   - `comma-model-stateful.patch` (`model.py`: `prev_feat` 피드백을 queued 한정,
     모델 라벨 일반화)
   - 단, session/model/link 패치는 하드웨어 없이 실행만 안 됐을 뿐 코드 리뷰는 완료.
5. `tests/test_backport.py` — 24개 전부 통과. `REPORT.md`에 검증 경계 명시.

## 당신이 할 일 (순서대로)

1. **패치 리뷰**: 6개 diff를 읽고 논리 오류·누락을 찾아라. 특히
   `session.py`의 `_warm`/`_infer` 분기와 `model.py`의 desire pulse 경로.
2. **`cinque_v3.json` 생성** (하드 블로커 해소):
   - Jetson(또는 766MB를 받을 수 있는 머신)에서 패치된 `lfs.py`로
     `fetch_pointer('bf3e3631b3f91d92a1020a5e0dd4298b93ff4244')` → ONNX 다운로드
     (oid/size 검증은 `lfs_download`이 자동 수행).
   - `spec_from_onnx()`로 spec 생성 → `cinque_v3.json`으로 저장.
   - **절대 날조 금지**: 텐서 이름·shape은 오직 실측 ONNX에서. upstream
     `tiny_stateful.spec.json`의 네이밍 규칙을 참고는 하되, big 모델 실측값으로 덮어쓴다.
3. **Jetson에 4개 패치 적용** (`ajouatom/carrot-jetson`의 `third_party/jetlink`),
   **comma에 2개 패치 + `cinque_v3.json` 배치** (`carrot-wip`의 `modeld/jetlink/`).
4. **TRT 10.3 엔진 빌드** (Jetson, 약 160초). 실패 시 opset/파서 로그를 분석하고,
   빌더는 건드리지 말고 원인을 보고하라.
5. **정지 상태 passive 추론 테스트**: finite 출력 확인, 프레임 시간 측정.
   통과 전까지 주행 테스트 금지.
6. 결과를 `REPORT.md` 양식으로 정리: 구현/미구현, 실행 검증/미실행 검증 구분.

## 금지 사항

- 실차 설정 변경·live CAN 송신·플래싱·자동 배포는 사용자 명시 승인 없이 수행 금지.
- v2를 기본값으로 유지 (fail-closed). v3는 명시적 선택 시에만 동작.
- `cinque_v3.json`의 어떤 필드도 추측으로 채우지 말 것.
- 테스트 통과를 위해 기준을 완화하거나 기존 기준 결과를 덮어쓰지 말 것.
- 개인 주행 로그·키·차량 식별정보를 공개 저장소에 올리지 말 것.
