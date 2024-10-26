from openvino.runtime import Core
import numpy as np
from colors import _COLORS
import cv2
import matplotlib.pyplot as plt

def nms(boxes, scores, nms_thr):
    """Single class NMS implemented in Numpy."""
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)

        inds = np.where(ovr <= nms_thr)[0]
        order = order[inds + 1]

    return keep

def multiclass_nms_class_agnostic(boxes, scores, nms_thr, score_thr):
    """Multiclass NMS implemented in Numpy. Class-agnostic version."""
    cls_inds = scores.argmax(1)
    cls_scores = scores[np.arange(len(cls_inds)), cls_inds]

    valid_score_mask = cls_scores > score_thr
    if valid_score_mask.sum() == 0:
        return None
    valid_scores = cls_scores[valid_score_mask]
    valid_boxes = boxes[valid_score_mask]
    valid_cls_inds = cls_inds[valid_score_mask]
    keep = nms(valid_boxes, valid_scores, nms_thr)
    if keep:
        dets = np.concatenate(
            [valid_boxes[keep], valid_scores[keep, None], valid_cls_inds[keep, None]], 1
        )
    return dets

def multiclass_nms_class_aware(boxes, scores, nms_thr, score_thr):
    """Multiclass NMS implemented in Numpy. Class-aware version."""
    final_dets = []
    num_classes = scores.shape[1]
    for cls_ind in range(num_classes):
        cls_scores = scores[:, cls_ind]
        valid_score_mask = cls_scores > score_thr
        if valid_score_mask.sum() == 0:
            continue
        else:
            valid_scores = cls_scores[valid_score_mask]
            valid_boxes = boxes[valid_score_mask]
            keep = nms(valid_boxes, valid_scores, nms_thr)
            if len(keep) > 0:
                cls_inds = np.ones((len(keep), 1)) * cls_ind
                dets = np.concatenate(
                    [valid_boxes[keep], valid_scores[keep, None], cls_inds], 1
                )
                final_dets.append(dets)
    if len(final_dets) == 0:
        return None
    return np.concatenate(final_dets, 0)

def multiclass_nms(boxes, scores, nms_thr, score_thr, class_agnostic=True):
    """Multiclass NMS implemented in Numpy"""
    if class_agnostic:
        nms_method = multiclass_nms_class_agnostic
    else:
        nms_method = multiclass_nms_class_aware
    return nms_method(boxes, scores, nms_thr, score_thr)

