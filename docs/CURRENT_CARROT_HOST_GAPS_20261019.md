# 2026-10-19 current carrot-wip Jetson host gap matrix

대상: `ajouatom/openpilot:carrot-wip @ 5032afca77a96e31a077a5e9ac738d9ac08a99df`

목적: "현재 carrot-wip가 이미 V3를 얼마나 이해하고, 실제 Jetson host에서 무엇이 남았는가"를
파일 단위로 구분한다. 이 문서는 **코드 이식 우선순위**이며 실장치 적용 절차가 아니다.

## 결론

현재 carrot-wip의 **comma/client 쪽은 protocol 3 + dynamic stateful ModelSpec까지 상당 부분 준비**되어 있다.
반면 vendored Python Jetson server는 여전히 **V2/queued 실행 경로가 기본**이다.

따라서 신규 작업은 전체 Jetlink를 다시 쓰는 것이 아니라 아래 server gap을 메우는 방향이 맞다.

## Gap matrix

| 영역 | 현재 carrot-wip | 상태 | 신규 작업 |
|---|---|---|---|
| protocol 3 framing/client | `third_party/jetlink/jetlink/protocol.py`, `protocol_v3.py`, `client.py` | 이미 있음 | 재작성 금지, 회귀만 |
| dynamic ModelSpec | `spec.py` | queued/stateful 구분 있음 | 재사용 |
| comma IPC | `openpilot/selfdrive/modeld/jetlink/link.py` | spec 기반 동적 크기 | 재사용 |
| comma parser | `contracts.py`, `model.py` | stateful/queued 동적 입력 및 fallback | 재사용 |
| offroad approval | `selection.py`, `mac.py` | App model 승인 있음 | managed Jetson 선택 경로만 추가 |
| Jetson queue/state | `third_party/.../queues.py` | **PolicyQueues만 존재** | 기존 백포트의 `StatefulState` 재이식 |
| server warm | `server/session.py::_warm` | 무조건 `PolicyQueues(spec)` | `spec.stateful`이면 StatefulState 사용 |
| server inference | `server/session.py::_infer` | 첫 output만 반환, next_state commit 없음 | next_state 검증→원자적 commit→driving output 반환 |
| server state failure | 현 server | state generation invalidation 없음 | nonfinite/shape/dtype state 실패 시 loaded generation 폐기 |
| TRT ONNX patch | `onnx_patch.py` | `img`, `big_img` uint8 전제 | `new_img`, `state_img_q` V3 처리 추가 |
| engine shape check | `session.py::_check_shapes` | input + 첫 output size 중심 | state output 전체 shape/dtype 검증 |
| TRT 10.3 builder | `server/backends/trt/build.py` | JetPack6/TRT10.3 경로 존재 | V3 patch가 들어오면 최대한 재사용 |
| HELLO version | `server/session.py::on_hello` | `protocol: P.VERSION` = 기본 2 | transport 실제 protocol version 보고 |
| host identity | backend describe | backend/device 있음 | `carrot_host=jetson` + 명시 capability 추가 |
| model selection | comma `mac.py` | protocol3 non-App Jetson은 사실상 V2 `SPEC` | explicit managed-Jetson capability일 때 `peer.loaded` 사용 |
| Web selector | 현재 web | 상태 표시 위주 | 하드웨어 검증 뒤 구현 |

## 1. 재사용할 기존 백포트 코드

이 저장소의 기존 `feature/cinque-v3-jetson`에 이미 검증 자산이 있다.

### `jetlink/queues.py`

기존 `StatefulState`는 다음을 이미 구현한다.

- state input ↔ `next_state_*` pair 검증
- reset 시 state input 0 초기화
- `new_img` + scalar input pack
- next-state shape/dtype/finite 검사
- 검증 후 commit
- 검증 실패 전에 state를 변경하지 않는 fail-closed

이 코드는 현재 carrot-wip `PolicyQueues`와 합치는 쪽이 낫다.
별도 model-specific queue를 새로 쓰지 않는다.

### `tools/build_trt_v3.py`

TRT 10.3에서 V3 UINT8/stateful input을 처리하기 위해 이미 만든 patch/build 검증을
현재 vendored `onnx_patch.py`와 비교해 필요한 최소 차이만 옮긴다.

**전체 builder를 교체하는 것보다 현재 carrot-wip의 builder를 유지하고 V3 patch만 채우는 것이 우선**이다.

## 2. current server에서 바로 확인된 V3 blocker

### A. `PolicyQueues(spec)` 고정

현재 `EngineHost._warm()`:

```python
from jetlink.queues import PolicyQueues
queues = PolicyQueues(spec)
```

stateful spec에는 `img`, `big_img`, `features_buffer`가 없으므로
V3를 그대로 넣으면 queued queue 생성 단계에서 맞지 않는다.

수정 방향:

```python
if spec.stateful:
    state = StatefulState(spec, host_inputs)
else:
    state = PolicyQueues(spec)
```

실제 순서는 `host_inputs` 획득과 shape 검증을 고려해 정한다.

### B. next_state가 현재 server에서 commit되지 않음

현재 `_infer()`는:

