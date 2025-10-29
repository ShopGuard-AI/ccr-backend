import json
import os
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging
from dotenv import load_dotenv

import cv2
import numpy as np
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator, colors

from capture import VideoCapture
from supabase_client import db

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuração CORS específica para produção
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://front-end-costa-silva-ccr-poc-tkkg.vercel.app",
            "https://*.vercel.app"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# Configurações
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "rtsp_transport;tcp|stimeout;15000000|max_delay;5000000|reorder_queue_size;2",
)

CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720
MAX_DISPLAY_WIDTH = 1280
MAX_DISPLAY_HEIGHT = 720
FPS_SMOOTHING_ALPHA = 0.15
FRAME_JPEG_PARAMS = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
PARKING_DETAILS_VERSION = 1
CAMERA_SYNC_INTERVAL = 60  # seconds

# URL base para streaming (Cloudflare Tunnel ou servidor público)
STREAM_BASE_URL = os.getenv('STREAM_BASE_URL', 'http://localhost:5000')

# Classes de veículos para detecção
VEHICLE_CLASSES = {
    "car", "truck", "bus", "motorbike", "motorcycle",
    "vehicle", "bicycle", "van"
}

# Modelo YOLO com otimizações de GPU
model = YOLO("yolo11s.pt", verbose=False)
model.to("cuda")

# Configurações de performance
model.fuse()  # Fuse layers para melhor performance

# Armazenamento de câmeras
cameras_config: Dict[str, Dict] = {}  # {camera_id: {name, location, url, areas, status}}
cameras_capture: Dict[str, VideoCapture] = {}  # {camera_id: VideoCapture}
cameras_frames: Dict[str, Optional[bytes]] = {}  # Último frame JPEG
cameras_locks: Dict[str, threading.Lock] = {}  # {camera_id: threading.Lock}
cameras_stats: Dict[str, Dict] = {}  # {camera_id: {occupied, free, total, fps, spots}}
cameras_last_save: Dict[str, float] = {}  # {camera_id: timestamp} - Para controle de persistência
last_camera_sync = 0.0
config_lock = threading.Lock()

CONFIG_FILE = Path("cameras_config.json")
OCCUPANCY_SAVE_INTERVAL = 60  # Salva ocupação a cada 60 segundos


def load_cameras_config():
    """Carrega configuração de câmeras do arquivo JSON"""
    global cameras_config
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            count = len(data)
            with config_lock:
                cameras_config = data
            logger.info(f"Loaded {count} cameras from config")
        except Exception as e:
            logger.error(f"Error loading cameras config: {e}")
            with config_lock:
                cameras_config = {}


def save_cameras_config():
    """Salva configuração de câmeras no arquivo JSON"""
    try:
        with config_lock:
            snapshot = json.dumps(cameras_config, indent=2, ensure_ascii=False)
            count = len(cameras_config)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(snapshot)
        logger.info(f"Saved {count} cameras to config")
    except Exception as e:
        logger.error(f"Error saving cameras config: {e}")


def sync_cameras_from_supabase(force: bool = False) -> None:
    """Sincroniza configuração de câmeras a partir do Supabase."""
    global cameras_config, last_camera_sync

    if not db.is_connected():
        if force:
            logger.warning("Supabase not connected; keeping local camera configuration.")
        return

    now = time.time()
    if not force and now - last_camera_sync < CAMERA_SYNC_INTERVAL:
        return

    try:
        supabase_cameras = db.get_all_cameras()
        new_config: Dict[str, Dict] = {}

        for camera in supabase_cameras:
            camera_id = camera.get('id')
            if not camera_id:
                continue

            areas_records = db.get_parking_areas(camera_id)
            sorted_records = sorted(
                areas_records,
                key=lambda item: item.get('area_index', 0)
            )
            areas = []
            for record in sorted_records:
                points = record.get('points')
                if isinstance(points, list) and len(points) == 4:
                    areas.append(points)

            new_config[camera_id] = {
                'name': camera.get('name', ''),
                'location': camera.get('location', ''),
                'url': camera.get('url', ''),
                'areas': areas,
                'status': camera.get('status', 'offline')
            }

        with config_lock:
            cameras_config = new_config
        last_camera_sync = now
        save_cameras_config()
        logger.info("Synced %d cameras from Supabase", len(new_config))
    except Exception as exc:
        logger.error("Failed to sync cameras from Supabase: %s", exc)


