import cv2
import numpy as np
import os


os.sched_setaffinity(0, {0, 1, 2, 3})

command_dict = {
    "move": True,
    "obstacle": False,
}


def filter_red(frame):
    top_half = frame[:frame.shape[0] // 2, :]
    frame = top_half

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    red_lower1 = np.array([0, 70, 50])   # First range of red
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([170, 70, 50]) # Second range of red
    red_upper2 = np.array([180, 255, 255])

    red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)

    return red_mask, is_dominant(red_mask)

def is_dominant(mask):
    total_pixels = mask.size
    red_pixels = cv2.countNonZero(mask)
    return red_pixels > (total_pixels / 20)

def compute_average_hsv(frame):
    height, width, _ = frame.shape

    # Define the size and position of the square (10% of frame size)
    square_size = int(min(height, width) * 0.5)
    center_x, center_y = width // 2, height // 2
    # center_x, center_y = width // 6, height // 6
    top_left_x = center_x - square_size // 2
    top_left_y = center_y - square_size // 2
    bottom_right_x = center_x + square_size // 2
    bottom_right_y = center_y + square_size // 2

    # Extract the region of interest (ROI)
    roi = frame[top_left_y:bottom_right_y, top_left_x:bottom_right_x]

    # Convert ROI to HSV
    # hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    hsv_roi = frame

    # Compute average HSV values
    avg_h = (np.mean(hsv_roi[:, :, 0]), np.std(hsv_roi[:, :, 0]))
    avg_s = (np.mean(hsv_roi[:, :, 1]), np.std(hsv_roi[:, :, 1]))
    avg_v = (np.mean(hsv_roi[:, :, 2]), np.std(hsv_roi[:, :, 2]))

    return avg_h, avg_s, avg_v


def capture_thread(port: str):
    gst_pipeline = (
        f"udpsrc port={port} caps=application/x-rtp,payload=96 ! "
        "rtpjitterbuffer latency=100 ! rtph264depay ! queue ! avdec_h264 ! "
        "videoconvert ! queue ! appsink"
    )
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Error: Unable to open video stream.")
        return

    # cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame. Exiting...")
            break

        cv2.imshow("Original Frame", frame)
        print("hererer", command_dict)

        if command_dict:
            processed_frame, obstacle_detected = filter_red(frame)
            # Overlay text based on `obstacle_detected` value
            if obstacle_detected:
                text = "Obstacle Detected!"
                color = (0, 0, 255)  # Red text for detection
            else:
                text = "No Obstacle"
                color = (0, 255, 0)  # Green text for no detection

            # Add text to the frame
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1
            thickness = 2
            line_type = cv2.LINE_AA

            # Position of the text (top-left corner)
            text_position = (10, 30)  # (x, y)

            cv2.putText(processed_frame, text, text_position, font, font_scale, color, thickness, line_type)

            # Show the processed frame
            cv2.imshow("Processed Frame", processed_frame)

            # Update the command dictionary
            command_dict["obstacle"] = obstacle_detected


        cv2.waitKey(1)

    cap.release()
    cv2.destroyAllWindows()

