# Cinque V3 Jetson 최소 변경계획

2026-10-11 1단계 계획을 보존하면서 사용자 승인에 따라 **2단계 범위만 구현**했다.
원본 확보·CPU 검사·가공/빌더/검증기 수정이 대상이다. 실제 장치 변경은 승인되지 않았다.
기준 SHA·원본 상태·실행 명령/결과는 [PROJECT_STATE.md](PROJECT_STATE.md), 제약은 [AGENTS.md](../AGENTS.md).

목표 경로: V3 원본 확인 → 필요한 TensorRT 가공/빌드 → Jetson stateful 실행 →
당근 기존 Jetson 연결 → 정지 상태 실제 장치 검증.
엔진 파일 생성만으로 최종 완료하지 않는다. V2 기본 동작과 기존 내부 모델 복귀를 유지한다.
MDM/범용 변환기/새 카탈로그·플러그인·CLI/PKL 역변환/재학습·INT8/eGPU/주변 설치·네트워크 개편/주행 튜닝은 제외한다.

## 재사용할 흐름과 계약

아래 경로의 `J:`는 고정 carrot-jetson, `C:`는 고정 carrot-wip의 저장소 루트다.
이 저장소의 `jetlink/`는 테스트 가능한 일부 모듈 사본이며 완전한 서버 설치본은 아니다.

| 흐름 | 현재 코드와 재사용할 기능 | 남은 최소 차이 |
|---|---|---|
| comma 카메라 | `C:openpilot/selfdrive/modeld/compile_modeld.py::make_warp`, `jetlink/model.py::Warp`, `jetlink/warp.py::validated_warp`의 NV12→6채널, 좁은/넓은 카메라 pair, native QCOM 준비/픽셀 검사 | V3 JSON과 동일한 `(2,6,128,256)` uint8 계약 검증. 전처리 재작성 안 함 |
| 기존 통신 | `C:.../jetlink/link.py::Client`, `daemon.py::_serve_local`, vendored `client.py`의 bounded IPC/USB, frame ID·길이·finite·deadline | protocol 2 stateful 차단과 V2 고정 선택을 대상 V3에 한해 좁게 연결 |
| Jetson build/load/run | `J:third_party/jetlink/jetlink/server/backends/trt/{build.py,__init__.py,engine.py}`의 FP16, 원자적 plan 저장, cache/runtime tag, pinned buffers, named tensor, CUDA graph | V3 patch와 physical dtype 선언, stateful session 통합 |
| state 갱신 | 이 저장소 `jetlink/queues.py::StatefulState`, `patches/session.py.new::_warm/_infer/_check_shapes` | 실제 J 파일에 필요한 분기만 이식. 기존 C에 중복 state queue 구현 안 함 |
| 반환/해석 | 서버는 `outputs`만 반환; `C:.../contracts.py::validate_model_spec/parse_outputs`, `parse_model_outputs.py::Parser` | 기존 V3 slice 호환 검사/실제 수치 검증. parser/주행 알고리즘 재작성 안 함 |
| 실패/복귀 | `C:.../model.py::JoiningModel.run/_reset_small`, `link.py::fault_active`; `selfdrived.py::update_events`가 commIssue 생성 | 기존 복귀·오류파일·알림을 재사용하고 정지 상태에서 실제 경로 검증 |

현재 C는 stateful spec/packed, `if 'prev_feat' in self.views`, desire rising-edge pulse,
parser 및 내부 모델 사전 warm/실패 시 reset을 이미 구현한다.
`test_app_models.py::test_joining_model_uses_selected_buffers_parser_and_recurrence`도 이미 있다
(이번 PC에서는 fcntl 때문에 본문 미실행). 현재 J는 PolicyQueues 전용이며 stateful이 없다.

**원본 ONNX에서 전체 대조한 계약** (2단계, 해시·크기 일치 파일):

| 텐서 | shape | 원본 dtype 기록 |
|---|---|---|
| new_img | `(2,6,128,256)` | uint8 |
| desire / traffic_convention / action_t | `(8,)` / `(1,2)` / `(1,2)` | float32 |
| state_img_q ↔ next_state_img_q | `(2,5,6,128,256)` | uint8 |
| state_desire_q ↔ next_state_desire_q | `(132,1,8)` | float32 |
| state_feat_q ↔ next_state_feat_q | `(128,1,16384)` | float32 |
| outputs | `(1,18452)` | float32 |

