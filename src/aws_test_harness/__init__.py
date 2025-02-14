import threading
import traceback


def handle_uncaught_thread_exception(args):
    print('Uncaught exception in thread')
    print(f"Exception Type: {args.exc_type.__name__}")
    print(f"Exception Message: {args.exc_value}")
    traceback.print_tb(args.exc_traceback)


threading.excepthook = handle_uncaught_thread_exception
