from typing import NamedTuple

class ExitCode(NamedTuple):
    """
    A class to hold an error code and a message, and to format them nicely.
    """
    code: int
    name: str

    def __str__(self):
        return f"{self.code} ({self.name})"


class ExitCodes:
    """
    This class effectively implements an enumeration type that can be 
    extended. Python's native Enum class cannot be subclassed to extend
    the list of constants. We want this, here, so we can define some
    generic error codes but allow class users to extend the collection.

    The base class defines three exit codes common to all subclasses.
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
        redefined the top level SUCCESS/INTERNAL_ERROR/CLI_ERROR codes. This
        is almost certainly overkill, but reflects the intent of Ariel's
        original code (also probably overkill!).
        """

        # We iterate up the tree of base classes for the subclass
        # that's being defined, checking that we're purely inheriting
        # (directly or indirectly) from the base class, that all 
        # public attributes are ExitCode objects, that there are 
        # no duplicate public attributes (i.e. we're not trying to
        # override an already-defined ExitCode) and that we're not
        # reusing any exit code numbers.

        # Remember what we've examined and make sure to break out
        # when we reach "object", which is ExitCodes' parent.
        seen = set((object,))

        # A stack containing the list of parent classes we still need
        # to examine.
        todo = [cls]

        # Keep track of attribute names and used codes.
        definitions = {}
        codes = {}

        while len(todo) != 0:
            # Get a class off the todo list.
            cls = todo.pop()

            if cls in seen:
                # We've already examined this class (could happen with
                # multiple inheritance) so skip.
                continue

            if not issubclass(cls, ExitCodes):
                # It's not a subclass of ExitCodes - means that cls, or
                # something it inherits from, is not a pure subclass of
                # ExitCodes.
                raise ValueError(f"{cls.__name__} is not a pure subclass of ExitCode")

            # Check all attributes in cls
            for name, value in vars(cls).items():
                if name.startswith("_"):
                    # Not a public attribute - skip.
                    continue

                if not isinstance(value, ExitCode):
                    # This attribute's value is not an ExitCode.
                    raise ValueError(f"{cls.__name__}.{name} is not an ExitCode")

                if name in definitions:
                    # This attribute is already defined by another class.
                    raise ValueError(f"{definitions[name][0].__name__} and {cls.__name__} both define a {name} entry")

                if value.code in codes:
                    # This attribute's .code value is already used by another class.
                    # Since we're working up the tree, construct the
                    # exception text in reverse order.
                    code_def = codes[value.code]
                    raise ValueError(f"{code_def[0].__name__}.{code_def[1]} value ({value.code}) is already used by {cls.__name__}.{name}")

                # Note down the name and code so we can spot duplication as
                # we work up the tree.
                definitions[name] = (cls, value)
                codes[value.code] = (cls, name)

            # Note that we've examined this class and add its base
            # classes to our stack.
            seen.add(cls)
            todo += cls.__bases__

    def __new__(cls, *args, **kwargs):
        """
        The __new__ function is called to create an object before __init__
        is called. In the case of ExitCodes and its subclasses,
        instantiation is meaningless - raise an exception if someone
        tries.
        """
        raise RuntimeError(f"'{cls.__name__}' is an enumeration type and should not be instantiated")
