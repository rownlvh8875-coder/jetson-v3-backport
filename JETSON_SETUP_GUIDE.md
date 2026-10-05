# Jetson 실기 작업 가이드 (Cinque v3 백포트)

> 대상: Jetson Orin Nano Super / L4T 36.4.7 / TensorRT 10.3.0 / Carrot R2 이미지
> 전체 흐름: 파일 가져오기 → 모델 받기 → 패치 붙이기 → 엔진 만들기 → 테스트
> 각 단계의 **확인** 항목을 보고 넘어갈 것. 막히면 멈추고 로그를 남길 것.

## 0단계: 준비

- 집 노트북에서 Jetson에 SSH 접속 (`jetlink` 계정, 키 인증)
- 아래 명령어는 전부 Jetson에 접속한 상태에서 입력

## 1단계: 작업 파일 가져오기

```bash
git clone https://github.com/rownlvh8875-coder/jetson-v3-backport
cd jetson-v3-backport
```

`ls` 했을 때 `tools`, `patches`, `artifacts` 폴더가 보이면 성공.

## 2단계: v3 모델 파일 받기 (766MB, 시간 소요)

```bash
mkdir -p artifacts
pip install -U huggingface_hub
hf download commaai/openpilot_driving_models \
  --include "f78ed37d-*/12864/big_driving_supercombo.onnx" \
  --local-dir ./hf_tmp
cp ./hf_tmp/f78ed37d-*/12864/big_driving_supercombo.onnx \
   artifacts/big_driving_supercombo_v3.onnx
```

**확인 (중요):**

```bash
ls -la artifacts/big_driving_supercombo_v3.onnx
sha256sum artifacts/big_driving_supercombo_v3.onnx
```

- 파일 크기: **766354845** 바이트
- sha256: **404a18cf** 로 시작
- 안 맞으면 지우고 다시 받기

## 3단계: 설정 파일 복사

```bash
cp artifacts/cinque_v3.json <comma의 jetlink 폴더>/
```

`<comma의 jetlink 폴더>` = comma 4의 openpilot 설치 경로 밑 `selfdrive/modeld/jetlink/`.
정확한 경로는 각자 환경에 맞게 변경.

## 4단계: 패치 6개 적용

Jetson 쪽 4개는 carrot-jetson 설치 폴더에서:

```bash
cd <carrot-jetson 폴더>
patch -p1 < ~/jetson-v3-backport/patches/jetson-spec-stateful.patch
patch -p1 < ~/jetson-v3-backport/patches/jetson-queues-stateful.patch
patch -p1 < ~/jetson-v3-backport/patches/jetson-lfs-export-fallback.patch
patch -p1 < ~/jetson-v3-backport/patches/jetson-session-stateful.patch
```

comma 쪽 2개는 openpilot 폴더에서:

```bash
cd <openpilot 폴더>
patch -p1 < ~/jetson-v3-backport/patches/comma-link-model-select.patch
patch -p1 < ~/jetson-v3-backport/patches/comma-model-stateful.patch
```

"patching file ..." 메시지가 뜨면 성공. 실패하면 멈출 것.

## 5단계: TensorRT 엔진 빌드 (약 3분)

```bash
cd ~/jetson-v3-backport
python3 tools/build_trt_v3.py \
  --onnx artifacts/big_driving_supercombo_v3.onnx \
  --spec artifacts/cinque_v3.json \
  --out artifacts/cinque_v3.engine \
  --verify
```

**확인:** `artifacts/cinque_v3.engine` 생성 + verify 통과.

## 6단계: 정지 상태 테스트 (주행 금지)

```bash
export CARROT_JETLINK_MODEL_JSON=/home/jetlink/jetson-v3-backport/artifacts/cinque_v3.json
export CARROT_JETLINK_MODEL_LABEL='Cinque v3'
```

이 상태에서 jetlink 서버를 재시작하고, **차는 세워둔 채로** 추론 로그가
정상인지(출력 숫자가 깨지지 않는지, finite인지) 확인.
여기 통과하기 전에는 절대 주행하지 말 것.

## 7단계: 최소 주행 확인

- 짧게, 저속으로, 한적한 곳에서만
- 이상 없으면 OK

이상 징후(급조향, 차선 이탈, 흔들림 악화) 발생 시 즉시 개입 후 롤백:

```bash
unset CARROT_JETLINK_MODEL_JSON
```

재시작하면 기본값 v2로 복귀 (fail-closed).

## 주의

- 이 코드는 추론 서버 코드다. 버그는 주행에 직결된다.
- v3가 정지·재출발 흔들림을 개선한다는 증거는 아직 없다. 7단계는 검증이지 확정이 아니다.
- 주행 로그 원본은 보존할 것.
