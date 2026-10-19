# 프로젝트 목표와 작업 제한

2026-10-19 사용자 지시와
[docs/JETLINK_MULTIMODEL_PLAN_20261019.md](docs/JETLINK_MULTIMODEL_PLAN_20261019.md)가
이 저장소의 **현재 개발 기준**이다.

2026-10-11의 [PROJECT_STATE](docs/PROJECT_STATE.md)와
[V3_JETSON_PLAN](docs/V3_JETSON_PLAN.md)은 검증 이력과 기존 자산을 제공하지만,
protocol-2 단일 V3 force-fit을 신규 주 경로로 적용하지 않는다.

- 목표는 Carrot R2 / Jetson Orin Nano Super에서 **기존 V2를 보존한 채**
  protocol 3 host와 multi-engine 선택 기반을 만들고, 우선 Cinque V3를 검증하는 것이다.
  이후 호환 모델은 한 개씩 같은 gate를 통과시킨다.
- 현재 carrot-wip 기준 SHA는 조사 시점 `5032afca77a96e31a077a5e9ac738d9ac08a99df`,
  carrot-jetson main은 `d0dc96fa32410403dfb2fefff3e2909c11ec109b`다.
  소스가 이동했으면 새 HEAD를 다시 고정하고 diff부터 조사한다.
- 현재 carrot-wip에는 protocol 3, dynamic queued/stateful ModelSpec, parser,
  model approval 및 fallback 기반이 이미 있다. **기존 기능을 재사용하고 중복 구현하지 않는다.**
- 과거 `patches/jetson-production-v3.patch`, `comma-integration-v3.patch`,
  `CARROT_JETLINK_V3=1` 경로는 역사/비상 fallback 자산이다.
  현재 carrot-wip/실장치에 사전 대조 없이 적용하지 않는다.
- `artifacts/cinque_v3.json`, TensorRT 10.3 builder, stateful state 처리,
  finite/shape/identity gate, parity/latency 도구는 재사용한다.
- 첫 실장치 단계는 **read-only inventory**다.
  `tools/jetson_runtime_inventory.py` 또는 동등한 읽기 전용 명령으로
  실제 NVMe boot, L4T, TensorRT/CUDA, service, ExecStart, runtime/cache 위치를 확인한다.
  이 단계에서는 서비스 재시작, 파일 변경, build/load, GPU 초기화, Params 변경을 하지 않는다.
- 주소/IP는 사용자가 제공하거나 이미 정상 SSH 경로가 확인된 경우 사용한다.
  사용자 승인 없이 광범위 네트워크 스캔을 하지 않는다.
- 실제 개발은 운영 runtime을 바로 덮어쓰지 않고 writable 개발 사본/별도 경로에서 시작한다.
  기존 V2 파일/engine을 삭제하지 않는다.
- 1차 구현 순서는 V2 protocol-3 loopback → Cinque V3 TensorRT 10.3 →
  comma USB 통합 → latency/fallback → V2/V3 선택이다.
  Web selector와 추가 모델은 그 다음이다.
- Jetson protocol-3 peer를 Mac/iOS/Android로 위장시키지 않는다.
  `carrot_host=jetson` 등 실제 HELLO identity를 명시적으로 검증하는 별도 경로를 사용한다.
- 처음 보는 모델/SHA/spec 승인과 모델 build/download는 offroad에서만 허용한다.
  onroad model identity/spec 변경은 session 폐기와 fallback으로 처리한다.
- V2는 정상 기준이자 rollback 대상이다. external model 실패 시
  현재 carrot-wip의 local small model fallback을 보존한다.
- timeout, finite, shape, identity gate를 테스트 통과를 위해 완화하지 않는다.
- 최신 zoompilot/jetlink는 설계 참고다. JetPack 7.2.1 / TRT 10.16 성능·binary를
  L4T 36.4.7 / TRT 10.3 Carrot R2에 그대로 적용하지 않는다.
- 추가 모델(BMRLNAP v6, Lebowski, Mountain Dew/ResAction 등)은
  카탈로그 존재만으로 허용하지 않는다. ONNX source/hash/spec, TRT 10.3 build,
  recurrent parity, 20 Hz 실측을 개별 확인한다.
- 대형 모델·engine·영상·SSH private key·Wi-Fi secret·차량 식별정보를 Git에 올리지 않는다.
  TLS 검증 해제, 임의 PKL 실행, 운영 패키지 강제 업그레이드는 금지한다.
- 개발 branch는 `feature/jetlink-multimodel-carrot`를 사용한다.
  main 직접 수정·병합, force push, reset --hard, 사용자 변경 삭제는 금지한다.
- 결과는 PASS/FAIL/SKIP/BLOCKED로 구분하고 코드 SHA, 실행 명령, 환경을 기록한다.
  mock/fixture, ORT CPU, TensorRT, 실제 Jetson/USB, 차량 검증을 섞어 표현하지 않는다.
- 차량 주행은 protocol/USB/성능/fallback이 정지 상태에서 검증된 뒤 별도 단계로 다룬다.
  정지→재출발 흔들림이 V3에서 개선된다고 선결론 내리지 않는다.
