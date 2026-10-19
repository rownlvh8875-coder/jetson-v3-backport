# Carrot × Jetson 멀티모델 Jetlink 개발계획 (2026-10-19)

> 이 문서는 2026-10-19 현재 소스를 다시 대조해 정리한 **새 기준 계획**이다.
> 기존 `docs/V3_JETSON_PLAN.md`의 protocol-2 Cinque V3 force-fit은 폐기하지 않지만,
> 신규 개발의 주 경로로 사용하지 않는다. 기존 패치의 실기 적용도 이 문서의 사전점검 전에는 금지한다.

## 1. 결론

현재 가장 합리적인 방향은 **Carrot R2 전체 OS를 최신 zoompilot Jetlink로 교체하는 것**도,
**옛 protocol 2 서버에 V3 하나만 억지로 끼우는 것**도 아니다.

목표 구조는 다음과 같다.

```text
comma4 / carrot-wip
  ├─ 기존 내부 small model (항상 fallback)
  ├─ Jetlink protocol 3 client
  ├─ dynamic ModelSpec / stateful parser
  └─ offroad-only 모델 승인·선택
               │
               │ USB 3
               ▼
Carrot Jetson R2 / Orin Nano Super
  ├─ 기존 V2 engine 보존
  ├─ protocol 3 host/server 추가
  ├─ TensorRT 10.3용 engine cache
  ├─ Cinque Terre V3
  ├─ 이후 BMRLNAP v6 등 검증된 모델
  └─ 실패 시 명시적 NOT_READY/ERROR → comma 내부 모델 복귀
```

**1차 목표는 V2 + Cinque V3 두 모델만 안전하게 선택 가능하게 하는 것**이다.
BMRLNAP v6, Lebowski, Mountain Dew 계열은 같은 프레임워크가 검증된 뒤 추가한다.

## 2. 2026-10-19 기준 소스 베이스라인

### 사용자 백포트 저장소

- repository: `rownlvh8875-coder/jetson-v3-backport`
- 기존 개발 branch: `feature/cinque-v3-jetson`
- 기준 HEAD: `26c9c06a5e51ff0e8d3a1e8575eece548e87f3b5`
- 이 계획 branch: `feature/jetlink-multimodel-carrot`

기존 branch에는 다음 자산이 이미 있다.

- 실제 Cinque V3 ONNX에서 생성한 `artifacts/cinque_v3.json`
- TensorRT 10.3용 `tools/build_trt_v3.py`
- stateful state 관리와 검증 코드
- V3 recurrent/finite/shape/identity 테스트
- 과거 protocol-2 host 백포트 패치
- Nav ONNX 분석 자료

이 자산은 버리지 않고 **TRT 10.3 모델 빌드·stateful 검증 oracle**로 재사용한다.

### 현재 carrot-wip

2026-10-19 조회:

- repository: `ajouatom/openpilot`
- branch: `carrot-wip`
- HEAD: `5032afca77a96e31a077a5e9ac738d9ac08a99df`

기존 이 저장소가 고정했던 `029ab60e...` 이후 100개가 넘는 커밋이 진행됐다.
따라서 과거 `comma-integration-v3.patch`를 현재 carrot-wip에 그대로 적용하면 안 된다.

현재 carrot-wip에는 이미 다음 기반이 들어가 있다.

- strict protocol 2 / protocol 3 wire 선택
- protocol 3 framing 및 client
- queued / stateful `ModelSpec`
- stateful 모델의 dynamic packed input
- dynamic output parsing
- 외부 모델 변경 시 fail-closed
- offroad-only model approval
- App-selected 모델의 spec 검증
- external model 실패 시 local small model 복귀
- Jetlink 상태/health/Web 표시

즉 **comma 쪽 V3 stateful 지원 자체를 다시 만드는 것은 중복 작업**이다.

### 현재 carrot-jetson

2026-10-19 조회:

- repository: `ajouatom/carrot-jetson`
- main HEAD: `d0dc96fa32410403dfb2fefff3e2909c11ec109b`
- base OS metadata: L4T 36.4.7 / TensorRT 10.3.0 / aarch64
- vendored Jetlink: `194ff6dc71cd27282378fff155e94daa7770152b` (0.3.0a1)

따라서 **실제 주된 미완성 구간은 Jetson host/server**다.

### 최신 zoompilot/jetlink 참고

2026-10-19 조회한 main HEAD:

- `d24328d849b0e5154b55f149dc18c5dfe8bd79cc`