def resolve_class_ids(names_map, target_names):
    """Resolve IDs das classes de interesse"""
    resolved = set()
    if isinstance(names_map, dict):
        iterable = names_map.items()
    else:
        iterable = enumerate(names_map)
    for idx, name in iterable:
        if str(name).lower() in target_names:
            resolved.add(int(idx))
    return resolved


target_class_ids = resolve_class_ids(model.names, VEHICLE_CLASSES)


def compute_parking_status(polygons, detections):
    """Calcula status de ocupação das vagas"""
    if not polygons:
        return []
    status = []
    for pts in polygons:
        pts_array = np.array(pts, dtype=np.int32)
        occupied = False
        for cx, cy in detections:
            if cv2.pointPolygonTest(pts_array, (float(cx), float(cy)), False) >= 0:
                occupied = True
                break
        status.append(occupied)
    return status


def draw_parking_overlay(frame, polygons, status):
    """Desenha overlay das vagas no frame"""
    if not polygons:
        return

    overlay = frame.copy()
    for idx, (pts, occupied) in enumerate(zip(polygons, status), start=1):
        pts_array = np.array(pts, dtype=np.int32)
        color = (0, 0, 255) if occupied else (0, 255, 0)
        cv2.fillPoly(overlay, [pts_array], color)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, dst=frame)

    for idx, (pts, occupied) in enumerate(zip(polygons, status), start=1):
        pts_array = np.array(pts, dtype=np.int32)
        color = (0, 0, 255) if occupied else (0, 255, 0)
        cv2.polylines(frame, [pts_array], True, color, 2, cv2.LINE_AA)
        center = tuple(np.mean(pts_array, axis=0).astype(int))
        label = f"#{idx} {'Ocupada' if occupied else 'Livre'}"
        cv2.putText(frame, label, center, cv2.FONT_HERSHEY_SIMPLEX,
                   0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, label, center, cv2.FONT_HERSHEY_SIMPLEX,
                   0.6, (255, 255, 255), 2, cv2.LINE_AA)


def resize_to_fit(frame, max_width=MAX_DISPLAY_WIDTH, max_height=MAX_DISPLAY_HEIGHT):
    """Redimensiona frame mantendo aspect ratio"""
    height, width = frame.shape[:2]
    if width == 0 or height == 0:
        return frame
    scale = min(max_width / width, max_height / height, 1.0)
    if scale < 1.0:
        new_size = (int(width * scale), int(height * scale))
        frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)
    return frame


