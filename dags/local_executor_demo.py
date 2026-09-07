from __future__ import annotations

import os
import time
from datetime import datetime

import pendulum
from airflow.decorators import dag, task


@dag(
    dag_id="local_executor_demo",
    schedule=None,
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    tags=["executor", "example"],
)
def local_executor_demo():

    @task
    def start() -> None:
        print("Starting parallel task demo")

    @task
    def parallel_task(name: str) -> None:
        print(f"[{name}] pid={os.getpid()} start={datetime.now().isoformat()}")
        time.sleep(5)
        print(f"[{name}] pid={os.getpid()} end={datetime.now().isoformat()}")

    @task
    def finish() -> None:
        print("All parallel tasks finished")

    tasks = [parallel_task(f"task-{i}") for i in range(3)]

    start() >> tasks >> finish()


local_executor_demo()
