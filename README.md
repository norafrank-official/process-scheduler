# ⚙️ Process Scheduler

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A robust Python application designed for simulating, managing, and visualizing operating system process scheduling algorithms. This project provides practical tools for exploring how various CPU scheduling strategies handle task execution, waiting times, and resource allocation.

---

## 🚀 Features

* **Interactive Live Simulation (`live.py`):** Real-time execution tracking and visualization of process scheduling.
* **Classic Scheduling Algorithms:** Supports core CPU scheduling paradigms such as:
  * First-Come, First-Served (FCFS)
  * Shortest Job First (SJF / SJN)
  * Round Robin (RR)
  * Priority Scheduling
* **Performance Metrics:** Automatically calculates key scheduling metrics including:
  * Waiting Time
  * Turnaround Time
  * Response Time
* **Clean & Modular Structure:** Easy-to-understand codebase built for academic learning, operating systems study, and algorithm experimentation.

---

## 📂 Repository Structure

```text
process-scheduler/
├── live.py           # Core live simulation script
├── src/              # Source code modules and algorithms
├── tests/            # Unit tests for scheduling algorithms
├── .gitignore        # Git ignore rules
└── README.md         # Project documentation
