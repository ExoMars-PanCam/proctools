from typing import NamedTuple

class ExitCode(NamedTuple):
    """
    A class to hold an error code and message.
    """
    code: int
    name: str

    def __str__(self):
        return f"{self.code} ({self.name})"


class ExitCodes:
    """
    This class is intended to be inherited from, and you cannot
    instantiate an object of it directly.

    It defines three exit codes common to all subclasses.
    """

    # The comon exit codes.
    SUCCESS = ExitCode(0, "success")
    INTERNAL_ERROR = ExitCode(1, "internal error")
    CLI_ERROR = ExitCode(2, "commandline error")

    def __init_subclass__(cls):
        """
        The __init_subclass__ function is called when a subclass of the
        current class is *defined*.

        This class uses __init_subclass__ to ensure that subclasses haven't
        redefined the top level SUCCESS/INTERNAL_ERROR/CLI_ERROR codes.
        """

        # Make a dict of key/value pairs, where the keys are our codes
        # defined above.
        common_codes = {
            n: c for n, c in vars(ExitCodes).items() if not n.startswith("_")
        }

        # Now run through the dict.
        for name, code in common_codes.items():
            # Lookup the name in the subclass and compare it with the
            # value in the current class. If it's different, that means
            # the subclass has redefined it and we'll raise an error.
            sub_code = getattr(cls, name, None)
            if sub_code != code:
                raise ValueError(
                    f"{cls.__name__}.{name}: common exit codes should not be"
                    " overwritten by subclasses"
                )

    def __new__(cls, *args, **kwargs):
        """
        The __new__ function is called to create an object before __init__
        is called. In the case of the ExitCodes class, we raise an exception
        to prevent instantiation of objects of this type.
        """
        raise RuntimeError(f"{cls} should not be instantiated")
