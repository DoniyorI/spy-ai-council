from src.reporting.daily_report import generate_report
from src.utils.time_helpers import today_et
from src.utils.logging_config import log


def main():
    log.info("Generating EOD report...")
    report = generate_report(today_et())
    print(report)
    log.info("EOD report complete")


if __name__ == "__main__":
    main()
