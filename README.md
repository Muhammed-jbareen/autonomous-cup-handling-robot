# Vision-Based Autonomous Robot

This is a fully autonomous robot designed and built by me (Muhammed Jbareen, age 18) from scratch. It uses a single camera for object detection, alignment, and distance estimation, and performs robotic tasks like grabbing and pouring without using depth sensors.

## 🔧 Core Features

- YOLO-based object detection (cup recognition)
- Visual servoing: estimates distance from object size
- Real-time movement control via calibrated delay
- Robotic arm integration (xArm SDK)
- Shared memory IPC between vision and motion modules
- Full FSM (state machine) architecture

## 📹 Demo

![Pouring Demo](media/pouring_clip.gif)  
→ Full video: [demo.mp4](media/demo.mp4)

## 🧠 System Overview

![Architecture Diagram](docs/architecture.png)

1. `camera_controller.py`: detects cup, sends data to shared memory
2. `robot_controller.py`: aligns and moves based on visual input
3. `arm_controller.py`: executes grasp and pour actions

## 📐 Magic Number Calculation

See `utils/magic_number_calc.pdf` for the geometry and timing math behind the delay model (compensates for battery level, FOV, and frame size).

## 📁 Directory Guide

- `robot_controller/`: main system scripts
- `media/`: demo videos + images
- `docs/`: architecture, behavior logic, diagrams
- `utils/`: timing model, memory protocol docs

## 🚀 How to Run

1. Set up shared memory IPC
2. Launch `camera_controller.py` in one terminal
3. Run `robot_controller.py` in another
4. Robot will search, align, approach, grab, pour, and return autonomously

## 📜 License

MIT License
