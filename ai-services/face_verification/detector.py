"""
detector.py — Detect & crop khuôn mặt dùng det_10g (buffalo_l / RetinaFace)
Fallback: YuNet → Haar Cascade
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .config import (
    DETECTOR_MODEL_PATH,
    YUNET_MODEL_PATH,
    DETECTOR_INPUT_SIZE,
    DET_SCORE_THRESHOLD,
    DET_NMS_THRESHOLD,
    ARCFACE_INPUT_SIZE,
)

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    face_crop:  np.ndarray          # Ảnh đã crop & resize (112x112 RGB)
    confidence: float
    bbox:       tuple               # (x1, y1, x2, y2) trong ảnh gốc
    kps:        Optional[np.ndarray] = field(default=None)  # 5 keypoints


class FaceDetector:
    """
    Detector ưu tiên:
      1. det_10g.onnx   (buffalo_l — RetinaFace, chính xác nhất)
      2. yunet           (fallback nếu chưa có det_10g)
      3. Haar Cascade   (fallback cuối)
    """

    def __init__(self):
        self._det10g   = None
        self._yunet    = None
        self._mode     = "haar"
        self._load_models()

    # ── Load ─────────────────────────────────────────────────

    def _load_models(self):
        if Path(DETECTOR_MODEL_PATH).exists():
            self._load_det10g()
        elif Path(YUNET_MODEL_PATH).exists():
            self._load_yunet()
        else:
            logger.warning("Không có model detector → dùng Haar Cascade fallback.")

    def _load_det10g(self):
        try:
            import onnxruntime as ort
            self._det10g = ort.InferenceSession(
                DETECTOR_MODEL_PATH,
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
            self._input_name  = self._det10g.get_inputs()[0].name
            self._mode = "det10g"
            logger.info("✅ det_10g.onnx loaded (buffalo_l detector).")
        except Exception as e:
            logger.error("Load det_10g thất bại: %s", e)
            self._det10g = None

    def _load_yunet(self):
        try:
            self._yunet = cv2.FaceDetectorYN.create(
                model=YUNET_MODEL_PATH,
                config="",
                input_size=DETECTOR_INPUT_SIZE,
                score_threshold=DET_SCORE_THRESHOLD,
                nms_threshold=DET_NMS_THRESHOLD,
            )
            self._mode = "yunet"
            logger.info("✅ yunet_face_detect.onnx loaded (fallback detector).")
        except Exception as e:
            logger.error("Load YuNet thất bại: %s", e)

    # ── Detect ───────────────────────────────────────────────

    def detect(self, image_bgr: np.ndarray) -> Optional[DetectionResult]:
        """Detect khuôn mặt lớn nhất, trả về crop 112×112 RGB."""
        if self._mode == "det10g":
            return self._detect_det10g(image_bgr)
        if self._mode == "yunet":
            return self._detect_yunet(image_bgr)
        return self._detect_haar(image_bgr)

    # ── det_10g (buffalo_l) ───────────────────────────────────

    def _detect_det10g(self, image_bgr: np.ndarray) -> Optional[DetectionResult]:
        """
        RetinaFace det_10g inference.
        Input: (1, 3, H, W) float32 BGR normalized
        Output: [scores, bboxes, kpss]
        """
        H, W = image_bgr.shape[:2]
        # Resize về input size để inference
        img = cv2.resize(image_bgr, DETECTOR_INPUT_SIZE)
        img = img.astype(np.float32)

        # Chuẩn hóa: trừ mean ImageNet
        img -= np.array([104.0, 117.0, 123.0], dtype=np.float32)
        img = img.transpose(2, 0, 1)          # HWC → CHW
        img = np.expand_dims(img, axis=0)     # (1, 3, H, W)

        try:
            outputs = self._det10g.run(None, {self._input_name: img})
        except Exception as e:
            logger.error("det_10g inference lỗi: %s", e)
            return None

        # outputs: list của nhiều stride outputs
        # Dùng InsightFace decode util để đơn giản hơn
        bboxes, kpss = self._decode_det10g_outputs(outputs, H, W)

        if len(bboxes) == 0:
            return None

        # Lấy bbox có score cao nhất
        best_idx = int(np.argmax(bboxes[:, 4]))
        x1, y1, x2, y2, score = bboxes[best_idx]
        kps = kpss[best_idx] if kpss is not None and len(kpss) > 0 else None

        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        crop = self._aligned_crop(image_bgr, kps) if kps is not None \
               else self._simple_crop(image_bgr, x1, y1, x2, y2)

        if crop is None:
            return None

        return DetectionResult(
            face_crop=crop,
            confidence=float(score),
            bbox=(x1, y1, x2, y2),
            kps=kps,
        )

    def _decode_det10g_outputs(
        self, outputs: list, orig_h: int, orig_w: int
    ) -> tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Decode multi-scale outputs của det_10g (buffalo_l).

        det_10g trả 9 tensors theo thứ tự:
            [score_s8, score_s16, score_s32,
             bbox_s8,  bbox_s16,  bbox_s32,
             kps_s8,   kps_s16,   kps_s32]

        KHÔNG xen kẽ theo stride như các model cũ hơn.
        """
        strides = [8, 16, 32]
        n       = len(strides)
        feat_h  = DETECTOR_INPUT_SIZE[0]
        feat_w  = DETECTOR_INPUT_SIZE[1]
        scale_h = orig_h / feat_h
        scale_w = orig_w / feat_w

        all_boxes = []
        all_kps   = []

        for idx, stride in enumerate(strides):
            # Thứ tự: tất cả scores → tất cả bboxes → tất cả kps
            if len(outputs) < n * 3:
                break

            scores_raw = outputs[idx]         # score stride idx
            bbox_raw   = outputs[idx + n]     # bbox  stride idx
            kps_raw    = outputs[idx + n * 2] # kps   stride idx

            scores = scores_raw.reshape(-1)
            bboxes = bbox_raw.reshape(-1, 4)
            kps    = kps_raw.reshape(-1, 5, 2) if kps_raw is not None else None

            # Đồng bộ kích thước — dùng len(bboxes) làm chuẩn
            n_bboxes = len(bboxes)
            scores   = scores[:n_bboxes]
            if kps is not None:
                kps = kps[:n_bboxes]

            # Tạo anchor grid khớp với n_bboxes
            fh          = int(feat_h / stride)
            fw          = int(feat_w / stride)
            n_locations = fh * fw
            num_anchors = max(1, round(n_bboxes / n_locations)) if n_locations else 2
            anchors     = self._generate_anchors(fh, fw, stride, num_anchors)

            # Cắt/tile để đúng n_bboxes
            if len(anchors) > n_bboxes:
                anchors = anchors[:n_bboxes]
            elif len(anchors) < n_bboxes:
                repeat  = int(np.ceil(n_bboxes / len(anchors)))
                anchors = np.tile(anchors, (repeat, 1))[:n_bboxes]

            # Decode bbox từ delta → tọa độ tuyệt đối
            cx = anchors[:, 0] + bboxes[:, 0] * stride
            cy = anchors[:, 1] + bboxes[:, 1] * stride
            bw = np.exp(np.clip(bboxes[:, 2], -10, 10)) * stride
            bh = np.exp(np.clip(bboxes[:, 3], -10, 10)) * stride

            x1 = (cx - bw / 2) * scale_w
            y1 = (cy - bh / 2) * scale_h
            x2 = (cx + bw / 2) * scale_w
            y2 = (cy + bh / 2) * scale_h

            mask = scores >= DET_SCORE_THRESHOLD
            if mask.sum() == 0:
                continue

            boxes_filtered = np.stack(
                [x1[mask], y1[mask], x2[mask], y2[mask], scores[mask]], axis=1
            )
            all_boxes.append(boxes_filtered)

            if kps is not None:
                kps_dec        = kps[mask].copy()
                anc_m          = anchors[mask]
                kps_dec[..., 0] = (anc_m[:, 0:1] + kps_dec[..., 0] * stride) * scale_w
                kps_dec[..., 1] = (anc_m[:, 1:2] + kps_dec[..., 1] * stride) * scale_h
                all_kps.append(kps_dec)

        if not all_boxes:
            return np.empty((0, 5)), None

        all_boxes_np = np.concatenate(all_boxes, axis=0)
        keep         = self._nms(all_boxes_np, DET_NMS_THRESHOLD)
        all_boxes_np = all_boxes_np[keep]
        all_kps_np   = np.concatenate(all_kps, axis=0)[keep] if all_kps else None

        return all_boxes_np, all_kps_np

    @staticmethod
    def _generate_anchors(fh: int, fw: int, stride: int, num_anchors: int = 2) -> np.ndarray:
        """Tạo anchor grid cho 1 stride."""
        ys, xs = np.mgrid[:fh, :fw]
        anchors = np.stack(
            [(xs.ravel() * stride + stride / 2),
             (ys.ravel() * stride + stride / 2)],
            axis=1
        ).astype(np.float32)
        if num_anchors > 1:
            return np.repeat(anchors, num_anchors, axis=0)
        return anchors

    @staticmethod
    def _nms(boxes: np.ndarray, iou_threshold: float) -> list:
        """Non-Maximum Suppression đơn giản."""
        if len(boxes) == 0:
            return []
        x1, y1, x2, y2, scores = boxes.T
        areas  = (x2 - x1) * (y2 - y1)
        order  = scores.argsort()[::-1]
        keep   = []
        while len(order):
            i = order[0]
            keep.append(i)
            if len(order) == 1:
                break
            inter_x1 = np.maximum(x1[i], x1[order[1:]])
            inter_y1 = np.maximum(y1[i], y1[order[1:]])
            inter_x2 = np.minimum(x2[i], x2[order[1:]])
            inter_y2 = np.minimum(y2[i], y2[order[1:]])
            inter    = np.maximum(0, inter_x2 - inter_x1) * np.maximum(0, inter_y2 - inter_y1)
            iou      = inter / (areas[i] + areas[order[1:]] - inter)
            order    = order[1:][iou < iou_threshold]
        return keep

    # ── Aligned crop dùng 5 keypoints ────────────────────────

    def _aligned_crop(
        self, image_bgr: np.ndarray, kps: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Crop & align khuôn mặt dùng 5 keypoints (mắt trái, mắt phải, mũi, miệng trái, miệng phải).
        Cho kết quả embedding chính xác hơn simple crop.
        """
        # Template 112x112 của ArcFace
        TEMPLATE = np.array([
            [38.2946, 51.6963],
            [73.5318, 51.5014],
            [56.0252, 71.7366],
            [41.5493, 92.3655],
            [70.7299, 92.2041],
        ], dtype=np.float32)

        try:
            M, _ = cv2.estimateAffinePartial2D(kps, TEMPLATE, method=cv2.LMEDS)
            if M is None:
                return None
            aligned = cv2.warpAffine(
                image_bgr, M, ARCFACE_INPUT_SIZE,
                flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT
            )
            return cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)
        except Exception as e:
            logger.debug("Aligned crop thất bại: %s", e)
            return None

    @staticmethod
    def _simple_crop(
        image_bgr: np.ndarray, x1: int, y1: int, x2: int, y2: int
    ) -> Optional[np.ndarray]:
        """Crop đơn giản khi không có keypoints."""
        H, W = image_bgr.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(W, x2), min(H, y2)
        if x2 <= x1 or y2 <= y1:
            return None
        crop_rgb = cv2.cvtColor(image_bgr[y1:y2, x1:x2], cv2.COLOR_BGR2RGB)
        return cv2.resize(crop_rgb, ARCFACE_INPUT_SIZE, interpolation=cv2.INTER_LINEAR)

    # ── YuNet fallback ────────────────────────────────────────

    def _detect_yunet(self, image_bgr: np.ndarray) -> Optional[DetectionResult]:
        h, w = image_bgr.shape[:2]
        self._yunet.setInputSize((w, h))
        _, faces = self._yunet.detect(image_bgr)
        if faces is None or len(faces) == 0:
            return None
        best  = max(faces, key=lambda f: f[14])
        x, y, fw, fh = int(best[0]), int(best[1]), int(best[2]), int(best[3])
        crop  = self._simple_crop(image_bgr, x, y, x + fw, y + fh)
        if crop is None:
            return None
        return DetectionResult(
            face_crop=crop, confidence=float(best[14]), bbox=(x, y, x + fw, y + fh)
        )

    # ── Haar fallback ─────────────────────────────────────────

    def _detect_haar(self, image_bgr: np.ndarray) -> Optional[DetectionResult]:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        faces = cv2.CascadeClassifier(path).detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
        )
        if len(faces) == 0:
            return None
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        crop = self._simple_crop(image_bgr, x, y, x + fw, y + fh)
        if crop is None:
            return None
        return DetectionResult(face_crop=crop, confidence=0.8, bbox=(x, y, x + fw, y + fh))


# ── Image decode utils ────────────────────────────────────────

def decode_image_bytes(image_bytes: bytes) -> Optional[np.ndarray]:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def decode_base64_image(b64_str: str) -> Optional[np.ndarray]:
    import base64
    try:
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        return decode_image_bytes(base64.b64decode(b64_str))
    except Exception as e:
        logger.error("Decode base64 thất bại: %s", e)
        return None
