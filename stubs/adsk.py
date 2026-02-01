# Minimal stub so VS Code doesn't freak out

class core:
    class Application:
        @staticmethod
        def get():
            return None

    class ValueInput:
        @staticmethod
        def createByString(s): pass

    class Matrix3D:
        @staticmethod
        def create(): pass

    class Vector3D:
        @staticmethod
        def create(x, y, z): pass


class fusion:
    class Design:
        @staticmethod
        def cast(x): return None

    class FeatureOperations:
        NewBodyFeatureOperation = 0
