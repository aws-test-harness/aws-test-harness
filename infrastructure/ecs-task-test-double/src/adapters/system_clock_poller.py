from time import time, sleep


class SystemClockPoller:

    def __init__(self, logger):
        super().__init__()
        self.__logger = logger

    def poll_for_value(self, try_get_value, timeout_seconds, interval_seconds):
        start_time = time()

        while True:
            self.__logger.debug("Polling...")
            value = try_get_value()

            if value is None:
                if time() - start_time > timeout_seconds:
                    raise TimeoutError()

                self.__logger.debug("Sleeping...")
                sleep(interval_seconds)
            else:
                return value
