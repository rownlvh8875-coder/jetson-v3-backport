# Nav Driving Model ONNX 정적 호환성 조사

조사일: 2026-10-12. **LEVEL 3 — 추가 입력 경로 필요**.
지정 Nav 모델의 원본을 실제 확보했으며 SHA256·크기를 확인했다.
V3의 기존 7개 입력/4개 출력은 이름·정확한 shape·dtype가 모두 같지만,
Nav에는 지도/내비 입력 2개와 recurrent state 2쌍이 추가된다.
따라서 현재 Cinque V3 실행기를 변경 없이 사용할 수 없다.
기존 state 검증/commit/reset, 카메라 가공, driving output 해석은 재사용 후보지만
Nav 입력 공급·wire·물리 dtype·identity/capability의 별도 검토가 필요하다.

이번 작업은 분석과 이 문서 작성뿐이다. 제품 코드, V3 ONNX/spec/패치,
AGENTS/PROJECT_STATE/V3_JETSON_PLAN 및 고정 참고 사본을 변경하지 않았다.
Nav 지원 구현, 모델 추론, ORT 비교, TensorRT build/load, 장치 접속/설치/활성화는 수행하지 않았다.
PKL 파일은 다운로드·실행·역직렬화하지 않았다.

## 1. 작업 기준과 원본 확보

- 작업 저장소: `https://github.com/rownlvh8875-coder/jetson-v3-backport`
- 브랜치: `feature/cinque-v3-jetson`.
- 시작 로컬 및 실제 조회 원격 HEAD: `6e2472a5ecd1d99c6764e0acdf43099cd4c57827`.
  시작 미커밋 변경 없음. 제품 테스트 기준 SHA는 기존 `e1096e60664ff2fd92d364ff9c1af10ce01488d7`이며
  이번 정적 분석의 코드 기준은 위 시작 HEAD다. 과거 테스트를 이번 실행 결과로 재기록하지 않는다.
- 분석용 임시 스크립트/JSON/로그/소스: Git ignore 대상 `tmp/`.
  모델은 기존 `artifacts/*.onnx` ignore 규칙 적용. 개인 절대경로와 원본 로그는 게시하지 않는다.
- 기존 격리 Python 3.12.14 / ONNX 1.23.2 사용. 패키지 설치/환경 설정 변경 없음.
  다운로드 전 C 볼륨 여유 약 88 GB 확인.

| 구분 | 로컬 상대경로 | 전체 SHA256 | 크기(bytes) |
|---|---|---|---:|
| Cinque V3 | `artifacts/big_driving_supercombo_v3.onnx` | `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4` | 766354845 |
| Nav | `artifacts/nav_driving_770e316.onnx` | `6ea13501cd6682321ee303c2fe425667988fa43a8aa326d35845602e22e4460d` | 764686430 |