def vis(img, boxes, scores, cls_ids, conf=0.5, class_names=None):

    for i in range(len(boxes)):
        box = boxes[i]
        cls_id = int(cls_ids[i])
        score = scores[i]
        if score < conf:
            continue
        x0 = int(box[0])
        y0 = int(box[1])
        x1 = int(box[2])
        y1 = int(box[3])

        color = (_COLORS[cls_id] * 255).astype(np.uint8).tolist()
        text = '{}:{:.1f}%'.format(class_names[cls_id], score * 100)
        txt_color = (0, 0, 0) if np.mean(_COLORS[cls_id]) > 0.5 else (255, 255, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX

        txt_size = cv2.getTextSize(text, font, 0.4, 1)[0]
        cv2.rectangle(img, (x0, y0), (x1, y1), color, 2)

        txt_bk_color = (_COLORS[cls_id] * 255 * 0.7).astype(np.uint8).tolist()
        cv2.rectangle(
            img,
            (x0, y0 + 1),
            (x0 + txt_size[0] + 1, y0 + int(1.5*txt_size[1])),
            txt_bk_color,
            -1
        )
        cv2.putText(img, text, (x0, y0 + txt_size[1]), font, 0.4, txt_color, thickness=1)

    return img

def demo_postprocess(outputs, img_size, p6=False):
    grids = []
    expanded_strides = []
    strides = [8, 16, 32] if not p6 else [8, 16, 32, 64]

    hsizes = [img_size[0] // stride for stride in strides]
    wsizes = [img_size[1] // stride for stride in strides]

    for hsize, wsize, stride in zip(hsizes, wsizes, strides):
        xv, yv = np.meshgrid(np.arange(wsize), np.arange(hsize))
        grid = np.stack((xv, yv), 2).reshape(1, -1, 2)
        grids.append(grid)
        shape = grid.shape[:2]
        expanded_strides.append(np.full((*shape, 1), stride))

    grids = np.concatenate(grids, 1)
    expanded_strides = np.concatenate(expanded_strides, 1)
    outputs[..., :2] = (outputs[..., :2] + grids) * expanded_strides
    outputs[..., 2:4] = np.exp(outputs[..., 2:4]) * expanded_strides

    return outputs

def preproc(img, input_size, swap=(2, 0, 1)):
    if len(img.shape) == 3:
        padded_img = np.ones((input_size[0], input_size[1], 3), dtype=np.uint8) * 114
    else:
        padded_img = np.ones(input_size, dtype=np.uint8) * 114

    r = min(input_size[0] / img.shape[0], input_size[1] / img.shape[1])
    resized_img = cv2.resize(
        img,
        (int(img.shape[1] * r), int(img.shape[0] * r)),
        interpolation=cv2.INTER_LINEAR,
    ).astype(np.uint8)
    padded_img[: int(img.shape[0] * r), : int(img.shape[1] * r)] = resized_img

    padded_img = padded_img.transpose(swap)
    padded_img = np.ascontiguousarray(padded_img, dtype=np.float32)
    return padded_img, r

def load_classes(classes_file):
    """Load class names from a file."""
    with open(classes_file, 'r') as f:
        return [line.strip() for line in f.readlines()]
    
def initialize_model(model_path, device="AUTO", performance_hint="LATENCY"):
    """Initialize and compile the OpenVINO model with optimizations."""
    ie = Core()

    # Set performance hint
    ie.set_property(device_name=device, properties={"PERFORMANCE_HINT": performance_hint})

    # Read and compile the model
    model = ie.read_model(model=model_path)
    compiled_model = ie.compile_model(model=model, device_name=device)

    # Retrieve input shape
    input_shape = compiled_model.input(0).shape

    return compiled_model, input_shape


def preprocess_image(image, input_shape):
    """Preprocess the input image for YOLOX model inference."""
    image, ratio = preproc(image, (input_shape[2], input_shape[3]))
    image = np.expand_dims(image, axis=0)
    return image, ratio

def postprocess_results(results, input_shape, ratio, nms_thr=0.45, score_thr=0.1):
    """Post-process YOLOX model output."""
    predictions = demo_postprocess(results, (input_shape[2], input_shape[3]))[0]
    boxes = predictions[:, :4]
    scores = predictions[:, 4, None] * predictions[:, 5:]

    # Convert boxes from center to xyxy format
    boxes_xyxy = np.ones_like(boxes)
    boxes_xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2.
    boxes_xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2.
    boxes_xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2.
    boxes_xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2.
    boxes_xyxy /= ratio

    # Apply Non-Maximum Suppression
    dets = multiclass_nms(boxes_xyxy, scores, nms_thr=nms_thr, score_thr=score_thr)
    
    if dets is not None:
        final_boxes = dets[:, :4].tolist()  # xyxy format
        final_scores = dets[:, 4].tolist()
        final_cls_inds = dets[:, 5].tolist()
        return final_boxes, final_scores, final_cls_inds
    return None, None, None

def visualize_results(image, boxes, scores, cls_inds, conf, classes):
    """Visualize the detection results on the image."""
    if boxes is not None:
        image = vis(image, boxes, scores, cls_inds, conf=conf, class_names=classes)
    return image

class YoloXOpenVinoInference:
    """YOLOX inference using OpenVINO."""

    def __init__(self, model_path, classes_file, device="CPU", nms = 0.4 ,confidence=0.5):
        """Initialize YOLOX model using OpenVINO."""
        self.classes = load_classes(classes_file)
        self.confidence = confidence
        self.nms = nms
        self.model_path = model_path
        self.device = device
        self.input_shape = None

        # Initialize model
        self.compiled_model, self.input_shape = initialize_model(model_path, device)

    def inference(self, image, show_results=True):
        """Run YOLOX inference on the input image."""
        # Preprocess image
        preprocessed_img, ratio = preprocess_image(image, self.input_shape)

        # Perform inference
        results = self.compiled_model([preprocessed_img])[self.compiled_model.output(0)]

        # Post-process results
        boxes, scores, class_indices = postprocess_results(
            results, self.input_shape, ratio, self.nms, self.confidence
        )

        if boxes is None:
            return [], [], [], [], None

        class_names = [self.classes[int(i)] for i in class_indices]

        # Visualize results
        output_img = visualize_results(image, boxes, scores, class_indices, self.confidence, self.classes)
        
        if show_results:
            plt.figure(figsize=(10, 10))
            plt.imshow(output_img)
            plt.show()
        
        return boxes, scores, class_indices, class_names, output_img

    def video_inference(self, video_path, output_path=None, show_results=True):
        """Run YOLOX inference on video."""
        # Open video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("Error: Could not open video.")
            return

        # Get video properties
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Define the codec and create VideoWriter object if output_path is specified
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

        import time
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Run inference on the frame
            t1 = time.time()
            _, _, _, _, output_frame = self.inference(frame, show_results=False)
            t2 = time.time()
            fps = round(1/(t2-t1),1)
            
            if output_frame is None:
                output_frame = frame
                
            # Add fps :
            cv2.putText(output_frame, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # Display the results
            if show_results:
                cv2.imshow("YOLOX Video Inference", output_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            # Write the frame to output video
            if output_path:
                out.write(output_frame)

        # Release video capture and writer objects
        cap.release()
        if output_path:
            out.release()

        # Close any open OpenCV windows
        if show_results:
            cv2.destroyAllWindows()

    
    
      


