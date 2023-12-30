import argparse
import logging
import logutil
import sys
import time
import traceback

import budgets

# Logging to file
logutil.add_file_handler()
logger = logging.getLogger(__name__)
logger.setLevel(logutil.get_deadline_config_level())

# Logging to stdout
log_handler = logging.StreamHandler()
log_fmt = logging.Formatter(
    "%(asctime)s - [%(levelname)-7s] "
    "[%(module)s:%(funcName)s:%(lineno)d] %(message)s"
)
log_handler.setFormatter(log_fmt)
logger.addHandler(log_handler)


def main():
    """Run at least one pass of notification.

    Command line arguments:
        -d (--delay): Refresh delay in seconds.
    """
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        '-d', '--delay',
        help='Set refresh delay in seconds. Specify 0 to run only once.',
        default=15
    )

    namespace = parser.parse_args(sys.argv[1:])
    
    # Check all budgets on all farms across all studios,
    # repeated every namespace.delay seconds
    while True:
        try:
            results = budgets.run()
            logger.info(results)
        except:
            logger.error(traceback.format_exc())
        
        if namespace.delay > 0:
            time.sleep(namespace.delay)
        else:
            break


if __name__ == "__main__":
    """Start the notifier.

    Exit codes:
        0 on success, 1 if exiting due to an error.
    """
    try:
        main()
        sys.exit(0)
    except:
        logger.error(traceback.format_exc())
        sys.exit(1)
