import numpy as np
from core.ga_controller import _evaluate_fitness

# Test fitness
print("Testing fitness multi-cycle...")
fitness = _evaluate_fitness(
    chromosome=np.array([20, 20]),
    queue_snapshot={"N": 10, "S": 10, "E": 5, "W": 5},
    num_cycles=3,
    arrival_rate=0.5
)
print("Fitness:", fitness)

from data_pipeline.traffic_generator import TrafficGenerator
from pathlib import Path
import os
print("Testing traffic generator...")
tg = TrafficGenerator(csv_path=Path("data/big.csv").resolve())
volumes = tg.get_all_hourly_volumes()
print("Hourly volumes:", len(volumes))
print("Volume at hour 8:", tg.get_hourly_volume(8))

print("ALL PASSED.")