wire는 카메라 uint8 `393216` bytes + packed float32 12개 `48` bytes;
protocol2 요청 payload는 8-byte header 포함 `393272`, 응답은 20-byte header + outputs `73808` = `73828` bytes
(요청 시 telemetry 별도 추가). state 텐서는 Jetson에 유지한다. V3 packed에는 prev_feat가 없다.
V2 queued는 기존 prev_feat/history 처리를 유지한다.
V3 uint8 가공을 채택할 경우 `new_img`, `state_img_q`, `next_state_img_q`만 float16으로 바뀌는
physical engine 계약을 원본 semantic spec과 분리해 선언/검사한다. JSON의 원본 dtype을 덮어쓰지 않는다.

## 1단계 문제 재현과 2단계 처리

아래 표의 빌더 입력 열거·반환/sidecar·검증기 dtype/finite/pinned/context·identity 테스트
문제는 2단계에서 집중 회귀 검사로 고정하고 수정했다. 표의 재현 근거는 1단계 당시 기록이다.
sidecar의 **production 소비**, state narrowing, protocol/모델 선택은 여전히 후속 작업이다.
현재 결과·코드 SHA는 PROJECT_STATE의 2단계 기록을 우선한다.

| 항목 | 현재 근거/판정 | 후속 대상 |
|---|---|---|
| state NaN/Inf·shape·고아 pair·warm 초기화 | 백포트에 validate/commit 분리, exact shape, warm 전후 reset 존재. 기존 안전성 검사 30개까지 PASS. 과거 결함을 그대로 현재 결함으로 복사하지 않음 | J에 검증된 기존 분기 재사용 |
| TRT FP16 flag / named 실행 API | 현재 `BuilderFlag.FP16`, `set_tensor_address`/`execute_async_v3` 사용. 과거 API 오타는 남아 있지 않음 | 실제 TRT 버전/API는 장치에서 검증 |
| J의 V3 가공·dtype 연결 부재 | `onnx_patch.py::IMG_INPUTS=('img','big_img')`; production build는 이 patch_file만 호출. TrtBackend에 dtype_transforms 없음 | J onnx_patch, TRT build/backend, session |
| 현재 comma의 protocol 차단 | vendored `client.py::infer_begin`이 stateful+protocol2에 무조건 LinkError. 대상 JSON으로 네트워크 전 CPU 재현. 기존 테스트도 이 거부를 의도적으로 요구 | 명시적 V3 호환 capability 및 제한된 opt-in, 아래 작업 4 |
| 현재 comma의 모델 선택 | `link.py::SPEC=DEFAULT_SPEC`; `mac.py::prepare`의 기존 Jetson 분기는 SPEC(V2)을 요청. 동적 App 선택은 기존 Jetson과 다른 분기 | V2 기본 유지, V3 한 파일만 명시적으로 선택 |
| 빌더의 입력 열거 오류 | `tools/build_trt_v3.py:122`의 `for i in network`는 layer를 input tensor처럼 읽음. NVIDIA [TRT 10.3 Python binding](https://github.com/NVIDIA/TensorRT/blob/release/10.3/python/src/infer/pyGraph.cpp#L961)은 network iteration을 layer로 정의. layer mock에서 `.shape` AttributeError 재현 | `build_engine`: num_inputs/get_input으로 열거 |
| 빌더 retype 반환/sidecar 연결 | `build_engine`은 `retypes_path`를 만들지만 return이 없음. mock에서 파일 생성 후 반환 None 재현. 실제 이름은 `<stem>.patched.retypes.json`; 서버 cache metadata로 전달하는 코드도 없음 | 명시적 반환 + 서버가 읽는 metadata 경로 통일 |
| 원본 ORT 입력 dtype | `verify_engine::ort_feeds`가 TRT host dtype을 복사. patched engine의 fp16 이미지를 uint8 원본 ORT에 그대로 전달하게 됨 (mock 관찰 + JSON/코드 대조). 실제 ORT dtype error는 원본 필요 | ORT session input 명세로 원본 feed 생성 |
| parity 실패 게이트 | ORT finite=False를 출력만 하고 실패로 처리하지 않음. NaN max_err 비교가 False여서 `--require-max-abs-err 0`에서도 정상 반환을 mock 재현. ORT 미설치 시 threshold가 있어도 비교를 생략하는 코드 존재 | finite/비교 불가/threshold/프레임 수 유효성의 명시적 gate |
| state dtype narrowing | same_kind 허용은 과거 보류사항이며 아직 존재. 합성 float32 70000→float16 state가 검증 후 Inf로 저장되는 것을 CPU 재현 | 실제 physical dtype 대조 + 축소 변환 금지/변환 후 finite 확인. 해당 Jetson에서 발생했다고 주장하지 않음 |
| 원본 없이 안전성 suite 중단 | `test_stateful_safety.py:525` 이후 identity negative가 실제 모델 경로를 무조건 열음 | 합성 temporary bytes로 identity 검사 분리, 실제 모델 검증은 정직하게 SKIP |
| 패치 적용성 | CRLF 원본 검사는 6개 FAIL; LF+index 검사에서 J 4개 PASS/C 2개 FAIL. C model/link 기능은 이미 발전한 상태 | J도 필요한 hunk만 재사용, C 과거 패치 적용 안 함 |
| 개발 OS 실패 | WIP protocol 테스트의 Windows sendmsg 실패, fcntl collection blocker, AF_UNIX skip | Linux 개발 환경 재실행. Jetson 통신 코드를 Windows용으로 개편하지 않음 |

TensorRT/ONNX parser 지원, 실제 dtype/메모리/속도와 원본 대비 오차는 코드만으로 확정할 수 없다.
verify_engine의 PyCUDA 버퍼/초기화 경로도 실제 GPU 검증 전 미확인이다.
기존 production pinned/cudart engine을 활용하여 검증 경로가 실제 서버와 갈라지지 않게 한다.

## 2단계 구현과 후속 작업

2단계 결과:

- 작업 1 완료: 임시 바이트의 identity 검사와 main build 차단. 모델 없는 격리 사본에서 40 PASS.
- 작업 2의 로컬 도구 완료: `num_inputs/get_input`, 반환 경로, 원본/가공/engine/patcher 해시와
  원본 I/O·명시적 dtype 3개·TRT 버전을 기록. engine은 staging 후 마지막에 원자적으로 게시한다.
  `<engine.name>.<engine SHA256>.retypes.json`을 검증기가 읽으며 원본/가공 해시도 다시 검사한다.
  정상 이전 engine은 실패 시 보존한다. 실패한 시도의 사용되지 않는 sidecar/가공본은 남을 수 있지만
  현재 engine 해시가 다르면 소비되지 않는다. 원본 dtype JSON은 변경하지 않았다.
- `verify_engine`은 ORT metadata와 실제 engine I/O를 별도로 검사하고 pinned host buffer를 사용한다.
  CUDA primary context를 push한 뒤 deserialize/context 생성, 완료 sync 후 자원 해제/pop/detach한다.
  고정 J `engine.py/cudart.py`의 pinned/named 실행을 참고했다. 별도 운영 backend를 만들지 않았다.
  PyCUDA의 [비동기 복사/pinned 조건과 primary context API](https://documen.tician.de/pycuda/driver.html)를 대조했다.
- `verify_onnx_pair`는 ORT CPU 세션을 하나씩 실행하고 reference 출력만 임시 디스크에 둔다.
  원본↔patched ONNX의 recurrent/same-state 각 5프레임, 출력 4종 매번 유한·max/mean abs error 0.
  기준이 없는 임의 허용오차는 지정하지 않았다. 측정 완료·합격 보류(exit 3), TRT 합격 근거가 아니다.
- 작업 2의 **J production patch/build/backend 연결**, 작업 3~5는 미실행이다.
  고정 참고 사본/원격에 변경·push하지 않았다. V2 기존 patch/build는 그대로다.

### 1. 같은 V3 원본 확인과 원본 없는 CPU 검사 독립화 — 2단계 완료

- 파일/함수: `tests/test_stateful_safety.py` identity negative 구간,
  `tools/build_trt_v3.py::check_onnx_identity` 재사용,
  `tools/onnx_meta_light.py::parse_meta_light`로 원본 I/O 대조.
- 입력/출력: 지정 source에서 별도 로컬 파일로 확보 후 **전체 SHA256+766354845 bytes** 일치;
  input/output 이름 집합·shape·dtype를 JSON과 모두 대조한다. 다른 ONNX로 대체하지 않는다.
  PKL 실행/역변환 없이 protobuf metadata를 읽는다. 기존 JSON을 무조건 재생성하지 않는다.
- 재현 검사: 현재 safety 명령은 원본 부재로 exit1. 수정 시 synthetic tempfile 정상/해시 변조/크기 변조와
  main의 build 미호출을 각각 검사한다. real-model 조건은 그대로 유지한다.
- 완료: 원본 없는 CPU suite가 완료되고 real-model 구간만 SKIP. 원본 확보 상태는 별도로 표시한다.
  원본 확보가 지연돼도 나머지 CPU 검토/구현은 계속 가능하다.

### 2. V3 한 모델의 가공·빌드·수치 검증 경로 보완 — 로컬 도구 완료, production/장치 대기

- 파일/함수: `tools/build_trt_v3.py::build_engine/verify_engine`, `tools/patch_v3_uint8.py::patch_file_v3`;
  J `third_party/jetlink/jetlink/onnx_patch.py::patch_file`, `server/backends/trt/build.py::build_engine`,
  `server/backends/trt/__init__.py::TrtBackend`.
- 재사용: 원본 identity gate, V3 queue data-movement 가공, J 원자적 plan 저장/runtime cache tag/pinned 실행.
  V2 head-Cast 가공은 유지한다. 직접 확보한 원본을 사용하므로 registry/LFS/catalog 패치는 필수가 아니다.
- 계약: original→patched hash/변환 3개/engine I/O/runtime 버전을 sidecar에 기록;
  backend가 해당 engine에 적용된 dtype_transforms를 load/warm에 전달한다.
  원본 ORT와 TRT는 같은 프레임/스칼라를 받고 각자의 next_state로 이어간다.
- 재현 검사: layer 입력 열거, retype 경로 반환, ORT NaN/Inf, ORT 미설치·provider fallback,
  원본 feed dtype, frames<=0/잘못된 threshold, V2 fresh build와 cache reload의 선언 누락/오선언을 확인한다.
  ORT/provider/허용오차가 미확정이면 검증 완료로 표시하지 않는다.
- 완료: CPU 재현을 회귀 검사로 고정하고, 실제 모델 patched↔original 다중 프레임 출력 4종을 검사.
  실제 Jetson의 TRT parse/build/reload/다중 프레임 parity가 별도 통과해야 한다.
  허용오차는 측정 전에 출력/state별 근거로 정하고, 임의 숫자로 PASS를 만들지 않는다.

### 3. Jetson stateful session에 기존 백포트 연결

- 파일/함수: J `third_party/jetlink/jetlink/{spec.py,queues.py,server/session.py}`의
  `ModelSpec.validate_stateful`, `StatefulState`, `EngineHost._warm/_check_shapes`, `Session._infer/on_hello`.
  이 저장소의 동명 모듈/`patches/session.py.new`를 필요한 hunk 단위로 재사용한다.
- 계약: warm 전후·RESET_QUEUES·새 실제 추론 session에서 state 3종 zero;
  다음 frame에는 해당 frame의 검증된 next_state 3종만 저장.
  outputs와 state의 존재/정확 shape/physical dtype/finite 확인 후 갱신하고 결과를 반환한다.
  갱신 복사는 transaction rollback을 보장한다고 표현하지 않는다.
- 재현 검사: 기존 A/B/C/D/E/F/G 및 V2 queued 회귀, state narrowing 오염,
  잘못된 output 이름/전치 shape/누락·NaN·Inf, reset/재연결을 실제 `_infer`까지 모의 호출한다.
  미선언 dtype 축소는 거부하고 실패 frame에서 이전 state가 보존되는지 검사한다.
- 완료: 기존 V2 검사 보존, V3 출력 선택을 이름으로 수행, 실패 status/예외가 기존 comma 복귀로 연결.
  실제 engine I/O dtype을 실측한 뒤 exact 계약을 확정하고 반복 실행/메모리/state를 장치에서 확인한다.

### 4. 기존 Jetson protocol2와 현재 comma의 최소 V3 호환 연결

- 파일/함수: C `openpilot/selfdrive/modeld/jetlink/link.py`의 SPEC/validate_spec,
  `mac.py::prepare`의 Jetson 분기, `third_party/jetlink/jetlink/client.py::hello/infer_begin`;
  C `third_party/jetlink/jetlink/spec.py::ModelSpec.from_dict/to_dict`의 optional dtype 보존;
  J `server/session.py::on_hello`의 좁은 capability 선언.
  V3 명세는 C의 기존 jetlink 디렉터리에 배치하는 계획이며 이번에는 배치하지 않았다.
- 계획: V2를 기본으로 두고, 기존 `CARROT_JETLINK_MODEL_JSON` 방식의 opt-in을 **V2/V3 두 고정 파일**에 한해 사용한다.
  arbitrary JSON/catalog 선택은 추가하지 않는다. V3 identity와 전체 입력/출력 계약을 검증한다.
  현재 C ModelSpec은 dtype 필드를 직렬화하지 않으므로 백포트의 optional dtype 보존만 재사용한다.
  C의 state_pairs는 dict, 백포트는 list이므로 모듈 전체 교체는 하지 않는다. V2의 기존 직렬화는 유지한다.
  J의 수정 서버는 예를 들어 `cinque_v3_stateful_v2: true` capability를 응답하고,
  C는 명시적 V3 선택+대상 전체 SHA/계약 일치+그 capability가 모두 있을 때만 protocol2 stateful을 허용한다.
  capability는 호환성 표시이며 인증으로 취급하지 않는다. protocol3/다른 런타임 이전은 하지 않는다.
  기존 일반 stateful+protocol2 거부 테스트/비호환 peer 거부는 유지한다.
- 계약: protocol2 header/flags 유지, V3 요청은 위 `393272` bytes, 반환은 위 `73828` bytes;
  hidden을 외부 피드백하지 않는다. J 내부에 state가 유지되므로 매 frame reset하지 않는다.
  `JoiningModel.run`의 prev_feat 분기·parser·내부 복귀·FAULT를 그대로 재사용한다.
- 재현 검사: 현재 client의 대상 JSON 거부를 먼저 고정한 뒤 capability 없는 구 서버/다른 SHA/잘못된 spec은 거부,
  patched server와 대상 V3는 protocol2 socket fixture에서 연속 frame/reset 동작;
  V2의 payload/prev_feat와 기존 거부 테스트는 유지한다.
  기존 parser/stateful JoiningModel 테스트와 stale/nonfinite/truncated/timeout→복귀/FAULT를 Linux에서 실행한다.
- 완료: 합성 양단 통신/출력 해석/실패 복귀 통과. 실제 장치의 설치 SHA를 먼저 읽어 현재 기준과 다르면
  해당 설치 버전으로 최소 diff를 다시 대조한다. 다른 연결/서비스/Params 개편으로 확대하지 않는다.

### 5. 정지 상태 실제 장치 완료 판정

- 대상: 위 engine/session과 기존 `JoiningModel.run`, daemon, Parser, fault_active→commIssue.
  실제 comma/Jetson 설치 Git SHA·L4T/JetPack/CUDA/TRT/자원 여유를 읽기 확인하는 것이 첫 장치 작업이다.
  배포/설정 변경은 후속 단계의 사용자 허용 범위에서만 한다.
- 검증 입력/출력: 정지 상태 실제 카메라 pair와 실제 scalar, 연속 frame ID;
  정상 session의 연속 state와 reset/재연결 후 zero 시작을 구분한다.
  최소 1,000 연속 frame을 관찰하고 outputs/state finite·parser 필드·통신/추론 로그를 대조한다.
  원본 기준 수치 오차와 가공 ONNX/engine 오차는 따로 기록한다.
- 성능: 기존 모델 루프의 20Hz/50ms 주기를 기준으로 지속 처리율과 p50/p95/p99 지연,
  deadline 초과/드롭/queue 누적, 메모리·온도·throttle을 측정한다.
  기존 150ms client timeout은 정상 성능 합격선으로 사용하지 않는다.
  지속 20Hz와 queue 비누적을 확인하고 tail이 frame 예산을 깨면 원인 계측 후 직접 경로만 최소 수정한다.
- 실패 재현: 테스트 경로에서 불일치 spec, 잘린/stale 응답, outputs/state NaN/Inf,
  timeout/연결 단절을 주입하고 내부 모델 재실행·상태 reset·FAULT/commIssue와 실제 오류 알림을 확인한다.
  운영 서비스 강제 종료를 오류 주입 수단으로 쓰지 않는다.
- 완료: 실제 반복 추론+실제 comma 송수신/해석+성능/state+복귀/알림의 증거가 모두 있어야 완료.
  원본 미확보/허용오차 미정/실제 장치 미검증이면 해당 항목을 미완료로 남긴다.
  주행 검증은 이 계획 범위 밖이며 다음 작업으로 자동 시작하지 않는다.

3단계 첫 작업: 고정 J의 `onnx_patch.py`, TRT `build.py/TrtBackend`에 V3 가공과 engine별
dtype 기록의 소비를 격리 개발 사본에서 연결하고, 기존 stateful session 분기를 필요한 hunk로 통합한다.
V2 build/cache와 V3 load/warm dtype 계약부터 검사한다. 사용자 지시 전 시작하지 않는다.
