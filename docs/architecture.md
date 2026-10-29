# 구성 및 통신

## 데이터 흐름

```text
OAK-D → Docker YOLO → UDP 127.0.0.1:5005 → ROS /yolo/detections
STL-27L → ROS /scan ────────────────────→ full_run_controller
STM32 STATUS → UART ───────────────────→ full_run_controller
full_run_controller → 좌우 RPM 명령 → STM32 → 모터
```

`jetson/amr_core/full_run.py`가 두 회피 모드와 상태 전이를 담당합니다. `reactive_avoidance.py`에는 객체 추적, 바운딩 박스와 LiDAR 클러스터 대응, 곡선 생성·추종, 바퀴 RPM 기반 위치 추정이 있습니다. `scripts/full_run_controller.py`는 이 로직을 ROS·UART·측면센서에 연결합니다.

카메라 브리지는 기존 동작을 보존하기 위해 `/vision/person_obstacle`도 발행합니다. 회피 제어기는 전체 검출 객체를 전달하는 `/yolo/detections`를 사용합니다. 필요한 사용자 정의 메시지는 `amr_interfaces/msg/ObstacleInfo.msg` 하나만 포함했습니다.

## 하드웨어 기본값

| 항목 | 기본값 |
| --- | --- |
| MCU 명령 UART | `/dev/ttyTHS1`, 115200 baud |
| MCU 상태 UART | `/dev/ttyTHS2`; 명령 UART RX도 검사 |
| LiDAR | CP2102의 `/dev/serial/by-id/...` 경로, 921600 baud |
| 측면 초음파 | STM32에서 측정한 좌우 cm 값 |
| 카메라 모델 | YOLO11n, 기본 추론 장치 `cpu`, 입력 크기 320 |

UART 이름은 물리 커넥터 번호를 보장하지 않습니다. 실제 STATUS가 도착하는 포트는 시작 로그의 `uart_status_source`로 확인합니다. 선택한 수신 포트는 실행 중 바꾸지 않습니다. 장치 경로와 LiDAR 작업공간은 `config/full_run.env`로 재설정할 수 있습니다.

## STM32 ASCII 인터페이스

Jetson에서 보내는 명령:

```text
$CMD,LEFT_RPM,RIGHT_RPM,EMERGENCY\r\n
```

현재 로봇의 수신 상태 메시지:

```text
$STATUS,BASE_RPM,LEFT_RPM,RIGHT_RPM,LEFT_US_CM,RIGHT_US_CM,SHARP_CM\r\n
```

`BASE_RPM` 변화로 버튼 방향을 추정하고, Jetson의 선택 속도를 한 번에 5 RPM씩 조절합니다. 첫 상태값은 출발 명령으로 사용하지 않습니다. 좌우 실제 RPM은 위치 추정에 사용하며, 초음파 cm는 m로 변환합니다. 초음파 `-1`은 `NO_ECHO`로 기록하고 0m로 해석하지 않습니다. 이 펌웨어는 상태 메시지에 측정 시각이나 독립된 버튼 카운터를 포함하지 않으므로 그 한계는 남습니다.

기존 11필드 STATUS 형식도 파서에 남겼습니다. 다만 이 형식에는 측면 초음파 값이 없으므로 `SIDE_SENSOR_SOURCE=gpio`를 사용하려면 초음파가 실제 Jetson GPIO에 연결된 하드웨어여야 합니다. 기본 구성은 7필드 STATUS와 `SIDE_SENSOR_SOURCE=mcu`입니다.

## 정지와 상태

- `STARTUP`: 센서·통신·안전거리 확인, 0 RPM 유지.
- `READY`: 새 UP 입력 대기.
- `RUNNING`: 직진 또는 선택한 모드의 우회·통과·복귀 수행.
- `PAUSED`: 현재 경로를 유지하며 재출발 조건과 새 UP 입력 대기.
- `FAULT_STOP`: 고장으로 정지; 원인 해결 후 프로세스 재시작.

차체 내부·경계의 LiDAR 자기반사는 설정된 범위에서 제거하며 외부 점은 안전거리 검사에 사용합니다. 주행 제어기의 센서 지연, 통신, 바퀴 진행량 검사와 원본의 정지 정책은 유지했습니다. 실행 스크립트의 잠금으로 중복 실행을 막고, 종료 시 모터 정지 명령과 하위 프로세스 정리를 수행합니다.
