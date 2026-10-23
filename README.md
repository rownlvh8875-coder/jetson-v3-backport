# jetson-v3-backport

> **2026-10-19 현재 기준:** 개발 주 경로를 **protocol 3 + Jetson 멀티모델**로 전환했다.
> 현재 `carrot-wip`는 이미 protocol 3, dynamic `ModelSpec`, stateful 모델 parsing/fallback 기반을 갖고 있다.
> 따라서 과거 protocol-2 Cinque V3 force-fit은 역사/비상 fallback 자료로 보존하고,
> 신규 작업은 [Carrot × Jetson 멀티모델 개발계획](docs/JETLINK_MULTIMODEL_PLAN_20261019.md)을 따른다.
> 실제 Jetson 적용 전에는 [read-only runtime inventory](tools/jetson_runtime_inventory.py)로
> SSD에 설치된 R2 runtime/service/TensorRT 경로를 먼저 확인한다.

**최신 작업 인계:** [CODEX_CONTINUATION.md](docs/CODEX_CONTINUATION.md).
현재 source adapter, 검증 결과와 원복 절차는
[current candidate 검증 안내](docs/CURRENT_CARROT_VALIDATION_20261019.md)에 있다.
최신 upstream 확인과 분리된 CPU 검증은
`python tools/check_latest_carrot_compat.py --update-baseline`으로 실행한다.
2026-10-23 [M0.5 비교](docs/M05_CARROT_NAV_VS_WIP_20261023.md)는 **전략 A**를 추천한다.
실제 comma의 `carrot-nav`와 운영 Protocol2/V2/Nav를 보존하고 필요한 managed P3 부분만 별도 준비한다.
[M1 실기 기록](docs/M1_JETSON_V3_TRT10_BUILD_20261023.md): 격리 경로에서 실제 Orin/TRT10.3
V3 빌드와 BASE 10+1000프레임/reset/reload 검사를 통과했다. ORT↔TRT는 수치 측정만 했으며
승인 허용오차가 없다. **DO_NOT_INSTALL**. USB/comma 추론·fallback·차량 검증은 NOT_RUN이다.

2026-10-23 [M1.5 semantic 비교](docs/M15_ORT_TRT_PARITY_20261023.md)는 실제 ORT/TRT
101프레임과 Nav parser를 측정했다. desire 예측 불일치 1건과 미승인 허용오차로
**PARITY_UNDETERMINED / M2 readiness NO**다. [최소 Nav adapter](docs/M15_CARROT_NAV_PROTOCOL3_ADAPTER_20261023.md)는
별도 개발 사본에서 P2/V2/Nav 회귀와 P3/fallback CPU 검증을 통과했다.
[M2 정차 USB 계획](docs/M2_PARKED_USB_PLAN_20261023.md)은 실행하지 않았다.

2026-10-23 [M1.6 정밀 분석](docs/M16_NUMERICAL_ACCEPTANCE_20261023.md): 기존 plan 그대로
historical512프레임의 독립 recurrence와 teacher forcing을 측정했다. 최대 plan/lead 차이는
각각 10초 horizon의 x이고, desire 예측 flip은 작은 top2 margin에서 재현된다.
128-slot turnover는 도달했으나 대표 기록 입력·승인 기준은 없으며 bounded TRT는
deserialize OOM으로 0프레임이다. **PARITY_UNDETERMINED / M2 NO**, 운영본·adapter는 보존했다.

2026-10-20 [외부 Jetson 최적화 검토](docs/JETSON_REVIEW_A890_ANALYSIS.md):
DeviceState와 InputFastpath는 기존 검증을 유지한 기본 OFF 실험 후보다.
AIO는 운영 transport에 연결하지 않았으며, 실장 순서는 M0 → 기본 V3 → USB →
latency 측정 → 필요한 최적화 A/B를 유지한다.

> Jetson Orin Nano Super에서 Cinque V3 및 호환 Big Model을
> Carrot/comma4와 안전하게 연결하기 위한 연구·백포트 저장소

## 현재 목표

1차 목표는 **기존 V2를 보존한 채 Cinque Terre V3를 protocol 3으로 추가**하고,
정차/offroad에서 V2↔V3를 선택할 수 있게 만드는 것이다.

그 다음 같은 프레임워크로 BMRLNAP v6 등 호환 모델을 하나씩 검증한다.
Lebowski나 최신 Mountain Dew 계열은 모델 목록에 있다는 이유만으로 자동 허용하지 않는다.

목표 구조:

```text
comma4 / carrot-wip
  ├─ local small model fallback
  ├─ Jetlink protocol 3
  ├─ dynamic queued/stateful ModelSpec
  └─ offroad model approval
             │ USB 3
             ▼
Carrot Jetson R2 / Orin Nano Super
  ├─ existing V2 engine
  ├─ protocol 3 host
  ├─ TensorRT 10.3 engine cache
  └─ V3 → 이후 검증된 추가 모델
```

## 왜 방향이 바뀌었나요?

이 저장소를 처음 만들 때는 Carrot의 Jetson 경로가 사실상 protocol 2 + Cinque V2 고정이어서
stateful V3를 직접 백포트해야 했다.

하지만 2026-10-19 현재 `ajouatom/openpilot:carrot-wip`에는 다음 기반이 이미 들어가 있다.

