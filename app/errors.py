class APIError(Exception):
    def __init__(
        self,
        message,
        status_code=400,
        error=None,
    ):
        self.message = message
        self.status_code = status_code
        self.error = error or message

        super().__init__(message)
