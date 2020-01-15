import pycares

for code, name in pycares.errno.errorcode.items():
    globals()[name] = code


class DNSError(Exception):
    def __init__(self, error_num, error_str):
        self.error_num = error_num
        self.error_str = error_str

    def __str__(self):
        return f"errorno({self.error_num}): {self.error_str}"
