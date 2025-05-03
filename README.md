# Vision-Based Autonomous Robot

This project is a fully autonomous robot designed to locate a white cup containing water, pick it up, search for a red cup, pour water into it, and put the white cup back. It uses computer vision, real-time decision-making, shared memory communication, and precise motion control without any external sensor.

## 🚀 Features

- Real-time YOLOv8 object detection
- Shared memory communication protocol
- Monocular depth estimation for movement control
- Visual servoing to align with objects
- Robotic arm integration with xArm
- Adaptive motor speed control based on cup distance

## 📹 Demo

![Pouring Demo](media/pouring_clip.gif)  
→ Full video: [demo.mp4](media/demo.mp4)

## 🧠 System Overview

The robot utilizes a Raspberry Pi 5 with a V3 camera module to run a YOLOv8 model in real-time. It detects cups, determines their colors, calculates relative distances, and communicates via shared memory with a motor control script that handles motion and manipulation.

1. `camera_controller.py`: detects cup, sends data to shared memory
2. `robot_controller.py`: aligns and moves based on visual input
3. `arm_controller.py`: executes grasp and pour actions

### ⚙️ Key Modules

- **Camera Processor**: Captures images, runs object detection, calculates color and size, then sends the data via shared memory.
- **Robot Controller**: Receives detection data, rotates, approaches, and commands the robotic arm to perform physical actions.
- **Arm Controller**: Handles servo movement and coordination for grabbing and pouring.
- **Shared Memory Protocol**: Efficient binary protocol for inter-process communication.

## 🧱 Architecture Diagram

![System Architecture](A_system_overview_diagram_illustrates_an_autonomou.png)

## 🛠️ Technologies Used

- **Languages**: Python
- **Libraries**: OpenCV, ultralytics, smbus, multiprocessing, TensorFlow (backend)
- **Hardware**: Raspberry Pi 5, V3 Camera Module, xArm1s, 4-channel encoder motor driver

## 📐 Magic Number Calculation

See `utils/magic_number_calc.pdf` for the geometry and timing math behind the delay model (compensates for battery level, FOV, and frame size).

## 📁 Directory Guide

- `robot_controller/`: main system scripts
- `media/`: demo videos + images
- `docs/`: architecture, behavior logic, diagrams
- `utils/`: timing model, memory protocol docs

## 🧪 Usage

1. Clone the repository
2. Set up the `config.ini` file with correct camera resolution, shared memory name, and voltage.
3. Run the camera detection script:
   ```bash
   python camera_controller.py
   ```
4. Run the robot controller:
   ```bash
   python robot_controller.py
   ```

## 📜 License

This project is released under the MIT License.
