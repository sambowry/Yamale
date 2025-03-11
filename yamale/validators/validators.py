import re
from datetime import date, datetime
import ipaddress
from .base import Validator
from . import constraints as con
from .. import util
from .. import yamale

# ABCs for containers were moved to their own module
try:
    from collections.abc import Sequence, Mapping
except ImportError:
    from collections import Sequence, Mapping


class String(Validator):
    """String validator"""

    tag = "str"
    constraints = [
        con.LengthMin,
        con.LengthMax,
        con.CharacterExclude,
        con.StringEquals,
        con.StringStartsWith,
        con.StringEndsWith,
        con.StringMatches,
    ]

    def _is_valid(self, value):
        return util.isstr(value)


class Number(Validator):
    """Number/float validator"""

    value_type = float
    tag = "num"
    constraints = [con.Min, con.Max]

    def _is_valid(self, value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)


class Integer(Validator):
    """Integer validator"""

    value_type = int
    tag = "int"
    constraints = [con.Min, con.Max]

    def _is_valid(self, value):
        return isinstance(value, int) and not isinstance(value, bool)


class Boolean(Validator):
    """Boolean validator"""

    tag = "bool"

    def _is_valid(self, value):
        return isinstance(value, bool)


class Enum(Validator):
    """Enum validator"""

    tag = "enum"

    def __init__(self, *args, **kwargs):
        super(Enum, self).__init__(*args, **kwargs)
        self.enums = args

    def _is_valid(self, value):
        return value in self.enums

    def fail(self, value):
        return "'%s' not in %s" % (value, self.enums)


class Day(Validator):
    """Day validator. Format: YYYY-MM-DD"""

    value_type = date
    tag = "day"
    constraints = [con.Min, con.Max]

    def _is_valid(self, value):
        return isinstance(value, date)


class Timestamp(Validator):
    """Timestamp validator. Format: YYYY-MM-DD HH:MM:SS"""

    value_type = datetime
    tag = "timestamp"
    constraints = [con.Min, con.Max]

    def _is_valid(self, value):
        return isinstance(value, datetime)


class Map(Validator):
    """Map and dict validator"""

    tag = "map"
    constraints = [con.LengthMin, con.LengthMax, con.Key]

    def __init__(self, *args, **kwargs):
        super(Map, self).__init__(*args, **kwargs)
        self.validators = [val for val in args if isinstance(val, Validator)]

    def _is_valid(self, value):
        return isinstance(value, Mapping)


class List(Validator):
    """List validator"""

    tag = "list"
    constraints = [con.LengthMin, con.LengthMax]

    def __init__(self, *args, **kwargs):
        super(List, self).__init__(*args, **kwargs)
        self.validators = [val for val in args if isinstance(val, Validator)]

    def _is_valid(self, value):
        return isinstance(value, Sequence) and not util.isstr(value)


class Include(Validator):
    """Include validator"""

    tag = "include"

    def __init__(self, *args, **kwargs):
        self.include_name = args[0]
        self.strict       = kwargs.pop("strict", None)
        super(Include, self).__init__(*args, **kwargs)

    def _is_valid(self, value):
        self.errors = []
        if isinstance(value,str):
            try:
              self.errors += yamale.schema.includes[self.include_name].validate( value, self.include_name, self.strict ).errors
            except KeyError:
              self.errors = [ f"'{self.include_name}' is not included" ]
        return not self.errors

    def get_name(self):
        return self.include_name

    def fail(self, value):
        return "'%s' is not %s because %s" % (value, self.include_name, '; '.join( self.errors ) )

class Any(Validator):
    """Any of several types validator"""

    tag = "any"

    def __init__(self, *args, **kwargs):
        self.literals   = []
        self.validators = []
        for val in args:
            if isinstance(val, Validator):
                self.validators.append( val )
            else:
                self.literals.append( val )

        if self.literals:
            self.validators.append( Enum( *self.literals ) )

        super(Any, self).__init__(*args, **kwargs)

    def _is_valid(self, value):
        return True


class NotAny(Validator):
    """No one of several types validator"""

    tag = "notany"
 
    def __init__(self, *args, **kwargs):
        self.validators = Any( *args, **kwargs ).validators
        super(NotAny, self).__init__(*args, **kwargs)

    def _is_valid(self, value):
        return True


