import cells
from cells import Cell

DEBUG = False

def _debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "observer".rjust(cells._DECO_OFFSET) + " > ")
    if DEBUG or cells.DEBUG:
        print " ".join(msgs)

# we want observers to be defined at the class level but have per-instance
# information. So, do the same trick as is done with CellAttr/Cells
class ObserverAttr(object):
    """
    Wrapper for Observers within Models. Will auto-vivify an Observer
    within a Model instance the first time it's called. 
    """
    def __init__(self, name, *args, **kwargs):
        self.name, self.args, self.kwargs = name, args, kwargs

    def __get__(self, owner, ownertype):
        if not owner: return self
        # if there isn't a value in owner.myname, make it an observer
        _debug("got request for observer", self.name,
              "args =", str(self.args),
              "kwargs =", str(self.kwargs))
        if self.name not in owner.__dict__.keys():
            owner.__dict__[self.name] = Observer(*self.args,
                                                 **self.kwargs)
        return owner.__dict__[self.name]

class Observer(object):
    """
    Wrapper for a function which fires when a C{L{Model}} updates and
    certain conditions are met. Observers may be bound to specific
    attributes or whether a function returns true when handed a cell's
    old value or new value, or any combination of the above. An
    observer that has no conditions on its running runs whenever the
    Model updates. Observers run at most once per datapulse.

    @ivar attrib_name: (optional) The cell name this observer
        watches. Only when a cell with this name changes will the
        observer fire.

    @ivar oldvalue: A function (signature: C{f(val) -> bool}) which,
        if it returns C{True} when passed a changed cell's out-of-date
        value, allows the observer to fire.

    @ivar newvalue: A function (signature: C{f(val) -> bool}) which,
        if it returns C{True} when passed a changed cell's out-of-date
        value, allows the observer to fire.

    @ivar func: The function to run when the observer
        fires. Signature: C{f(model_instance) -> (ignored)}

    @ivar last_ran: The DP this observer last ran in.
    """
    def __init__(self, attrib, oldvalue, newvalue, func):
        self.attrib_name = attrib
        self.oldvalue = oldvalue
        self.newvalue = newvalue
        self.func = func
        self.last_ran = 0

    def run_if_applicable(self, model, attr):
        """
        Determine whether this observer should fire, and fire if
        appropriate.

        @param model: the model instance to search for matching cells
            within.

        @param attr: the attribute which "asked" this observer to run.
        """
        _debug("running observer", self.func.__name__)
        if self.last_ran == cells.cellenv.dp:   # never run twice in one DP
            _debug(self.func.__name__, "already ran in this dp")
            return
        
        if self.attrib_name:
            if isinstance(attr, Cell):
                if attr.name != self.attrib_name:
                    _debug(self.func.__name__, "wants a cell named '" +
                          self.attrib_name + "', got a cell named '" +
                          attr.name + "'")
                    return
            elif getattr(model, self.attrib_name) is not attr:
                _debug(self.func.__name__, "looked in its model for an attrib" +
                      "with its desired name; didn't match passed attr.")
                return
            
        if self.newvalue:
            if isinstance(attr, Cell):
                if not self.newvalue(attr.value):
                    _debug(self.func.__name__,
                          "function didn't match cell's new value")
                    return
            else:
                if not self.newvalue(attr):
                    _debug(self.func.__name__, "function didn't match non-cell")
                    return

        # since this is immediately post-value change, the last_value attr
        # of the cell is still good.
        if self.oldvalue:
            if isinstance(attr, Cell):
                if not self.oldvalue(attr.last_value):
                    _debug(self.func.__name__,
                           "function didn't match old value")
                    return

        # if we're here, it passed all the tests, so
        _debug(self.func.__name__, "running")
        self.func(model)
        self.last_ran = cells.cellenv.dp
