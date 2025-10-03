"""  Created on Mon Oct 3 14:10:53 2025
    @author: dcupolillo """

import cv2
import time
from tqdm import tqdm


def estimate_camera_fps() -> None:
    """Estimate the actual FPS of the camera"""

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    num_frames = 100
    frames_captured = 0

    start = time.time()

    for _ in tqdm(range(num_frames), desc="Capturing frames"):
        ret, frame = cap.read()
        if not ret:
            break
        frames_captured += 1

    end = time.time()

    actual_fps = frames_captured / (end - start)

    cap.release()

    return actual_fps


if __name__ == "__main__":
    fps = estimate_camera_fps()
    print(f"Actual camera FPS: {fps:.2f}")