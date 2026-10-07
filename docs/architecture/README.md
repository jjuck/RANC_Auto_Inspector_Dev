# 아키텍처 스냅샷

`ef5b508d349d9be25b13e97ddcec02d60103d684`의 실제 진입점과 I/O를 근거로 만든 시스템 개요입니다. `candidate.json`의 각 구성 요소에서 고정된 소스 경로와 줄 범위를 확인할 수 있습니다.

`index.html`을 브라우저로 열거나 README 이미지에서 호스팅된 뷰어로 이동하세요. `preview.png`는 light 1440×900 캡처입니다. 고정 Viewer UI는 영어이며 설명은 한국어입니다.

소스 변경 시 진입점, 처리 조건, 실제 읽기·쓰기와 호출 소유자를 다시 추적한 뒤 candidate를 갱신하고 Archify `finalize architecture`를 `--repo-root`와 `--quality showcase`로 실행하세요. 검증 증거와 캡처 원본은 저장소 밖에 보관하세요. 휴대용 candidate의 `meta.output`은 이 저장소 기준 경로입니다.

기존 그림의 `ResultWriter → WebSocket` 연결은 수정했습니다. 저장은 ResultWriter, 전송 예약은 AutoInspectorDaemon, 실제 전송은 WebSocketManager가 맡습니다. 저장 실패 자체는 전송을 막지 않습니다. `request_history`는 아직 미구현이며 브라우저 이력은 메모리의 최대 20건입니다.

`provenance.json`은 생성 원본과 게시용 파일의 해시를 기록합니다. 게시용 HTML에서는 공백만 있는 줄의 공백만 정리했습니다. Archify 3.0.1을 사용했으며 해당 실행의 업데이트 알림은 없습니다.