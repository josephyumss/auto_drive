# Auto Drive

YOLO 객체 인식과 LiDAR 거리 정보를 결합하여 차동구동 로봇의 장애물 회피와 원래 진행선 복귀를 제어하는 제출용 저장소입니다. 실물 로봇에서 사용한 `fixed` / `dynamic` 두 모드의 실행 코드를 원본 프로젝트에서 분리했습니다.

YOLO 바운딩 박스를 LiDAR 관측 각도와 대응시켜 장애물의 전방 거리와 횡방향 범위를 추정합니다. 바퀴의 실제 RPM으로 이동 위치를 추정하며 곡선 경로를 추종하고, 측면 초음파센서로 장애물 통과를 확인합니다. 목적지 기반 내비게이션이나 SLAM은 이 저장소의 범위에 포함되지 않습니다.

## 두 가지 회피 모드

| 모드 | 회피 계획 | 통과 후 복귀 |
| --- | --- | --- |
| `fixed` (기본값) | 설정값과 속도에 따른 감지거리로 장애물을 선정하고 곡선 경로 생성 | 측면 기준거리·장애물 감지·후단 확인 후 후방 여유거리까지 진행 |
| `dynamic` | 장애물 폭, 우회 폭, 현재 속도, 감속거리, 반응시간을 반영해 회피 시점과 곡선 진입거리 계산 | 진입 후 최소 차체 길이만큼 진행하고, 장애물 쪽 초음파센서가 연속으로 빈 공간을 확인하면 복귀 |

여기서 `fixed`도 곡선 경로를 추종합니다. 개발 초기의 일정 시간 회전 방식과는 다릅니다. 두 모드 모두 정지 후 새 UP 입력으로 출발하며, 동일한 주행 제어기와 안전거리 검사를 사용합니다.

## 실행 환경

- NVIDIA Jetson Orin Nano/Super, JetPack 6 / Ubuntu 22.04 ARM64
- ROS 2 Humble, Docker 및 NVIDIA 컨테이너 런타임
- OAK-D 카메라, LDROBOT STL-27L LiDAR
- 기존 ASCII 펌웨어가 탑재된 STM32와 좌우 모터·RPM 피드백
- STM32에 연결된 좌우 초음파센서

이 저장소는 Jetson 쪽 실행 코드입니다. STM32의 기존 펌웨어가 이미 구동 중이어야 하며, 펌웨어 빌드·업로드는 수행하지 않습니다. 기본 하드웨어 연결은 [구성 및 통신](docs/architecture.md)을 참고하세요.

## 설치

```bash
git clone https://github.com/josephyumss/auto_drive.git
cd auto_drive
sudo bash scripts/setup_full_run.sh
```

설치 스크립트는 ROS 브리지와 LiDAR 드라이버를 빌드하고 YOLO11n 모델·카메라 컨테이너를 준비합니다. 이미 준비된 의존성은 재사용합니다. JetPack과 Docker/NVIDIA 런타임은 먼저 설치되어 있어야 합니다. 모델과 외부 드라이버는 설치 시 내려받으며 저장소에는 포함하지 않습니다.

필요한 경우 `config/full_run.env.example`을 `config/full_run.env`로 복사하여 UART, LiDAR 장치 및 작업공간 경로를 설정하세요. 기존 로봇의 다른 주행 프로그램은 먼저 종료해야 합니다.

## 점검 및 실행

```bash
# 설치·설정 확인: 센서 프로세스와 모터 제어기를 시작하지 않음
sudo bash scripts/start_full_run.sh --avoidance-mode dynamic --check

# 실제 센서·통신·안전거리 점검: 항상 0 RPM만 전송하고 종료
sudo bash scripts/start_full_run.sh --avoidance-mode dynamic --preflight-only

# 동적 회피 모드
sudo bash scripts/start_full_run.sh --avoidance-mode dynamic

# 기존 회피 모드: 동적 모드 종료 후 별도로 실행
sudo bash scripts/start_full_run.sh --avoidance-mode fixed
```

터미널의 `[READY]` 표시 후 물리 UP 버튼을 새로 눌러 출발합니다. 두 모드는 동시에 실행하지 않습니다. 종료는 실행 터미널에서 `Ctrl+C`를 누르고 정리 완료를 기다리세요.

```bash
# 다른 터미널에서 전체 종료 요청
sudo bash scripts/start_full_run.sh --stop

# 프로세스를 유지한 채 즉시 정지 요청
sudo bash scripts/start_full_run.sh --instant-stop

# 최근 실행 로그 확인
sudo tail -F logs/full_run/latest/controller.log
```

`--instant-stop` 이후에는 정지 확인과 새 UP 입력이 필요합니다. 이는 소프트웨어 정지 기능이며 물리 비상정지 회로를 대체하지 않습니다.

## 설정

`config/full_run.json`에서 차체 치수, LiDAR 장착 위치, 주행 RPM, 안전거리와 동적 회피 파라미터를 설정합니다. 이 파일은 설명용 `//` 주석을 지원합니다. 실제 로봇의 치수·배선·센서 방향에 맞게 확인한 뒤 사용하세요.

주요 항목은 `robot_width_m`, `robot_length_m`, `wheel_base_m`, `lidar_*`, `maximum_rpm`, `dynamic_entry_heading_deg`, `dynamic_reaction_time_s`, `dynamic_max_trigger_distance_m`입니다. 기존 시험 설정은 그대로 보존했습니다.

## 폴더 구성

```text
config/                 주행 파라미터와 하드웨어 환경변수 예제
jetson/amr_core/        두 모드의 제어·센서 융합·통신·진단
scripts/                설치·실행·종료·진단 도구
docker/                 OAK-D YOLO 추론 컨테이너
jetson_ws/src/          필요한 ROS 브리지와 메시지 패키지
tests/                  하드웨어 없이 실행하는 회귀 테스트
docs/                   구성·통신·원본 출처
```

운영 중 생성되는 `logs/`, 모델, 빌드 결과물, 개인 환경설정은 Git에서 제외합니다. 과거 실험 코드·모니터링 UI·성과보고서·대용량 진단 압축파일은 포함하지 않았습니다.

## 검증

Python 3.10 이상에서 외부 Python 패키지 없이 핵심 테스트를 실행할 수 있습니다.

```bash
python -m unittest discover -s tests -v
```

가상 센서·UART·ROS와 이상적인 바퀴 피드백으로 두 모드의 판단, 정지, 우회·복귀 및 설치/종료 처리를 검사합니다. Linux 프로세스 관리 테스트는 Windows에서 건너뜁니다. 실제 로봇의 주행 정확도·제동거리 검증은 별도로 필요합니다.

## 라이선스

라이선스는 저장소의 [MIT License](LICENSE)를 따릅니다. 설치 시 내려받는 외부 소프트웨어와 모델의 라이선스는 각 배포처를 따릅니다.