```python
outputs = loaded.engine.run()
out = next(iter(outputs.values())).reshape(-1)
```

만 수행한다.

V3는 이 프레임의:

- `next_state_img_q`
- `next_state_desire_q`
- `next_state_feat_q`

를 다음 프레임 입력 state로 commit해야 한다.

수정 순서는 반드시:

```text
engine.run()
→ driving output finite 검증
→ next_state 전체 shape/dtype/finite 검증
→ next_state commit
→ OK response
```

이어야 한다.

next_state 검증 실패 후 OK를 보내면 안 된다.

### C. ONNX patch가 V2 image 이름에 고정

현재 `onnx_patch.py`:

```python
IMG_INPUTS = ('img', 'big_img')
```

V3는 `new_img`와 recurrent image state를 포함한다.
TRT 10.3 UINT8 parser 제약 때문에 기존 V3 builder에서 검증했던 Cast rewrite가 필요하다.

여기서 "모든 uint8을 무조건 fp16" 같은 범용 rewrite는 금지한다.
실제 graph의 Cast 구조와 dtype을 확인하고 대상 tensor를 제한한다.

### D. HELLO가 server 기본 VERSION=2를 보고

현재 `server/session.py::on_hello`은:

```python
'protocol': P.VERSION
```

을 보낸다. vendored `P.VERSION` 기본값은 2다.

protocol 3 transport로 열었다면 HELLO에도 실제 stream version을 보고해야 한다.
그렇지 않으면 wire는 v3인데 JSON peer metadata는 v2가 되는 모순이 생긴다.

### E. comma의 protocol3 Jetson은 아직 "선택 가능한 Jetson"이 아님

현재 `mac.prepare()`에서 App이 아닌 protocol3 peer는 `legacy_v3`로 분기되지만
실제 selected model은 App이 아니면 `SPEC.sha256`, 즉 고정 V2다.

따라서 Jetson host가 V3를 loaded로 보고해도 **별도 managed-Jetson 계약 없이는 그 loaded SHA를 따라가면 안 된다.**

이 저장소의 새 `jetlink/multimodel_policy.py`는 다음 명시 계약을 proposal로 고정했다.

```json
{
  "protocol": 3,
  "carrot_host": "jetson",
  "backend": "trt",
  "device": "Orin-sm87",
  "carrot_model_selection_v1": {
    "version": 1,
    "selection": "host"
  },
  "loaded": "<64-char lowercase sha256 or null>"
}
```

이 metadata는 인증이 아니다. 실제 모델은 기존 carrot-wip의 full ModelSpec 검증 및 offroad approval을
추가로 통과해야 한다.

## 3. 구현 순서

### Host patch 1 — protocol3 transport + HELLO

목표:

- 실제 protocol3 header/padding
- HELLO에 `protocol=3`
- `carrot_host=jetson`
- managed selection capability
- 기존 V2 engine loaded 상태를 그대로 보고

이 단계에서는 **V3를 아직 build하지 않는다.**

통과 기준:

- protocol3 HELLO
- V2 ENGINE_REQ
- V2 inference
- 기존 protocol2 V2 회귀

### Host patch 2 — stateful runtime

- `StatefulState` 통합
- warm/reset
- next_state validate/commit
- bad state → NOT_FINITE/INFER_FAILED + generation invalidate
- reload 후 zero-state 확인

먼저 CPU synthetic fixture로 통과시킨다.

### Host patch 3 — TRT 10.3 V3

- current carrot-wip TRT builder 유지
- V3 ONNX patch만 추가
- 실제 V3 SHA/size/spec gate
- TRT build
- repeated inference/parity

### Comma patch — managed Jetson selection

- legacy Jetson: 현재 V2 경로 유지
- explicit managed Jetson: `peer.loaded`를 candidate로 사용
- first V3 approval: offroad-only
- exact approved spec: onroad reconnect 가능
- loaded SHA/spec 변경: fail-closed
- selected engine missing: internal model 유지

### UI — 마지막

- selected / loaded / active 구분
- V2/V3 상태
- build/ready/error 표시
- offroad-only selection
- 추가 모델 catalog는 이후

## 4. 먼저 수정하지 않을 파일

다음은 현재 기능이 이미 충분하므로 **문제 증거 없이 먼저 뜯지 않는다.**

- `openpilot/selfdrive/modeld/jetlink/model.py`
- `openpilot/selfdrive/modeld/jetlink/link.py`
- `parse_model_outputs.py`

V3 문제를 server-side state와 managed selection 경로에서 해결하는 것이 우선이다.

## 5. 첫 하드웨어 접속 전 완료 가능한 것

이미 완료:

- current source baseline 고정
- V2/V3 seed identity
- managed Jetson capability proposal
- policy unit tests
- read-only runtime inventory

다음으로 가능한 것:

- current vendored server를 기준으로 protocol3 synthetic host fixture 작성
- `StatefulState`를 current `PolicyQueues`와 합친 candidate module 작성
- current `onnx_patch.py`와 기존 V3 patch의 정확한 delta 추출
- current server `_warm/_infer/_check_shapes/on_hello` patch candidate 작성

단, 실제 Carrot R2 service/install 경로는 SSH inventory 전 추정하지 않는다.
