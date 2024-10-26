# YOLOX OpenVINO Inference

This repository provides a step-by-step guide to run inference with the YOLOX model using Intel's OpenVINO toolkit.

## Prerequisites

Before you begin, make sure you have the following components installed:

- **[OpenVINO Toolkit](https://docs.openvino.ai/latest/openvino_docs_install_guides_installing_openvino_windows.html)**
- **Python 3.8 or later** (tested with Python 3.10)
- **Open Model Zoo Tools**: `omz_downloader` and `omz_converter`

To install the required Python dependencies:

```bash
pip install -r requirements.txt
```

## Download and Convert YOLOX-Tiny Model

### 1. Download the YOLOX-Tiny Model

Use the Open Model Zoo Downloader to fetch the YOLOX-Tiny model:

```bash
omz_downloader --name yolox-tiny
```

*This command will download the YOLOX-Tiny model to the default Open Model Zoo directory.*

### 2. Convert the Model to OpenVINO IR Format

To convert the YOLOX-Tiny model into OpenVINO's Intermediate Representation (IR) format:

```bash
omz_converter --name yolox-tiny --precisions FP16
```

*The conversion generates `.xml` and `.bin` files that are optimized for OpenVINO inference.*

## Run Inference

### 1. Locate the Converted Model Files

The converted model files (`yolox-tiny.xml` and `yolox-tiny.bin`) will be located in the `public/yolox-tiny/FP16` directory.

### 2. Inference Script

Refer to the [infer_yolox_openvino.ipynb](infer_yolox_openvino.ipynb) Jupyter notebook for detailed steps on running image and video inference.

*This notebook provides a comprehensive guide to running inference and visualizing the results using OpenVINO.*

## References

- [YOLOX-Tiny Model Documentation](https://docs.openvino.ai/2024/omz_models_model_yolox_tiny.html)
- [OpenVINO Toolkit Documentation](https://docs.openvino.ai/latest/index.html)
- [Open Model Zoo Repository](https://github.com/openvinotoolkit/open_model_zoo)