#!/usr/bin/env python3
"""Optional glasses-removal pre-pass using BiSeNet face parsing + TELEA inpaint.

Skeleton only. Wire in your preferred ONNX parser and OpenCV inpaint.
"""

def remove_glasses(input_path: str, output_path: str) -> None:
    raise NotImplementedError("Wire BiSeNet (or similar) + dilation + TELEA inpaint")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: prepass_glasses.py <input.mp4> <output.mp4>")
        sys.exit(1)
    remove_glasses(sys.argv[1], sys.argv[2])