최신 upstream은 이미 model catalog, protocol 3, stateful 모델, 모델 전환,
Swift server, Jetson 성능 최적화까지 포함한다.

단, 공개 성능 측정 환경은 Carrot R2와 다르다.

- upstream bench: JetPack 7.2.1 / TensorRT 10.16.2.10 / MAXN SUPER
- Carrot R2 baseline: L4T 36.4.7 / TensorRT 10.3.0

따라서 **최신 Jetson 바이너리를 그대로 복사하지 않는다.**
protocol/selection/registry 설계는 참고하되, 현재 R2의 TensorRT 10.3에서 다시 빌드·실측한다.

## 3. 기존 계획에서 바뀌는 핵심

### 폐기하지 않지만 주 경로에서 제외

다음은 과거 연구/비상 fallback 자료로 보존한다.

- `patches/jetson-production-v3.patch`
- `patches/comma-integration-v3.patch`
- protocol 2 위에서 stateful V3를 force-fit하는 경로
- `CARROT_JETLINK_V3=1` 단일 모델 opt-in 방식

이유:

1. 현재 carrot-wip 자체가 protocol 3 + dynamic stateful 모델을 이해한다.
2. protocol 2에 stateful V3를 별도 확장하면 upstream과 다른 독자 규약을 계속 유지해야 한다.
3. 멀티모델 목표에는 protocol 3의 server-owned recurrent state가 더 자연스럽다.
4. 향후 모델 추가 때 모델별 comma 패치를 만드는 구조를 피할 수 있다.

### 계속 재사용

- `artifacts/cinque_v3.json`
- ONNX identity/hash gate
- TensorRT 10.3 build helper
- UINT8 recurrent image patch 검증
- state input/output pair 검증
- finite/shape validation
- recurrent lockstep parity 검사
- latency 측정 코드
- V2 회귀 검사
- fail-closed 원칙

## 4. 목표 아키텍처

### 4.1 comma 쪽

현재 carrot-wip의 다음 코드를 최대한 그대로 사용한다.

- `openpilot/selfdrive/modeld/jetlink/contracts.py`
- `compat.py`
- `link.py`
- `model.py`
- `selection.py`
- `daemon.py`

필요한 신규 변경은 작게 제한한다.

#### A. Jetson protocol-3 peer를 명시적으로 구분

현재 App provisioning은 Mac/iOS/Android를 대상으로 한다.
Jetson이 protocol 3을 사용한다고 Mac/Android로 위장시키면 안 된다.

추가 방향:

```python
def is_jetson_peer(peer):
    return (
        isinstance(peer, dict)
        and peer.get("protocol") == 3
        and peer.get("carrot_host") == "jetson"
        and peer.get("backend") == "trt"
    )
```

실제 필드는 장치 HELLO를 읽은 뒤 확정한다. 위 코드는 설계 예시이며
검증 전 제품 코드에 그대로 넣지 않는다.

#### B. protocol-3 Jetson의 loaded model을 offroad에서 승인

현재 `mac.prepare()`의 legacy protocol-3 비-App 경로는 기본 V2 `SPEC.sha256`을 선택한다.
멀티모델 Jetson에서는 다음이 필요하다.

- Jetson이 HELLO/STATE에서 현재 `loaded` SHA와 full spec을 보고
- comma가 지원 계약을 `validate_model_spec()`으로 검증하고
- 처음 보는 SHA는 ignition-off에서만 승인
- 승인된 모델은 재연결 시 exact spec이 같을 때만 사용
- onroad에서 다른 SHA로 바뀌면 즉시 session 폐기/fallback

**임의 SHA를 신뢰하지 않는다.**

#### C. Web selector는 2차

첫 하드웨어 검증 전에는 Web UI를 만들지 않는다.
처음에는 개발용 명시적 선택만 사용하고, 선택/빌드/추론이 안정된 뒤
웹당근에 selector를 추가한다.

최종 UI 후보:

```text
Jetlink 모델
  Cinque Terre V2       Ready
  Cinque Terre V3       Active
  BMRLNAP v6            Not built
  Lebowski              Unsupported / unverified
```

모델 변경은 반드시 offroad/parked gate를 통과한다.

### 4.2 Jetson 쪽

Jetson은 다음 기능을 제공해야 한다.