- strict protocol 2/3 wire
- queued/stateful `ModelSpec`
- dynamic packed input/output parser
- protocol 3 App-selected 모델 검증
- offroad-only approval
- external model failure → internal small model fallback

그래서 지금의 핵심 공사는 **comma 쪽 V3를 다시 만드는 것**이 아니라
**Carrot Jetson R2 host/server를 protocol 3 + multi-engine 구조로 올리는 것**이다.

## 소스 기준

2026-10-19 조사 기준:

| 구성 | 기준 |
|---|---|
| 이 저장소 기존 V3 branch | `feature/cinque-v3-jetson @ 26c9c06a...` |
| 현재 개발 branch | `feature/jetlink-multimodel-carrot` |
| carrot-wip | `5032afca77a96e31a077a5e9ac738d9ac08a99df` |
| carrot-jetson | `d0dc96fa32410403dfb2fefff3e2909c11ec109b` |
| zoompilot/jetlink 참고 | `d24328d849b0e5154b55f149dc18c5dfe8bd79cc` |
| Carrot R2 metadata | L4T 36.4.7 / TensorRT 10.3.0 / aarch64 |

최신 zoompilot Jetlink의 Jetson benchmark는 JetPack 7.2.1 / TensorRT 10.16 계열이므로
그 바이너리/성능 수치를 현재 R2에 그대로 적용하지 않는다.

## 폴더 설명

| 폴더/파일 | 내용 |
|---|---|
| `docs/JETLINK_MULTIMODEL_PLAN_20261019.md` | **현재 개발 기준**. protocol 3 + 멀티모델 로드맵 |
| `docs/CURRENT_CARROT_HOST_GAPS_20261019.md` | current carrot-wip server에서 실제로 남은 V3 gap을 파일 단위로 정리 |
| `tools/jetson_runtime_inventory.py` | 첫 SSH 접속 때 쓰는 read-only runtime 조사 도구 |
| `jetlink/multimodel_policy.py` | managed protocol-3 Jetson 선택 계약 proposal |
| `artifacts/multimodel_seed.json` | V2/V3 초기 로컬 seed identity |
| `docs/PROJECT_STATE.md` | 2026-10-11까지의 세부 구현/검증 기록 |
| `docs/V3_JETSON_PLAN.md` | 과거 단일 V3 force-fit 계획. 신규 주 경로 아님 |
| `artifacts/cinque_v3.json` | 실제 V3 ONNX에서 생성한 모델 계약 |
| `tools/build_trt_v3.py` | TensorRT 10.3 V3 engine build/verify 도구 |
| `tools/jetson_m1.py`, `tools/jetson_m1_recurrent.py` | 격리·offroad guard와 실제 BASE 반복 추론 도구; M1 보고서의 실행 조건 필수 |
| `tools/jetson_m1_parity.py` | 원본 ORT CPU와 BASE TRT의 독립 recurrent 수치 비교; 허용오차 없으면 exit3 |
| `jetlink/` | stateful spec/state/registry 백포트 자산 |
| `tests/` | recurrent/finite/identity/loopback 등 회귀검사 |
| `patches/` | 과거 고정 SHA용 실험 패치. 현재 carrot-wip에 무조건 적용 금지 |
| `REPORT.md` | 2026-10-05까지의 초기 백포트 보고서 |

## 이미 확보된 자산

- Cinque V3 ONNX identity:
  - SHA256 `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`
  - size `766354845` bytes
- 실제 ONNX 기반 `cinque_v3.json`
- TensorRT 10.3 builder
- stateful recurrent state 관리
- finite/shape/identity gate
- V2 회귀검사
- recurrent multi-frame parity 도구
- fail-closed 설계 자료

## 실기 확인 상태

M0에서 NVMe/runtime/release/service와 패키지를 조사했고, M1에서 실제 TRT/CUDA API,
V3 engine build와 합성 입력 BASE 반복 추론을 확인했다. 전후 운영 cache/service/current는 동일하다.
수치 parity 승인과 다음 항목은 남아 있다.

- protocol-3 USB host/server
- comma camera → Jetson → parser end-to-end
- 20 Hz latency
- 열/전력/throttle
- link/model failure 시 실제 local model fallback
- V2↔V3 전환
- 정지→재출발 거동

## 어디서부터 시작하나요?

**현재 작업** → [JETLINK_MULTIMODEL_PLAN_20261019.md](docs/JETLINK_MULTIMODEL_PLAN_20261019.md)

Jetson SSH가 준비되면 첫 단계:

```bash
python3 tools/jetson_runtime_inventory.py --pretty
```

이 명령은 설치·서비스 재시작·모델 build를 하지 않고 현재 runtime을 읽기만 한다.

과거 구현 맥락 → [PROJECT_STATE.md](docs/PROJECT_STATE.md)

초기 백포트 전체 보고 → [REPORT.md](REPORT.md)

## 주의

- 기존 정상 V2 환경을 먼저 보존한다.
- 과거 `jetson-production-v3.patch` / `comma-integration-v3.patch`를 현재 HEAD에 그대로 적용하지 않는다.
- 최신 upstream Jetson binary를 Carrot R2에 바로 복사하지 않는다.
- 모델 build/download/선택은 offroad에서만 한다.
- 실제 USB·latency·fallback 검증 전에는 V3 주행 사용을 완료로 선언하지 않는다.
- v3가 정지·재출발 흔들림을 개선한다는 것은 아직 실증되지 않았다.