def process_camera_stream(camera_id):
    """Processa stream de uma câmera específica"""
    logger.info(f"Starting stream processing for camera {camera_id}")

    fps_smooth = 0.0
    prev_frame_time = None
    cameras_last_save[camera_id] = 0.0

    while camera_id in cameras_capture:
        sync_cameras_from_supabase()

        cap = cameras_capture.get(camera_id)
        if not cap:
            time.sleep(0.1)
            continue

        grabbed, frame, status = cap.read()
        if not grabbed or frame is None:
            time.sleep(0.1)
            continue

        # Garantir resolução consistente
        if frame.shape[1] != CAPTURE_WIDTH or frame.shape[0] != CAPTURE_HEIGHT:
            frame = cv2.resize(frame, (CAPTURE_WIDTH, CAPTURE_HEIGHT), interpolation=cv2.INTER_AREA)

        annotated_frame = frame.copy()
        annotator = None
        result = None

        # Inferência com YOLO (GPU otimizada)
        try:
            result = model.predict(
                annotated_frame,
                device='cuda',
                half=True,
                verbose=False,
                conf=0.25,
                iou=0.45,
                max_det=100,
                classes=list(target_class_ids) if target_class_ids else None,
            )[0]
            annotator = Annotator(annotated_frame, line_width=2)
        except Exception as exc:
            logger.error(f"YOLO error on camera {camera_id}: {exc}")
            result = None
            annotator = None
            annotated_frame = frame.copy()

        boxes_xyxy = (
            result.boxes.xyxy.cpu().numpy()
            if result is not None and result.boxes is not None
            else np.empty((0, 4))
        )
        classes = (
            result.boxes.cls.int().cpu().tolist()
            if result is not None and result.boxes is not None and result.boxes.cls is not None
            else []
        )

        vehicle_centers: List[tuple[int, int]] = []

        if annotator is not None and len(boxes_xyxy):
            for xyxy, cls in zip(boxes_xyxy, classes):
                cls_idx = int(cls) if cls is not None else None
                if cls_idx is None:
                    continue

                class_name = (
                    model.names.get(cls_idx, "obj")
                    if isinstance(model.names, dict)
                    else model.names[cls_idx]
                )

                if target_class_ids and cls_idx not in target_class_ids:
                    continue

                annotator.box_label(xyxy, class_name, color=colors(cls_idx, True))

                cx = int((xyxy[0] + xyxy[2]) / 2)
                cy = int((xyxy[1] + xyxy[3]) / 2)
                vehicle_centers.append((cx, cy))

            annotated_frame = annotator.result()

        # FPS suavizado
        frame_time = time.time()
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

        with config_lock:
            cam_config = cameras_config.get(camera_id, {})
            raw_areas = cam_config.get('areas', [])
        areas: List[List[List[int]]] = [
            [[int(pt[0]), int(pt[1])] for pt in polygon]
            for polygon in raw_areas
            if isinstance(polygon, list) and len(polygon) == 4
        ]
        occupied_count = 0
        parking_status: List[bool] = []
        spot_details: List[Dict] = []

        if areas:
            parking_status = compute_parking_status(areas, vehicle_centers)
            occupied_count = sum(parking_status)
            spot_details = [
                {
                    'index': idx,
                    'occupied': bool(occupied),
                    'points': area,
                }
                for idx, (area, occupied) in enumerate(zip(areas, parking_status))
            ]
            draw_parking_overlay(annotated_frame, areas, parking_status)

        previous_stats = cameras_stats.get(camera_id, {})
        previous_occupied = previous_stats.get('occupied')

        cameras_stats[camera_id] = {
            'occupied': occupied_count,
            'free': max(len(areas) - occupied_count, 0),
            'total': len(areas),
            'fps': fps_smooth,
            'spots': spot_details,
        }

        if (
            db.is_connected()
            and previous_occupied is not None
            and previous_occupied != occupied_count
        ):
            threading.Thread(
                target=db.log_event,
                kwargs={
                    'camera_id': camera_id,
                    'event_type': 'occupancy_change',
                    'description': f'{previous_occupied} -> {occupied_count}',
                    'metadata': {
                        'previous': previous_occupied,
                        'current': occupied_count,
                        'total': len(areas),
                    },
                },
                daemon=True,
            ).start()

        if areas and db.is_connected():
            current_time = time.time()
            if current_time - cameras_last_save.get(camera_id, 0.0) >= OCCUPANCY_SAVE_INTERVAL:
                cameras_last_save[camera_id] = current_time
                free_count = len(areas) - occupied_count
                occupancy_pct = (occupied_count / len(areas) * 100) if len(areas) else 0
                details_payload = {
                    'version': PARKING_DETAILS_VERSION,
                    'spots': spot_details,
                }
                threading.Thread(
                    target=db.save_occupancy,
                    kwargs={
                        'camera_id': camera_id,
                        'total_spots': len(areas),
                        'occupied_spots': occupied_count,
                        'free_spots': free_count,
                        'occupancy_percentage': occupancy_pct,
                        'fps': fps_smooth,
                        'details': details_payload,
                    },
                    daemon=True,
                ).start()

        # Overlay de FPS
        cv2.putText(
            annotated_frame,
            f"FPS: {fps_smooth:.1f}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        annotated_frame = resize_to_fit(annotated_frame)
        success, buffer = cv2.imencode('.jpg', annotated_frame, FRAME_JPEG_PARAMS)
        frame_bytes = buffer.tobytes() if success else None

        if not success:
            logger.warning("Failed to encode frame for camera %s", camera_id)

        lock = cameras_locks.get(camera_id)
        if lock:
            with lock:
                cameras_frames[camera_id] = frame_bytes

    logger.info(f"Stopped stream processing for camera {camera_id}")


# ========== API ENDPOINTS ==========

@app.route('/api/cameras', methods=['GET'])
def get_cameras():
    """Lista todas as câmeras configuradas"""
    sync_cameras_from_supabase()
    cameras_list = []

    # Buscar dados do Supabase para incluir stream_url
    supabase_cameras = db.get_all_cameras() if db.is_connected() else []
    supabase_dict = {cam['id']: cam for cam in supabase_cameras}

    with config_lock:
        config_items = list(cameras_config.items())
    for cam_id, config in config_items:
        # Buscar stream_url do Supabase se disponível
        supabase_data = supabase_dict.get(cam_id, {})
        stream_url = supabase_data.get('stream_url', '')

        cameras_list.append({
            'id': cam_id,
            'name': config.get('name', ''),
            'location': config.get('location', ''),
            'url': config.get('url', ''),
            'status': config.get('status', 'offline'),
            'stream_url': stream_url,
            'areas_count': len(config.get('areas', [])),
            'stats': cameras_stats.get(cam_id, {})
        })
    return jsonify(cameras_list)


@app.route('/api/cameras', methods=['POST'])
def add_camera():
    """Adiciona uma nova câmera"""
    data = request.json
    camera_id = data.get('id') or str(int(time.time() * 1000))

    name = data.get('name', '')
    location = data.get('location', '')
    url = data.get('url', '')

    with config_lock:
        cameras_config[camera_id] = {
            'name': name,
            'location': location,
            'url': url,
            'areas': [],
            'status': 'offline'
        }

    save_cameras_config()

    # Salva no Supabase
    db.save_camera(camera_id, name, location, url, status='offline', areas_count=0)
    db.log_event(camera_id, 'camera_created', f'Camera {name} was created')
    sync_cameras_from_supabase(force=True)

    return jsonify({'id': camera_id, 'message': 'Camera added successfully'})


@app.route('/api/cameras/<camera_id>', methods=['DELETE'])
def delete_camera(camera_id):
    """Remove uma câmera"""
    with config_lock:
        camera_data = cameras_config.get(camera_id)

    if not camera_data:
        return jsonify({'error': 'Camera not found'}), 404

    # Para captura se existir
    capture = cameras_capture.pop(camera_id, None)
    if capture:
        capture.stop()
    cameras_locks.pop(camera_id, None)
    cameras_frames.pop(camera_id, None)

    camera_name = camera_data.get('name', '')

    # Loga evento ANTES de deletar (senão não existe mais a FK)
    db.log_event(camera_id, 'camera_deleted', f'Camera {camera_name} was deleted')

    # Deleta do Supabase (cascata remove áreas, histórico, etc)
    db.delete_camera(camera_id)

    # Remove do config local e stats
    with config_lock:
        cameras_config.pop(camera_id, None)
    cameras_stats.pop(camera_id, None)
    cameras_last_save.pop(camera_id, None)
    save_cameras_config()
    sync_cameras_from_supabase(force=True)

    return jsonify({'message': 'Camera deleted successfully'})


@app.route('/api/cameras/<camera_id>/snapshot', methods=['GET'])
def get_snapshot(camera_id):
    """Captura um frame da câmera para desenhar áreas"""
    with config_lock:
        cam_config = cameras_config.get(camera_id)
    if not cam_config:
        return jsonify({'error': 'Camera not found'}), 404

    video_url = cam_config.get('url', '')

    try:
        # Usa MESMA configuração que VideoCapture para consistência
        cap = cv2.VideoCapture(video_url)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return jsonify({'error': 'Failed to capture frame'}), 500

        # Garante que está no tamanho correto
        if frame.shape[1] != CAPTURE_WIDTH or frame.shape[0] != CAPTURE_HEIGHT:
            frame = cv2.resize(frame, (CAPTURE_WIDTH, CAPTURE_HEIGHT), interpolation=cv2.INTER_AREA)

        # Codifica como JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            return jsonify({'error': 'Failed to encode frame'}), 500

        return Response(buffer.tobytes(), mimetype='image/jpeg')
    except Exception as e:
        logger.error(f"Error capturing snapshot: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cameras/<camera_id>/areas', methods=['POST'])
def save_camera_areas(camera_id):
    """Salva as áreas desenhadas para uma câmera"""
    data = request.json
    areas = data.get('areas', [])

    with config_lock:
        if camera_id not in cameras_config:
            return jsonify({'error': 'Camera not found'}), 404
        cameras_config[camera_id]['areas'] = areas
        current_fps = cameras_stats.get(camera_id, {}).get('fps', 0.0)

    cameras_stats[camera_id] = {
        'occupied': 0,
        'free': len(areas),
        'total': len(areas),
        'fps': current_fps,
        'spots': [
            {'index': idx, 'occupied': False, 'points': area}
            for idx, area in enumerate(areas)
        ],
    }
    save_cameras_config()

    # Salva áreas no Supabase
    areas_formatted = [{'points': area} for area in areas]
    db.save_parking_areas(camera_id, areas_formatted)
    db.log_event(camera_id, 'areas_configured', f'{len(areas)} parking areas configured')
    sync_cameras_from_supabase(force=True)

    return jsonify({'message': 'Areas saved successfully', 'count': len(areas)})


@app.route('/api/cameras/<camera_id>/start', methods=['POST'])
def start_camera(camera_id):
    """Inicia o processamento de uma câmera"""
    with config_lock:
        cam_config = cameras_config.get(camera_id)

    if cam_config is None:
        return jsonify({'error': 'Camera not found'}), 404

    if camera_id in cameras_capture:
        return jsonify({'message': 'Camera already running'})

    video_url = cam_config.get('url', '')

    try:
        # Inicia captura
        cap = VideoCapture(video_url, width=CAPTURE_WIDTH, height=CAPTURE_HEIGHT).start()
        cameras_capture[camera_id] = cap
        cameras_locks[camera_id] = threading.Lock()
        cameras_frames[camera_id] = None
        with config_lock:
            cameras_config[camera_id]['status'] = 'online'

        # Inicia thread de processamento
        thread = threading.Thread(target=process_camera_stream, args=(camera_id,), daemon=True)
        thread.start()

        save_cameras_config()

        # Atualiza status e stream_url no Supabase
        db.update_camera_status(camera_id, 'online')
        stream_url = f"{STREAM_BASE_URL}/api/cameras/{camera_id}/stream"
        db.update_camera_stream_url(camera_id, stream_url)
        db.log_event(camera_id, 'camera_online', f'Camera started processing')
        sync_cameras_from_supabase(force=True)

        return jsonify({'message': 'Camera started successfully', 'stream_url': stream_url})
    except Exception as e:
        logger.error(f"Error starting camera: {e}")
        # Loga erro no Supabase
        db.log_event(camera_id, 'camera_error', f'Failed to start: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/cameras/<camera_id>/stop', methods=['POST'])
def stop_camera(camera_id):
    """Para o processamento de uma câmera"""
    capture = cameras_capture.pop(camera_id, None)
    if not capture:
        return jsonify({'message': 'Camera not running'})

    capture.stop()
    cameras_locks.pop(camera_id, None)
    cameras_frames.pop(camera_id, None)
    cameras_last_save.pop(camera_id, None)
    with config_lock:
        if camera_id in cameras_config:
            cameras_config[camera_id]['status'] = 'offline'
    save_cameras_config()

    # Atualiza status no Supabase
    db.update_camera_status(camera_id, 'offline')
    db.log_event(camera_id, 'camera_offline', f'Camera stopped processing')
    sync_cameras_from_supabase(force=True)

    return jsonify({'message': 'Camera stopped successfully'})


@app.route('/api/cameras/<camera_id>/stream')
def camera_stream(camera_id):
    """Stream de vídeo processado da câmera"""
    def generate():
        while camera_id in cameras_frames:
            lock = cameras_locks.get(camera_id)
            if lock:
                with lock:
                    frame_data = cameras_frames.get(camera_id)
            else:
                frame_data = cameras_frames.get(camera_id)

            if frame_data is None:
                time.sleep(0.01)
                continue

            if isinstance(frame_data, bytes):
                frame_bytes = frame_data
            else:
                ret, buffer = cv2.imencode('.jpg', frame_data)
                if not ret:
                    continue
                frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/cameras/<camera_id>/status', methods=['GET'])
def get_camera_status(camera_id):
    """Retorna status atual das vagas de uma câmera"""
    sync_cameras_from_supabase()
    if camera_id not in cameras_config:
        return jsonify({'error': 'Camera not found'}), 404

    stats = cameras_stats.get(camera_id, {
        'occupied': 0,
        'free': 0,
        'total': 0,
        'fps': 0.0,
        'spots': []
    })

    return jsonify(stats)


@app.route('/api/cameras/<camera_id>/history', methods=['GET'])
def get_camera_history(camera_id):
    """Retorna histórico de ocupação de uma câmera"""
    hours = request.args.get('hours', default=24, type=int)
    history = db.get_occupancy_history(camera_id, hours)
    return jsonify(history)


@app.route('/api/cameras/<camera_id>/events', methods=['GET'])
def get_camera_events(camera_id):
    """Retorna eventos de uma câmera"""
    limit = request.args.get('limit', default=50, type=int)
    events = db.get_recent_events(camera_id, limit)
    return jsonify(events)


@app.route('/api/cameras/<camera_id>/statistics', methods=['GET'])
def get_camera_statistics(camera_id):
    """Retorna estatísticas diárias de uma câmera"""
    days = request.args.get('days', default=7, type=int)
    stats = db.get_daily_statistics(camera_id, days)
    return jsonify(stats)


@app.route('/api/realtime-stats', methods=['GET'])
def get_realtime_stats():
    """Retorna estatísticas em tempo real de todas as câmeras"""
    stats = db.get_realtime_stats()
    return jsonify(stats)


@app.route('/')
def index():
    return jsonify({
        'message': 'Parking Monitoring API',
        'cameras': len(cameras_config),
        'active': len(cameras_capture),
        'supabase_connected': db.is_connected()
    })


def auto_start_online_cameras():
    """Inicia automaticamente câmeras marcadas como online"""
    sync_cameras_from_supabase(force=True)
    with config_lock:
        config_items = [
            (camera_id, config.copy())
            for camera_id, config in cameras_config.items()
        ]
    for camera_id, config in config_items:
        if config.get('status') == 'online' and len(config.get('areas', [])) > 0:
            try:
                logger.info(f"Auto-starting camera {camera_id} ({config.get('name')})")
                video_url = config.get('url', '')

                # Inicia captura
                cap = VideoCapture(video_url, width=CAPTURE_WIDTH, height=CAPTURE_HEIGHT).start()
                cameras_capture[camera_id] = cap
                cameras_locks[camera_id] = threading.Lock()
                cameras_frames[camera_id] = None

                # Inicia thread de processamento
                thread = threading.Thread(target=process_camera_stream, args=(camera_id,), daemon=True)
                thread.start()

                # Atualiza stream_url no Supabase
                stream_url = f"{STREAM_BASE_URL}/api/cameras/{camera_id}/stream"
                db.update_camera_stream_url(camera_id, stream_url)
                db.log_event(camera_id, 'camera_online', f'Camera auto-started on server boot')

                logger.info(f"Camera {camera_id} started successfully with stream URL: {stream_url}")
            except Exception as e:
                logger.error(f"Failed to auto-start camera {camera_id}: {e}")
                cameras_config[camera_id]['status'] = 'offline'
                db.update_camera_status(camera_id, 'offline')
                db.log_event(camera_id, 'camera_error', f'Failed to auto-start: {str(e)}')


if __name__ == "__main__":
    load_cameras_config()
    sync_cameras_from_supabase(force=True)
    logger.info(f"Starting API server with {len(cameras_config)} cameras")

    # Inicia câmeras online em background
    startup_thread = threading.Thread(target=auto_start_online_cameras, daemon=True)
    startup_thread.start()

    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