1. protocol 3 HELLO
2. STATE
3. ENGINE_REQ
4. engine build/load 상태
5. INFER_REQ/RESP
6. stateful recurrent state를 server 내부에서 유지
7. RESET_QUEUES
8. telemetry
9. 모델 generation/identity 변경 감지
10. 오류 시 NOT_READY/INFER_FAILED/NOT_FINITE

현재 R2의 Python/TensorRT 10.3 경로를 우선 활용한다.

**Swift upstream server 전체 이식은 1차 목표가 아니다.**

이유:

- 현 R2의 TensorRT ABI와 upstream bench 환경이 다름
- 기존 Carrot R2의 protected runtime/update 구조를 유지해야 함
- 이미 백포트 저장소에 Python TensorRT 10.3 stateful 실행기가 있음

## 5. 모델 관리 전략

### 단계 1 — 고정 두 모델

먼저:

- Cinque V2: 기존 정상 기준
- Cinque Terre V3: `404a18cf...`, 766354845 bytes

두 모델만 등록한다.

V3의 full spec은 기존 `artifacts/cinque_v3.json`과 실제 ONNX를 다시 대조한다.

### 단계 2 — BMRLNAP v6

V2/V3 구조가 검증된 다음 BMRLNAP v6를 추가한다.

추가 전 필수:

- 출처 ref/ONNX SHA/size 확인
- named input/output 실제 파싱
- `validate_model_spec` 통과 여부
- TensorRT 10.3 parse/build
- ORT↔TRT recurrent parity
- Jetson 20 Hz 실측

### 단계 3 — 그 외 모델

Lebowski는 upstream에서 Orin Nano Super 구동 사례가 있지만 약 1.76 GB이고
Carrot R2 8 GB / TensorRT 10.3에서 메모리·열 여유가 별도 검증되지 않았다.
따라서 초기 대상에서 제외한다.

Mountain Dew/ResAction 등 최신 모델도 **카탈로그에 있다는 이유만으로 활성화하지 않는다.**
각 모델의 ONNX contract와 현재 Carrot parser 호환성을 개별 검증한다.

## 6. 미리 할 수 있는 코드 작업

하드웨어 접속 전에 진행 가능:

1. 이 문서와 source baseline 고정
2. read-only Jetson inventory 도구 준비
3. 기존 V3 TensorRT builder를 protocol-3 host용으로 재사용할 인터페이스 정리
4. 현재 carrot-wip의 `ModelSpec` JSON과 `artifacts/cinque_v3.json` round-trip 검사
5. Jetson HELLO/STATE/ENGINE/INFER protocol-3 loopback fixture 준비
6. V2/V3 선택 정책 단위 테스트
7. 모델 변경 중/실패 시 fallback 테스트
8. Web selector API contract만 문서화

하드웨어 없이는 확정하면 안 되는 것:

- 실제 설치된 runtime path
- 실제 service 이름/ExecStart
- SSD에 설치된 release version
- 실제 TensorRT Python/C++ API 조합
- V3 engine build 성공
- 실제 USB protocol-3 호환
- 20 Hz 성능
- 열/전력/throttle
- 반복 stop/restart 동작

## 7. 첫 Jetson SSH 접속 시 작업 순서

### M0 — 읽기 전용 inventory

`tools/jetson_runtime_inventory.py`를 실행한다.

확인:

- NVMe boot 여부
- L4T / kernel
- TensorRT / CUDA
- nvpmodel / clocks
- Jetlink service 상태
- 설치 runtime/cache 경로
- 기존 engine/model 파일 위치와 크기
- 현재 network address
- 기존 V2를 실행하는 실제 binary/module 경로

**이 단계에서는 서비스 재시작·파일 변경·모델 build를 하지 않는다.**

### M1 — 개발 복제본에서 host protocol 3

실장치 운영 경로를 직접 수정하지 말고, writable 개발 경로에 복제하여:

- protocol 3 HELLO/STATE 확인
- V2 engine으로 protocol-3 inference loopback
- comma 없이 local synthetic frame으로 server contract 검사

V2 출력과 기존 protocol-2 V2 출력을 비교한다.

### M2 — Cinque V3 engine

- V3 ONNX 전체 SHA 확인
- TensorRT 10.3 engine build
- warm/reset
- 5-frame 이상 recurrent parity
- 반복 1000+ frame finite/state continuity
- 엔진 unload/reload 후 동일 contract 확인

### M3 — comma4 USB 통합

차량 제어와 분리된 상태에서:

