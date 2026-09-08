from datetime import datetime


def log(component: str, message: str) -> None:
    """Write one timestamped Chinese-friendly log line."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{now} [{component}] {message}", flush=True)