대상 [커밋](https://github.com/commaai/openpilot/commit/770e316f3b8a30d6f4f1b516bee16a8c4ba78f58)의
`openpilot/selfdrive/modeld/models/big_driving_supercombo.onnx`는 위 Nav oid/size의 LFS pointer다.
GitHub media 직접 요청은 HTTP 404로 실패했고 파일 본문을 받지 못했다.
이후 같은 커밋의 [.lfsconfig](https://github.com/commaai/openpilot/blob/770e316f3b8a30d6f4f1b516bee16a8c4ba78f58/.lfsconfig)를 읽어
공식 설정 LFS endpoint `https://huggingface.co/commaai/openpilot-lfs.git/info/lfs`를 확인했다.
`objects/batch`에 `operation=download`, 지정 oid/size 한 개만 요청하고 반환 download action으로 본문을 받았다.
TLS 검증을 유지했다. HTTP 200/Content-Length는 참고 정보로만 사용했다.
`.onnx.part`에 스트리밍 다운로드하며 전체 SHA256·바이트 수를 검사한 뒤에만 최종 `.onnx`로 이름을 바꿨다.
분석 시작 시 다시 디스크 파일 전체 해시를 계산했다. 기존 V3도 전체 해시·크기를 새로 계산했다.
두 원본 모두 분석 후 재검사하며, 모델/엔진은 Git에 추가하지 않는다.

## 2. 실제 입력 전체와 V3 비교

원본 semantic dtype 기준이다. `tools/onnx_meta_light.py`와 ONNX protobuf reader의 결과를 교차 확인했다.
`—`는 V3에 해당 tensor가 없다는 뜻이며 같다고 취급하지 않는다.
이름 비교는 입력 이름 집합에 대한 비교이고 shape와 dtype는 별도로 판단했다.

| input 이름 | V3 shape | V3 dtype | Nav shape | Nav dtype | 이름/shape/dtype 동일 |
|---|---|---|---|---|---|
| new_img | (2,6,128,256) | uint8 | (2,6,128,256) | uint8 | YES / YES / YES |
| desire | (8,) | float32 | (8,) | float32 | YES / YES / YES |
| traffic_convention | (1,2) | float32 | (1,2) | float32 | YES / YES / YES |
| action_t | (1,2) | float32 | (1,2) | float32 | YES / YES / YES |
| nav_map | — | — | (1,1,256,256) | uint8 | NO / N/A / N/A |
| navigation | — | — | (47,) | float32 | NO / N/A / N/A |
| state_img_q | (2,5,6,128,256) | uint8 | (2,5,6,128,256) | uint8 | YES / YES / YES |
| state_desire_q | (132,1,8) | float32 | (132,1,8) | float32 | YES / YES / YES |
| state_feat_q | (128,1,16384) | float32 | (128,1,16384) | float32 | YES / YES / YES |
| state_map_q | — | — | (32,1,256,256) | uint8 | NO / N/A / N/A |
| state_nav_q | — | — | (32,47) | float32 | NO / N/A / N/A |

입력 수: V3 **7**, Nav **11**. 전체 집합 차이는
`{nav_map, navigation, state_map_q, state_nav_q}`이며 제거된 V3 입력은 없다.
둘 다 `new_img`가 있고 `prev_feat` graph input은 없다.
카메라 tensor의 공간 크기는 둘 다 **128×256**, Nav 지도 tensor는 **256×256** 단일 채널이다.
이는 모델 tensor 해상도이며 실제 센서 해상도나 카메라 설치 조건을 뜻하지 않는다.
Nav의 외부 입력은 `nav_map` 65,536 bytes + `navigation` 188 bytes가 추가된다.
현재 wire에 없는 최소 semantic 데이터 65,724 bytes/step이며 새 패킷 포맷을 설계한 수치는 아니다.
`navigation` 47개 값의 의미·단위·정규화·유효성/미제공 표현은 확인되지 않았다. 임의 zero로 대체하지 않는다.

## 3. 실제 출력 전체와 V3 비교

| output 이름 | V3 shape | V3 dtype | Nav shape | Nav dtype | 이름/shape/dtype 동일 |
|---|---|---|---|---|---|
| outputs | (1,18452) | float32 | (1,18452) | float32 | YES / YES / YES |
| next_state_img_q | (2,5,6,128,256) | uint8 | (2,5,6,128,256) | uint8 | YES / YES / YES |
| next_state_desire_q | (132,1,8) | float32 | (132,1,8) | float32 | YES / YES / YES |
| next_state_feat_q | (128,1,16384) | float32 | (128,1,16384) | float32 | YES / YES / YES |
| next_state_map_q | — | — | (32,1,256,256) | uint8 | NO / N/A / N/A |
| next_state_nav_q | — | — | (32,47) | float32 | NO / N/A / N/A |

출력 수: V3 **4**, Nav **6**. driving `outputs` 원소 수는 둘 다 **18,452**.
state를 포함한 전체 graph output 원소 수는 V3 **4,082,740**, Nav **6,181,396**이다.
서로 다른 dtype 원소의 합계이며 byte 크기/GPU 메모리 총량으로 해석하지 않는다.

## 4. stateful 구조와 그래프

| input ↔ next output (동일 shape/dtype) | Nav 각 state의 원소 수 | V3와 관계 |
|---|---:|---|
| state_img_q ↔ next_state_img_q | 1,966,080 | 동일 |
| state_desire_q ↔ next_state_desire_q | 1,056 | 동일 |
| state_feat_q ↔ next_state_feat_q | 2,097,152 | 동일 |
| state_map_q ↔ next_state_map_q | 2,097,152 | 추가 |
| state_nav_q ↔ next_state_nav_q | 1,504 | 추가 |

V3 state 3쌍/4,064,288 elements → Nav state 5쌍/6,162,944 elements.
두 모델 모두 next-state를 다음 step input으로 되먹임하는 queue 형식이다.
Nav의 새 queue는 다음과 같이 그래프에서 확인했다.

```text
state_map_q[1:] + nav_map                       → Concat(axis=0) → next_state_map_q
state_nav_q[1:] + Unsqueeze(navigation, axis=0) → Concat(axis=0) → next_state_nav_q
state_feat_q[1:] + Unsqueeze(outputs[:,2066:18450], axis=0) → next_state_feat_q
```

`node_slice_10/11`의 start=1, axis=0, step=1과 `node_cat_9/10`의 axis=0을
작은 initializer의 실제 값과 함께 읽었다. map/nav read path는 과거 queue의 `::4`와
현재 값을 결합한다(`node_slice_6/7`, step initializer `[4]`).
frame_skip metadata는 ONNX에 별도 제공되지 않으므로 이 관찰을 새 실행 spec으로 임의 확정하지 않는다.
지도/내비의 현재 입력과 state 모두 `outputs`까지 연결된 그래프 경로가 있다. 미사용 placeholder로 취급할 수 없다.

IR version은 둘 다 **10**, opset은 둘 다 **ai.onnx 20 + org.tinygrad 1**, producer는 `pytorch`다.
V3는 837 nodes/610 initializers, Nav는 861 nodes/658 initializers다.
Nav에 `map_encoder` weight를 사용하는 Conv 경로가 존재한다. 모델 내부 연산까지 같은 것은 아니다.
Nav checkpoint metadata는 **`cf8f6120-49ee-48f8-b2d7-d663a4708271/56320`**이며 V3 checkpoint와 다르다.

## 5. 카메라 및 지도 dtype 가공 재사용

카메라 경로는 두 모델에서 아래 op 순서·attribute가 같았다. 중간 tensor/node 이름은 다르다.

```text
state_img_q → Slice(axis=1, start=1)
new_img → Unsqueeze(axis=1)
두 경로 → Concat(axis=1) → next_state_img_q
        → Gather(axis=0) → Slice → Reshape  [두 카메라 분기]
        → Concat(axis=1) → Cast(to=FLOAT16) → vision trunk
```

V3 trunk 직전은 `node__to_copy_4`, Nav는 `node__to_copy_5`다.
원본 `new_img/state_img_q/next_state_img_q`의 dtype는 모두 uint8이다.
`tools/patch_v3_uint8.py`가 재사용하는 실제 `jetlink/cinque_v3.py::patch_v3_uint8_inputs`를
로드한 각 모델의 **메모리 안에서만** 호출했다. 구조 guard를 통과하고 두 모델 모두 정확히
`{new_img: float16, state_img_q: float16, next_state_img_q: float16}`를 반환했다.
가공본을 저장하지 않았고 원본은 변경하지 않았다. 이것은 구조 guard 검사이며
가공 모델의 checker/ORT parity/TensorRT 실행 성공을 뜻하지 않는다.

**카메라 3개 tensor 가공의 분류: SAME WITH IDENTITY CHANGE.**
실제 production은 `validate_spec/validate_source`와 capability에서 고정 V3 identity/전체 명세만 허용하므로
Nav를 V3로 속여 통과시킬 수 없다. identity만 바꿔 전체 Nav 지원이 끝나는 것은 아니다.

Nav의 지도 경로는 별도다.

```text
state_map_q → Slice(::4) + nav_map → Concat → Unsqueeze → Transpose
  → GatherND → Transpose → Cast(FLOAT32) → Div(255.0)
  → Cast(FLOAT16) → Reshape(9,1,256,256) → map_encoder Conv
state_map_q[1:] + nav_map → next_state_map_q
```

실제 node: `node_Transpose_482`, `node_GatherND_489`, `node_index`,
`node__to_copy_6`, `node_div_1`, `node__to_copy_7`, `node_view_41`, `node_conv2d_41`.
기존 patch는 `nav_map/state_map_q/next_state_map_q`의 UINT8을 처리하지 않는다.
기존 카메라 guard의 허용 op 집합에는 `Transpose/GatherND`가 없고, Cast 경계도 FP16만 허용하므로
이를 지도에 그대로 확대하면 FP32 Cast를 포함하는 이 경로와 맞지 않는다.

**모델 전체의 TRT 가공 경로 분류: PATCH LOGIC NEEDS MODIFICATION.**
Nav 전용 원본/physical 계약과 추가 UINT8 지도 경로의 TRT 처리 방식을 별도로 정의·검증해야 한다.
실제 대상 TensorRT에서 지도 UINT8/GatherND 등을 받아들이는지, retype이 필요한지,
어떤 최소 가공이 원본 수치를 보존하는지는 이번 조사에서 확인하지 않았다.
메모리 구조 guard 통과를 완성된 Nav 변환기로 보고하지 않는다.

## 6. output layout / parser

둘 다 ONNX `metadata_props.output_slices`가 있다. 기존 도구의 제한된 pickle opcode 해석기로
dict[str,slice] 정보만 추출했다. `pickle.load/loads` 또는 PKL 역직렬화는 실행하지 않았다.
**아래 15개 slice가 모두 V3 JSON 및 V3 원본 metadata와 정확히 일치한다.**
구간은 `[start, stop)`이다.

| slice | V3와 Nav 공통 구간 |
|---|---|
| lane_lines | 0–528 |
| lane_lines_prob | 528–536 |
| road_edges | 536–800 |
| meta | 800–855 |
| desire_pred | 855–887 |
| pose | 887–899 |
| wide_from_device_euler | 899–905 |
| road_transform | 905–917 |
| plan | 917–1907 |
| lead | 1907–2051 |
| lead_prob | 2051–2054 |
| desire_state | 2054–2062 |
| action | 2062–2066 |
| hidden_state | 2066–18450 |
| pad | 18450–18452 |

같은 output 원소 수로 추측한 것이 아니라 모델에 내장된 layout을 비교한 결과다.
target [parse_model_outputs.py](https://github.com/commaai/openpilot/blob/770e316f3b8a30d6f4f1b516bee16a8c4ba78f58/openpilot/selfdrive/modeld/parse_model_outputs.py)와
고정 Carrot의 실제 적용 사본 parser를 텍스트/AST로 비교했다.
유일한 코드 차이는 `parse_mdn(..., out_shape=None)` → `out_shape=()` 기본 인수다.
관련 `parse_vision_outputs/parse_policy_outputs`의 호출은 모두 out_shape를 명시한다.
`constants.py`의 텍스트는 동일하다. 현재 Carrot `contracts.py::parse_outputs`의
plan 990/lead 144/action 4/hidden-state 16384 폭과도 일치한다.

**출력 layout 및 확인한 parser 호출 계약은 호환**이다.
이는 수치 범위/분포/제어 품질 검증이 아니며 parser 실행·메시지 발행·실차 동작은 시험하지 않았다.
기존 내부 모델 fallback/FAULT/commIssue 경로의 변경 근거로 사용하지 않는다.

## 7. map/nav 공급 경로와 현재 실행기 제한

대상 커밋의 실제 [mapsd.py](https://github.com/commaai/openpilot/blob/770e316f3b8a30d6f4f1b516bee16a8c4ba78f58/openpilot/selfdrive/navigation/mapsd.py)는
GPS/navRoute → route tracker/renderer → `VisionIpcServer('mapsd')` → `VISION_STREAM_MAP`를 생성한다.
renderer SIZE는 256이며 map image는 uint8 `(256,256)`다. usable map이 없으면 black frame과 timestamp=0을 보낸다.
생산자의 이 동작이 Nav ONNX에서 승인된 missing-map 표현이라는 근거는 아직 없다.

대상 [modeld.py](https://github.com/commaai/openpilot/blob/770e316f3b8a30d6f4f1b516bee16a8c4ba78f58/openpilot/selfdrive/modeld/modeld.py)의
`ModelState.run/main`은 카메라와 desire/traffic_convention/action_t를 공급한다.
읽은 파일에는 `VISION_STREAM_MAP` subscriber나 nav_map/navigation 채우기 경로가 없다.
`pack_inputs`가 비-state/non-new_img 입력 공간을 만들 수 있어도 올바른 지도/47-vector 공급을 입증하지 않는다.
PR #39066 최종 head의 modeld도 별도로 읽었으며 해당 연결은 발견하지 못했다.
navd 소스는 navInstruction을 발행하지만 읽은 코드에서 ONNX의 47-vector encoder는 확인되지 않았다.

현재 프로젝트의 제한은 다음 실제 함수에서 확인했다.

| 지점 | 현재 계약 | Nav에 필요한 별도 검토 |
|---|---|---|
| comma `contracts.py::validate_model_spec` | stateful의 비-state 입력은 new_img/desire/traffic_convention/action_t만 허용 | 추가 nav_map/navigation 및 5쌍 state 명세 |
| `ModelSpec.packed_shapes` | desire/traffic_convention/action_t만 wire packed에 포함 | 지도 bytes와 47-vector 전송 계약/길이/시각/유효성 |
| `StatefulState.step_into` | 카메라와 scalar 3개만 host buffer에 씀 | 외부 입력 2개 공급, GPU buffer 준비 |
| `StatefulState.validate_next_states/commit_next_states/reset` | spec pair loop, exact physical dtype, finite 및 commit 실패 무효화 | 5쌍 확장 후 warm/reset/실패 중간 commit 회귀 |
| `cinque_v3.validate_spec/source/record` 및 `v3_compat` | 정확한 V3 identity/semantic 명세만 허용 | Nav를 위한 독립 identity/가공 기록/선택 협상 |

필요한 연결은 `mapsd → VISION_STREAM_MAP → comma modeld → Jetson wire → TRT nav_map`과
별도로 명세를 확보해야 하는 `navigation(47)` 공급 경로다.
기존 state pair 기반 서버 구조는 재사용 후보지만 현재 준비·선택·wire·입력 handler를 그대로 사용할 수 없다.
일반 stateful+protocol2 차단을 지우거나 현재 V3 capability를 Nav에 재사용하는 방안은 제안하지 않는다.

## 8. 대상 커밋 / master / PR 상태

공개 GitHub REST API 조회 기준: **2026-10-12 01:26 UTC**.
처음 web HTML 캐시는 PR을 Open/6 commits로 표시했지만, 직접 API는 아래 최신 상태를 반환했다.
캐시 결과로 현재 상태를 확정하지 않았다.

- target: `770e316f3b8a30d6f4f1b516bee16a8c4ba78f58`, 제목 `nav driving model`,
  commit time `2026-10-11T22:39:44Z`.
- parent: **`db47ef5cc3ef135248e5621a7929bb6d83b22dd3`** (`prefetch all tiles`).
- [nav alpha #39066](https://github.com/commaai/openpilot/pull/39066):
  **merged / closed**, merge time `2026-10-12T00:49:50Z`,
  merge commit **`4c362ca3272c7418a068d43c402c84bd0544f35a`**.
- 같은 조회의 master HEAD도 `4c362ca3272c7418a068d43c402c84bd0544f35a`.
  API compare target...master는 `diverged` (ahead 1 / behind 4)를 반환했다.
  **target은 그 master의 조상/포함 커밋이 아니다.**
- PR head: `812e26abab44088d54487adb029774cbdb619352`.
  PR 7개 커밋 목록에는 target이 없고 parent db47ef5는 포함된다.
  target...PR head는 `diverged` (ahead 4 / behind 1), 공통 조상은 위 parent다.
  따라서 nav alpha 작업과 같은 parent에서 갈라진 별도 모델 커밋이라는 관계가 확인된다.
- target의 associated PR API 결과 `[]`, branches-where-head 결과 `[]`.
  조회 당시 GitHub에 등록된 연결 PR/이 커밋을 head로 하는 branch는 확인되지 않았다.
  비공개 ref/삭제된 branch 이름/향후 병합 여부는 추측하지 않는다.
- merge commit의 변경 파일 목록에는 target의 ONNX/PKL 변경이 없다.
  **nav alpha 코드 병합과 이 Nav ONNX의 master 채택은 별개**다.
  이 모델을 현재 master 공식 production 모델이라고 부르지 않는다.
  개발/시험용 별도 모델 커밋이라는 판단은 이 ancestry·파일 변경 근거에 따른 해석이며 release 보증이 아니다.

재조회 endpoint: `commits/<target>`, `commits/master`, `pulls/39066`, `pulls/39066/commits`,
`commits/<target>/pulls`, `commits/<target>/branches-where-head`, `compare/<target>...<snapshot SHA>`.
참고 carrot-jetson/carrot-wip을 fetch/pull/최신화하지 않았다.

## 9. 실제 검사 명령과 근거

`$Py`는 기존 개발 venv의 Python이다. 명령은 작업 저장소에서 실행했으며
분석 과정에서 시스템 Python·장치·네트워크 설정을 변경하지 않았다.

```powershell
git status --short --branch
git rev-parse HEAD
git remote get-url origin
git ls-remote origin refs/heads/feature/cinque-v3-jetson
git check-ignore artifacts/nav_driving_770e316.onnx artifacts/nav_driving_770e316.onnx.part tmp/nav_analysis.json
& $Py tmp/nav_fetch.py
& $Py tmp/nav_github.py
& $Py tmp/nav_sources.py
& $Py tmp/nav_analyze.py
& $Py tools/onnx_meta_light.py artifacts/nav_driving_770e316.onnx
& $Py tools/onnx_meta_light.py artifacts/big_driving_supercombo_v3.onnx artifacts/cinque_v3.json
& $Py tmp/nav_verify.py
```

tmp scripts는 이번 로컬 조사용이며 제품/지원 CLI가 아니다. 결과 재현 시 모델은 위 LFS endpoint의
단일 oid/size를 받고 전체 해시를 확인한 뒤 기존 metadata 명령을 사용한다.
opset/graph와 출력 slice는 다음처럼 추론 없이 재확인할 수 있다.

```python
import onnx
from tools.onnx_meta_light import parse_meta_light, decode_output_slices
p = 'artifacts/nav_driving_770e316.onnx'
meta = parse_meta_light(p)
print(meta['inputs'], meta['outputs'])
print(decode_output_slices(meta['props']['output_slices']))
m = onnx.load(p, load_external_data=False)
print([(x.domain, x.version) for x in m.opset_import])
print(len(m.graph.node), len(m.graph.initializer))
roots = {'new_img', 'state_img_q', 'nav_map', 'navigation', 'state_map_q', 'state_nav_q'}
for n in m.graph.node:
    if roots.intersection(n.input) or any(x.startswith('next_state_') for x in n.output):
        print(n.name, n.op_type, list(n.input), list(n.output))
```

| 실제 검사 | 결과 | 한계 |
|---|---|---|
| Git 상태/origin/remote 및 ignore | PASS | 장치 코드 점검 아님 |
| 첫 GitHub media download | FAIL / HTTP 404 | 실제 .lfsconfig endpoint로 원인을 확인해 경로 변경 |
| 공식 설정 LFS 단일 객체 download, 디스크 identity | PASS / exit 0 | 본문 전체 SHA256+size 일치 |
| V3 디스크 identity 및 JSON 전체 metadata 비교 | PASS / exit 0 | 실제 V3 원본, 추론 없음 |
| Nav metadata reader + ONNX protobuf I/O 교차 확인 | PASS / exit 0 | 실제 Nav 원본 정적 분석 |
| state pair shape/dtype, image op/attribute, slices 비교 | PASS / exit 0 | 차이를 정확히 추출했다는 결과, 전체 계약 동일 판정 아님 |
| 카메라 가공 함수 구조 guard / 메모리 retype | PASS / exit 0 | 저장/체커/parity/TRT는 수행하지 않음 |
| 분석 후 두 원본 전체 identity, 표와 metadata, 카메라 op/attribute/initializer 재대조 | PASS / exit 0 | 제품/spec/patch/기존 계획 변경 없음도 확인 |
| Nav 및 가공본 ORT 추론/수치 비교 | SKIP | 정적 조사 범위 밖 |
| Nav TensorRT/Jetson/USB/차량 | SKIP | 범위 밖, 호환성 미확인 |
| 기존 제품 regression suite | SKIP | 제품 변경 없음, 과거 PASS를 이번 실행으로 표시하지 않음 |

로컬 `tmp/nav_analysis.json` SHA256:
`24b17c243e6b3d85b8fbb3b4f6a80fb289dc0937b87a44257776bf62992bf39b`.
`tmp/nav_analysis.log` SHA256:
`6ee497990ba3475ac3319a4ee95efc6ab33936135a2230dd383650f200a5d4c2`.
개인 경로 없는 실측 요약은 이 문서의 전체 tensor/slice/graph 표에 보존한다.
실제 ONNX 정적 검사이며 mock/ORT/GPU/USB 시험 결과가 아니다.

## 10. 재사용 판정과 다음 권장 작업

**LEVEL 3 — 추가 입력 경로 필요**. 기존 V3 실행기는 기반으로 재사용할 수 있지만 그대로 실행할 수 없다.
LEVEL 1/2가 아닌 근거는 `nav_map/navigation` 외부 입력과 `state_map_q/state_nav_q` 2쌍 추가다.
LEVEL 4로 판단하지 않은 이유는 기존 카메라·scalar·3쌍 state·driving output layout이 같고,
추가 state도 동일한 next-state queue 방식이기 때문이다.

현재 V3 실장치 검증·개발 목표는 유지한다. Nav 지원을 실제 추진하는 별도 승인 전에는 제품 변경하지 않는다.
다음 Nav 조사에서 먼저 확보할 것은 **navigation 47-vector의 공식 의미/생성 코드와 지도 입력의 시각·유효성 계약**이다.
이를 확인한 후에만 추가 wire/input handler·5쌍 state·Nav identity/capability·지도 dtype 가공의 최소 변경을 설계할 수 있다.
그 이후 별도 승인 범위에서 원본↔가공본 수치 비교와 대상 TRT parse/build/load/infer를 검증해야 한다.
성능·허용오차·주행 품질은 이번 결과로 판정하지 않는다.
