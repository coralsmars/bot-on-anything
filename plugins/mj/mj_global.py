import threading
lock = threading.Lock()
MJ_RESULT=dict()
def put(key, data):
    lock.acquire()
    MJ_RESULT[key] =data
    lock.release()
def remove(key):
    lock.acquire()
    MJ_RESULT.pop(key, None)
    lock.release()
def get(key):
    lock.acquire()
    va = MJ_RESULT.get(key, None)
    lock.release()
    return va

def all():
    lock.acquire()
    l = [].extend(MJ_RESULT.values)
    MJ_RESULT.clear()
    lock.release()
    return l