- USB SuperSpeed
- protocol 3 HELLO
- full spec 승인
- camera warp → Jetson → result → parser
- model identity/status 확인
- intentional disconnect/fault → local model fallback

### M4 — 성능

기록:

- GPU time
- queue time
- Jetson server total
- USB round trip
- comma `modelExecutionTime`
- p50/p95/p99/max
- dropped/failed frames
- temperature
- memory
- throttle/over-current 여부

20 Hz는 프레임당 50 ms다. **timeout을 늘려서 합격시키지 않는다.**

upstream의 Cinque V3 24.5/25.8 ms(p50/p99)는 다른 JetPack/TRT 환경의 참고값일 뿐
우리 장치 합격 수치로 복사하지 않는다.

### M5 — V2/V3 선택

- ignition off에서 V2↔V3 변경
- engine already-built path
- engine missing path
- bad spec/SHA 거부
- onroad model mutation 거부
- reconnect 후 승인 유지
- reset 후 recurrent state 초기화

### M6 — Web selector

M0–M5가 통과한 뒤 웹당근에 선택 UI/API를 추가한다.
선택은 정차/offroad에서만 허용하고 활성 모델과 선택 모델을 따로 표시한다.

### M7 — 추가 모델

BMRLNAP v6부터 하나씩 같은 gate를 통과시킨다.

## 8. 롤백 계약

항상 아래가 성립해야 한다.

1. 기존 V2 engine/파일을 삭제하지 않는다.
2. 새 기능 flag/selection이 없으면 기존 Jetson V2 또는 내부 small model로 동작한다.
3. protocol/model/spec 오류는 자동으로 다른 임의 big model을 선택하지 않는다.
4. external model이 active 중 실패하면 기존 carrot-wip fallback 경로를 사용한다.
5. 주행 중 모델 선택/빌드/업로드를 시작하지 않는다.
6. 기존 timeout/finite/shape gate를 완화하지 않는다.

## 9. 코드 변경 우선순위

### 지금 작성 가능 — 이 저장소

- [x] 최신 개발방향 문서
- [x] read-only runtime inventory 도구
- [ ] current carrot-wip protocol-3 Jetson peer 정책 fixture
- [ ] protocol-3 Jetson host loopback fixture를 최신 wire contract로 갱신
- [ ] V2/V3 local model catalog fixture
- [ ] V3 builder와 server engine cache adapter 분리

### Jetson inventory 후 작성

- [ ] R2 host protocol-3 adapter
- [ ] TensorRT 10.3 multi-engine manager
- [ ] selected/loaded/active model 상태
- [ ] server telemetry/generation
- [ ] systemd integration용 patch

### comma integration

현재 carrot-wip가 상당 부분 준비돼 있으므로 최소 patch만 목표로 한다.

예상 수정 후보:

- `openpilot/common/jetlink_peer.py`
- `openpilot/selfdrive/modeld/jetlink/mac.py`
- 필요 시 `contracts.py`의 모델 name/display metadata
- Web selector 단계에서 carrot server + JS

**`model.py`, `link.py`, parser를 먼저 뜯지 않는다.**
현재 dynamic stateful 경로를 재사용하는 것이 우선이다.

## 10. 현재 GO / NO-GO

| 항목 | 상태 |
|---|---|
| 개발방향을 protocol 3 + multi-model로 전환 | GO |
| 기존 V3 TensorRT 10.3 자산 재사용 | GO |
| 현재 carrot-wip dynamic stateful 경로 재사용 | GO |
| 옛 protocol-2 V3 패치를 현재 차량에 적용 | NO-GO |
| 최신 upstream Jetson 바이너리를 R2에 그대로 복사 | NO-GO |
| Jetson read-only inventory | GO |
| 실제 host 코드 설치/서비스 재시작 | inventory 후 별도 진행 |
| V3 실차 사용 | USB/성능/fallback 검증 전 NO-GO |
| 다른 모델 일괄 활성화 | NO-GO |

## 11. 다음 실제 작업

Jetson에 전원을 넣고 SSH가 되는 시점에 첫 명령은 build/install이 아니다.

```bash
python3 tools/jetson_runtime_inventory.py --pretty
```

그 결과를 저장해 현재 R2 설치 상태와 이 문서의 예상치를 대조한다.
그 뒤 **실제 설치 경로를 기준으로** host protocol-3 patch를 생성한다.

이 순서를 지키면 기존 SSD의 정상 V2 환경을 보존한 상태로 V3/multi-model 개발을 이어갈 수 있다.