class All(Validator):
    """All of several types validator"""

    tag = "all"
 
    def __init__(self, *args, **kwargs):
        self.validators = Any( *args, **kwargs ).validators
        super(All, self).__init__(*args, **kwargs)

    def _is_valid(self, value):
        return True


class Subset(Validator):
    """Subset of several types validator"""

    tag = "subset"

    def __init__(self, *args, **kwargs):
        super(Subset, self).__init__(*args, **kwargs)
        self._allow_empty_set = bool(kwargs.pop("allow_empty", False))
        self.validators = [val for val in args if isinstance(val, Validator)]
        if not self.validators:
            raise ValueError("'%s' requires at least one validator!" % self.tag)

    def _is_valid(self, value):
        return self.can_be_none or value is not None

    def fail(self, value):
        # Called in case `_is_valid` returns False
        return "'%s' may not be an empty set." % self.get_name()

    @property
    def is_optional(self):
        return self._allow_empty_set

    @property
    def can_be_none(self):
        return self._allow_empty_set


class Null(Validator):
    """Validates null"""

    value_type = None
    tag = "null"

    def _is_valid(self, value):
        return value is None


class Regex(Validator):
    """Regular expression validator"""

    tag = "regex"
    _regex_flags = {"ignore_case": re.I, "multiline": re.M, "dotall": re.S}

    def __init__(self, *args, **kwargs):
        self.regex_name = kwargs.pop("name", None)

        flags = 0
        for k, v in util.get_iter(self._regex_flags):
            flags |= v if kwargs.pop(k, False) else 0

        self.regexes = [re.compile(arg, flags) for arg in args if util.isstr(arg)]
        super(Regex, self).__init__(*args, **kwargs)

    def _is_valid(self, value):
        return util.isstr(value) and any(r.match(value) for r in self.regexes)

    def get_name(self):
        return self.regex_name or self.tag + " match"


class Ip(Validator):
    """IP address validator"""

    tag = "ip"
    constraints = [con.IpVersion, con.IpPrefix]

    def __init__(self, *args, **kwargs):
        self.strict = bool(kwargs.get("strict", False))
        super(Ip, self).__init__(*args, **kwargs)

    def _is_valid(self, value):
        return self.ip_address(value)

    def ip_address(self, value):
        try:
            ip = ipaddress.ip_network(util.to_unicode(value), self.strict)
        except ValueError:
            return False
        return True

    def fail(self, value):
        return "'%s' is not ip(%s)" % (value, str(self.kwargs) )


class Mac(Regex):
    """MAC address validator"""

    tag = "mac"

    def __init__(self, *args, **kwargs):
        super(Mac, self).__init__(*args, **kwargs)
        self.regexes = [
            re.compile(r"[0-9a-fA-F]{2}([-:]?)[0-9a-fA-F]{2}(\1[0-9a-fA-F]{2}){4}$"),
            re.compile(r"[0-9a-fA-F]{4}([-:]?)[0-9a-fA-F]{4}(\1[0-9a-fA-F]{4})$"),
        ]


class SemVer(Regex):
    """Semantic Versioning (semver.org) validator"""

    tag = "semver"

    def __init__(self, *args, **kwargs):
        super(SemVer, self).__init__(*args, **kwargs)
        self.regexes = [
            # https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
            re.compile(
                r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
            ),
        ]

class FileLine(Validator):
    """checks if the value is in a file line"""

    tag = "file_line"

    constraints = [
        con.FileLine
    ]

    def __init__(self, *args, **kwargs):
        self.filename = args
        self.error    = ''
        super(FileLine, self).__init__(*args, **dict( kwargs, filename=args ))

    def _is_valid(self, value):
        from pathlib import Path
        for fn in self.filename:
          f = Path(fn)
          if not f.is_file():
            self.error = f"file '{fn}' does not exists"
        return not self.error

    def fail(self, value):
        return self.error


DefaultValidators = {}

for v in util.get_subclasses(Validator):
    # Allow validator nodes to contain either tags or actual name
    DefaultValidators[v.tag] = v
    DefaultValidators[v.__name__] = v
