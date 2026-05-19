class ImageBuildError(Exception):
    """Exception raised for errors in building images"""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)