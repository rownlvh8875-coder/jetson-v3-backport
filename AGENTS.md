# 프로젝트 목표와 작업 제한

2026-10-11 사용자 지시가 과거 인계 문서와 미수행 범용 변환기 계획보다 우선한다.
현재 기준은 [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md)와
[docs/V3_JETSON_PLAN.md](docs/V3_JETSON_PLAN.md)이다.

- 대상은 `artifacts/cinque_v3.json`에 기록된 Cinque V3 ONNX 한 개다.
  SHA256 `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`,
  크기 `766354845` bytes. JSON 존재와 실제 원본 확보를 혼동하지 않는다.
- 최종 목표는 Jetson Orin Nano Super의 반복 추론, 당근 기존 연결을 통한
  comma 카메라 입력·결과 반환·출력 해석, 처리속도와 state 연속성,
  실패 시 내부 모델 복귀와 오류 알림의 실제 확인이다. 엔진 생성만으로 완료하지 않는다.
- 현재는 승인된 2단계다. V3 원본 확보, CPU 안전성 검사, V3 ONNX 가공·TRT 빌더·
  수치 검증기와 집중 회귀 테스트, 관련 문서를 수정할 수 있다. 원본 명세를 조용히 변경하지 않는다.
  Jetson session/queues 운영 통합과 comma protocol/모델 선택·전처리·parser 수정은 3단계 이후다.
- 이번 단계는 검증된 코드·테스트·진행 문서를 작은 커밋으로 남긴다. 개발 브랜치를 보존하여
  이어가고 새 작업/main에서는 `feature/cinque-v3-jetson`을 사용한다.
  main 직접 수정·병합, force push, reset --hard, 사용자 변경 삭제는 금지한다.
- 실제 comma/Jetson 설치·설정·서비스·모델 선택·Params를 변경하지 않는다.
  진행 중인 사용자 프로세스를 임의로 종료하지 않는다. 차량 제어·도로 주행은 금지한다.
- 참고 코드는 고정한 carrot-jetson / carrot-wip의 연결·전처리·명세·TensorRT·state·출력·복귀와
  직접 의존 코드·테스트만 조사한다. 실제 설치 버전은 별도 확인 전 미확인이다.
- stateful 처리, 출력 검사, prev_feat 분기, 내부 모델 복귀는 기존 기능을 재사용한다.
  과거 리뷰와 패치는 현재 코드·고정 SHA에 대조한 뒤 필요한 차이만 채택한다.
- V2는 기존 동작 보존·회귀 확인용이다. 범용 카탈로그·플러그인·CLI,
  MDM V1/V2·carrot-mdm2, PKL 역변환, 재학습·INT8, eGPU/다른 런타임 이전,
  GUI/대시보드, 주행 튜닝, SD/SSD·Wi-Fi·부팅·자동 업데이트 개편은 제외한다.
- 대형 모델·엔진·영상·인증정보를 Git에 올리지 않는다. TLS 검증 해제,
  임의 PKL 실행, 운영 패키지 강제 업그레이드는 금지한다.
- 결과는 PASS/FAIL/SKIP/BLOCKED, 실행 명령과 코드 전체 SHA를 기록한다.
  mock·합성 fixture·실제 ONNX·TensorRT·Jetson 실측을 구분한다.
  테스트 완화/삭제로 통과시키지 않는다. 주행로그 추가 수집은 선행조건이 아니다.
