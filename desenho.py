import argparse
import json
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

Point = Tuple[int, int]
Polygon = List[Point]


class ParkingAreaAnnotator:
    def __init__(self, image: np.ndarray, existing: List[Polygon] = None):
        self.original = image
        self.canvas = image.copy()
        self.window = "Parking Area Annotator"
        self.polygons: List[Polygon] = existing[:] if existing else []
        self.current_points: Polygon = []
        self.status_message = "Clique esquerdo para adicionar pontos. ENTER finaliza vaga."

    def reset_canvas(self) -> None:
        self.canvas = self.original.copy()

        for idx, polygon in enumerate(self.polygons, start=1):
            pts = np.array(polygon, dtype=np.int32)
            color = (0, 200, 0)
            cv2.polylines(self.canvas, [pts], True, color, 2, cv2.LINE_AA)
            label_pos = tuple(pts.mean(axis=0).astype(int))
            cv2.putText(
                self.canvas,
                f"#{idx}",
                label_pos,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        for idx, point in enumerate(self.current_points, start=1):
            cv2.circle(self.canvas, point, 5, (0, 120, 255), -1, cv2.LINE_AA)
            cv2.putText(
                self.canvas,
                str(idx),
                (point[0] + 8, point[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 120, 255),
                1,
                cv2.LINE_AA,
            )

        if len(self.current_points) > 1:
            cv2.polylines(
                self.canvas,
                [np.array(self.current_points, dtype=np.int32)],
                False,
                (0, 120, 255),
                2,
                cv2.LINE_AA,
            )

        self.draw_status()

    def draw_status(self) -> None:
        overlay = self.canvas.copy()
        cv2.rectangle(overlay, (0, 0), (self.canvas.shape[1], 60), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.55, self.canvas, 0.45, 0, dst=self.canvas)
        cv2.putText(
            self.canvas,
            self.status_message,
            (20, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            self.canvas,
            "ENTER: salvar vaga | U: desfaz vaga | BACKSPACE: desfaz ponto | C: limpa pontos | R: remover todas | S: salvar JSON | ESC/Q: sair",
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )

    def mouse_callback(self, event: int, x: int, y: int, flags: int, param) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.current_points) < 4:
                self.current_points.append((x, y))
                if len(self.current_points) == 4:
                    self.status_message = "Pressione ENTER para confirmar a vaga ou BACKSPACE para ajustar pontos."
                else:
                    remaining = 4 - len(self.current_points)
                    self.status_message = f"Selecione mais {remaining} ponto(s)."
            else:
                self.status_message = "Já existem 4 pontos. Pressione ENTER ou BACKSPACE."
            self.reset_canvas()

    def confirm_polygon(self) -> None:
        if len(self.current_points) != 4:
            self.status_message = "Uma vaga deve ter exatamente 4 pontos."
            return
        self.polygons.append(self.current_points[:])
        self.current_points.clear()
        self.status_message = "Vaga salva. Clique para iniciar a próxima."
        self.reset_canvas()

    def undo_polygon(self) -> None:
        if self.polygons:
            self.polygons.pop()
            self.status_message = "Última vaga removida."
        else:
            self.status_message = "Nenhuma vaga cadastrada."
        self.reset_canvas()

    def undo_point(self) -> None:
        if self.current_points:
            self.current_points.pop()
            remaining = 4 - len(self.current_points)
            self.status_message = f"Selecione mais {remaining} ponto(s)." if remaining else "Pressione ENTER para confirmar."
        else:
            self.status_message = "Nenhum ponto para remover."
        self.reset_canvas()

    def clear_current(self) -> None:
        self.current_points.clear()
        self.status_message = "Pontos atuais descartados. Clique para começar."
        self.reset_canvas()


def load_background(source: str) -> np.ndarray:
    if source.startswith(("rtsp://", "http://", "https://")) or Path(source).suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"}:
        cap = cv2.VideoCapture(source)
        grabbed, frame = cap.read()
        cap.release()
        if not grabbed:
            raise RuntimeError(f"Não foi possível ler um frame de '{source}'.")
        return frame

    image = cv2.imread(source)
    if image is None:
        raise RuntimeError(f"Não foi possível abrir a imagem '{source}'.")
    return image


def load_existing(json_path: Path) -> List[Polygon]:
    if not json_path.exists():
        return []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Erro ao interpretar {json_path}: {exc}") from exc

    polygons = []
    for item in data.get("areas", []):
        pts = item.get("points")
        if isinstance(pts, list) and len(pts) == 4:
            polygon = []
            valid = True
            for pt in pts:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    polygon.append((int(pt[0]), int(pt[1])))
                else:
                    valid = False
                    break
            if valid:
                polygons.append(polygon)
    return polygons


def save_polygons(json_path: Path, polygons: List[Polygon]) -> None:
    data = {
        "areas": [
            {"id": idx + 1, "points": [[int(x), int(y)] for x, y in polygon]}
            for idx, polygon in enumerate(polygons)
        ]
    }
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ferramenta para anotar vagas de estacionamento (4 pontos).")
    parser.add_argument("--source", required=True, help="Imagem ou vídeo/stream para extrair o quadro base.")
    parser.add_argument("--output", default="parking_areas.json", help="Arquivo JSON de saída (default: parking_areas.json).")
    parser.add_argument("--load", default=None, help="Arquivo JSON para carregar vagas existentes (default: igual ao output se existir).")
    args = parser.parse_args()

    background = load_background(args.source)
    json_path = Path(args.output)
    load_path = Path(args.load) if args.load else json_path

    existing_polygons = load_existing(load_path)
    annotator = ParkingAreaAnnotator(background, existing=existing_polygons)

    cv2.namedWindow(annotator.window, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(annotator.window, annotator.mouse_callback)
    annotator.reset_canvas()

    while True:
        cv2.imshow(annotator.window, annotator.canvas)
        key = cv2.waitKey(50) & 0xFF

        if key in {13, 10}:  # Enter
            annotator.confirm_polygon()
        elif key == 27:  # ESC
            break
        elif key in {ord("s"), ord("S")}:
            save_polygons(json_path, annotator.polygons)
            annotator.status_message = f"Vagas salvas em {json_path}."
            annotator.reset_canvas()
        elif key in {ord("u"), ord("U")}:
            annotator.undo_polygon()
        elif key == 8:  # Backspace
            annotator.undo_point()
        elif key in {ord("c"), ord("C")}:
            annotator.clear_current()
        elif key == ord("r"):
            annotator.clear_current()
            annotator.polygons.clear()
            annotator.status_message = "Todas as vagas foram removidas."
            annotator.reset_canvas()
        elif key == ord("q"):
            break

    cv2.destroyAllWindows()

    if annotator.polygons:
        save_polygons(json_path, annotator.polygons)
        print(f"Anotações salvas em {json_path.resolve()}")
    else:
        print("Nenhuma vaga salva.")


if __name__ == "__main__":
    main()
