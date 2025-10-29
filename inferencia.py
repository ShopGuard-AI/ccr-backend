import json
import os
import threading
import time
from pathlib import Path
from typing import List, Sequence, Set

import cv2
import numpy as np
from flask import Flask, Response
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator, colors

from capture import VideoCapture

app = Flask(__name__)

os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "rtsp_transport;tcp|stimeout;15000000|max_delay;5000000|reorder_queue_size;2",
)

model = YOLO("yolo11m.pt", verbose=False)
video_path = "rtsp://admin:Gcs@9282@192.168.1.254:554/Streaming/Channels/101"

CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720
RESTART_AFTER_STALL_SECONDS = 30
FPS_SMOOTHING_ALPHA = 0.15
PARKING_JSON_PATH = Path("parking_areas.json")
PARKING_RELOAD_INTERVAL = 5.0

cap = VideoCapture(video_path, width=CAPTURE_WIDTH, height=CAPTURE_HEIGHT).start()
last_success_time = time.time()

output_frame = None
frame_lock = threading.Lock()

MAX_DISPLAY_WIDTH = 1280
MAX_DISPLAY_HEIGHT = 720
fps_smooth = 0.0
prev_frame_time = None
parking_areas: List[np.ndarray] = []
parking_status: List[bool] = []
parking_last_loaded = 0.0
parking_file_mtime: float | None = None
target_class_ids: Set[int] = set()
target_class_ids: Set[int] = set()
VEHICLE_CLASSES = {
    "car",
    "truck",
    "bus",
    "motorbike",
    "motorcycle",
    "vehicle",
    "person",
    "bicycle",
    "van",
}


def resolve_class_ids(names_map, target_names) -> Set[int]:
    resolved: Set[int] = set()
    if isinstance(names_map, dict):
        iterable = names_map.items()
    else:
        iterable = enumerate(names_map)
    for idx, name in iterable:
        if str(name).lower() in target_names:
            resolved.add(int(idx))
    return resolved


def load_parking_areas_from_json(path: Path) -> List[np.ndarray]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[parking] Erro ao interpretar {path}: {exc}")
        return []

    polygons: List[np.ndarray] = []
    for item in data.get("areas", []):
        points = item.get("points")
        if not isinstance(points, list) or len(points) != 4:
            continue
        polygon = []
        valid = True
        for pt in points:
            if isinstance(pt, (list, tuple)) and len(pt) == 2:
                polygon.append((int(pt[0]), int(pt[1])))
            else:
                valid = False
                break
        if valid and len(polygon) == 4:
            polygons.append(np.array(polygon, dtype=np.int32))
    return polygons


def ensure_parking_areas_loaded(force: bool = False) -> None:
    global parking_areas, parking_status, parking_last_loaded, parking_file_mtime
    now = time.time()
    if not force and now - parking_last_loaded < PARKING_RELOAD_INTERVAL:
        return

    parking_last_loaded = now
    if not PARKING_JSON_PATH.exists():
        if parking_areas:
            print("[parking] Arquivo de vagas não encontrado, limpando lista.")
        parking_areas = []
        parking_status = []
        parking_file_mtime = None
        return

    mtime = PARKING_JSON_PATH.stat().st_mtime
    if not force and parking_file_mtime is not None and mtime == parking_file_mtime:
        return

    polygons = load_parking_areas_from_json(PARKING_JSON_PATH)
    if polygons:
        print(f"[parking] {len(polygons)} vagas carregadas de {PARKING_JSON_PATH}.")
    else:
        print(f"[parking] Nenhuma vaga válida encontrada em {PARKING_JSON_PATH}.")
    parking_areas = polygons
    parking_status = [False] * len(parking_areas)
    parking_file_mtime = mtime


def compute_parking_status(polygons: Sequence[np.ndarray], detections: Sequence[tuple[int, int]]) -> List[bool]:
    if not polygons:
        return []
    status = []
    for pts in polygons:
        occupied = False
        for cx, cy in detections:
            if cv2.pointPolygonTest(pts, (float(cx), float(cy)), False) >= 0:
                occupied = True
                break
        status.append(occupied)
    return status


def draw_parking_overlay(frame: np.ndarray, polygons: Sequence[np.ndarray], status: Sequence[bool]) -> None:
    if not polygons:
        return

    overlay = frame.copy()
    for idx, (pts, occupied) in enumerate(zip(polygons, status), start=1):
        color = (0, 0, 255) if occupied else (0, 255, 0)
        cv2.fillPoly(overlay, [pts], color)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, dst=frame)

    for idx, (pts, occupied) in enumerate(zip(polygons, status), start=1):
        color = (0, 0, 255) if occupied else (0, 255, 0)
        cv2.polylines(frame, [pts], True, color, 2, cv2.LINE_AA)
        center = tuple(np.mean(pts, axis=0).astype(int))
        label = f"#{idx} {'Ocupada' if occupied else 'Livre'}"
        cv2.putText(
            frame,
            label,
            center,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 0),
            3,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            label,
            center,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    total = len(polygons)
    occupied_count = sum(status)
    free_count = total - occupied_count
    summary = f"Vagas livres: {free_count}/{total}"
    (text_width, text_height), _ = cv2.getTextSize(summary, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
    summary_bg = (10, 10)
    summary_end = (summary_bg[0] + text_width + 20, summary_bg[1] + text_height + 20)
    cv2.rectangle(frame, summary_bg, summary_end, (0, 0, 0), -1)
    cv2.putText(
        frame,
        summary,
        (summary_bg[0] + 10, summary_bg[1] + text_height + 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )


target_class_ids = resolve_class_ids(model.names, VEHICLE_CLASSES)
if not target_class_ids:
    print("[parking] Nenhuma classe alvo encontrada no modelo. Todas as detecções serão ignoradas.")


def resize_to_fit(frame, max_width=MAX_DISPLAY_WIDTH, max_height=MAX_DISPLAY_HEIGHT):
    """Resize frame to fit on screen while preserving aspect ratio."""
    height, width = frame.shape[:2]
    if width == 0 or height == 0:
        return frame

    scale = min(max_width / width, max_height / height, 1.0)
    if scale < 1.0:
        new_size = (int(width * scale), int(height * scale))
        frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)
    return frame


def build_status_frame(message, base_shape=(480, 640, 3)):
    """Return a simple status frame with the provided message."""
    frame = np.zeros(base_shape, dtype=np.uint8)
    cv2.putText(
        frame,
        message,
        (20, base_shape[0] // 2 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )
    if parking_status:
        total = len(parking_status)
        occupied = sum(parking_status)
        summary = f"Ocupadas: {occupied}/{total} | Livres: {total - occupied}"
        cv2.putText(
            frame,
            summary,
            (20, base_shape[0] // 2 + 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (200, 200, 200),
            2,
            cv2.LINE_AA,
        )
    return resize_to_fit(frame)


def restart_capture(reason: str):
    """Attempt to restart the capture stream with a short backoff."""
    global cap, last_success_time, output_frame, fps_smooth, prev_frame_time

    backend = getattr(cap, "backend", None)

    status_frame = build_status_frame(f"Reiniciando captura: {reason}")
    with frame_lock:
        output_frame = status_frame.copy()

    cv2.imshow("YOLO11 Tracking", status_frame)
    cv2.waitKey(1)

    try:
        cap.stop()
    except Exception:
        pass

    time.sleep(2.0)
    new_cap = VideoCapture(
        video_path, width=CAPTURE_WIDTH, height=CAPTURE_HEIGHT, backend=backend
    ).start()
    cap = new_cap
    last_success_time = time.time()
    fps_smooth = 0.0
    prev_frame_time = None


def process_stream():
    global output_frame, last_success_time, fps_smooth, prev_frame_time

    ensure_parking_areas_loaded(force=True)

    while True:
        ensure_parking_areas_loaded()
        grabbed, frame, status = cap.read()
        read_time = time.time()
        if not grabbed or frame is None:
            status_message = {
                "initializing": "Inicializando stream...",
                "reconnecting": f"Reconectando stream... tentativa {cap.reconnect_attempts}",
                "failed": "Stream falhou. Verifique a fonte.",
                "stopped": "Stream encerrado.",
            }.get(status, f"Status do stream: {status}")

            status_frame = build_status_frame(status_message)
            with frame_lock:
                output_frame = status_frame.copy()

            cv2.imshow("YOLO11 Tracking", status_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            if status in {"failed", "stopped"}:
                restart_capture(f"status {status}")
                continue

            if read_time - last_success_time > RESTART_AFTER_STALL_SECONDS:
                restart_capture("sem frames recentes")
                continue

            time.sleep(0.1 if status == "reconnecting" else 0.05)
            continue

        last_success_time = read_time

        result = model.track(frame, persist=True, verbose=False)[0]
        annotated_frame = frame.copy()
        annotator = Annotator(annotated_frame, line_width=2)

        boxes_xyxy = (
            result.boxes.xyxy.cpu().numpy() if result.boxes is not None else np.empty((0, 4))
        )
        track_ids = (
            result.boxes.id.int().cpu().tolist()
            if result.boxes is not None and result.boxes.id is not None
            else [None] * len(boxes_xyxy)
        )
        classes = (
            result.boxes.cls.int().cpu().tolist()
            if result.boxes is not None and result.boxes.cls is not None
            else [None] * len(boxes_xyxy)
        )

        vehicle_centers = []
        for xyxy, track_id, cls in zip(boxes_xyxy, track_ids, classes):
            cls_idx = int(cls) if cls is not None else None
            if cls_idx is not None:
                if isinstance(model.names, dict):
                    class_name = model.names.get(cls_idx, "obj")
                else:
                    class_name = model.names[cls_idx] if cls_idx < len(model.names) else "obj"
            else:
                class_name = "obj"

            color_seed = track_id if track_id is not None else (cls_idx if cls_idx is not None else 0)
            label = f"{class_name} #{track_id}" if track_id is not None else class_name
            annotator.box_label(xyxy, label, color=colors(color_seed, True))

            if cls_idx is not None and (not target_class_ids or cls_idx in target_class_ids):
                cx = int((xyxy[0] + xyxy[2]) / 2)
                cy = int((xyxy[1] + xyxy[3]) / 2)
                vehicle_centers.append((cx, cy))

        annotated_frame = annotator.result()
        frame_time = time.time()
        last_success_time = frame_time

        if prev_frame_time is not None:
            delta = frame_time - prev_frame_time
            if delta > 0:
                fps_instant = 1.0 / delta
                fps_smooth = (
                    fps_instant
                    if fps_smooth == 0.0
                    else fps_smooth * (1 - FPS_SMOOTHING_ALPHA) + FPS_SMOOTHING_ALPHA * fps_instant
                )
        prev_frame_time = frame_time

        fps_label = fps_smooth if fps_smooth > 0 else 0.0
        if parking_areas:
            parking_status[:] = compute_parking_status(parking_areas, vehicle_centers)
            draw_parking_overlay(annotated_frame, parking_areas, parking_status)

        cv2.putText(
            annotated_frame,
            f"FPS: {fps_label:.1f}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        annotated_frame = resize_to_fit(annotated_frame)

        with frame_lock:
            output_frame = annotated_frame.copy()

        cv2.imshow("YOLO11 Tracking", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.stop()
    cv2.destroyAllWindows()


def generate_stream():
    while True:
        with frame_lock:
            frame = output_frame.copy() if output_frame is not None else None
        if frame is None:
            time.sleep(0.01)
            continue
        ret, buffer = cv2.imencode(".jpg", frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )


@app.route("/")
def index():
    return (
        "<html><body>"
        "<h1>YOLO11 Tracking Stream</h1>"
        "<img src='/video_feed' style='max-width: 100%;' />"
        "</body></html>"
    )


@app.route("/video_feed")
def video_feed():
    return Response(generate_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True, use_reloader=False)


if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    process_stream()
