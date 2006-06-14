"""
Cell

Cell, and subclasses of Cell.
TODO: More here.
"""

DEBUG = False

def debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "        cell > ")
    if DEBUG:
        print " ".join(msgs)


class CellException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class RuleCellSetError(CellException):
    pass

class EphemeralCellUnboundError(CellException):
    pass

class ValueCellRunError(CellException):
    pass
        
        
class Cell(object):
    """The base Cell class. Does everything interesting.

    TODO: Write a better description
    """
    def __init__(self, owner, name, function=lambda s,p: None, value=None,
                 observers=[], type="default"):
        debug("running cell init for", name, "with", str(len(observers)),
              "observers, value=", str(value))
        self.name = name
        self.function = function
        self.value = value
        self.observers = observers
        self.owner = owner
        
        self.called_by = set([])     # the cells which call this cell
        self.calls = set([])         # the cells which this cell calls

        self.time = None
        self.bound = False
        self.dirty = True
        self.value_set = False

        if value:
            self.bound = True
            self.value_set = True
            self.dirty = False
            self.run_observers(None, False)

    def get(self):
        """Special getter for Cell attributes.

        If the value's been set, return that. If there's a memoized
        value, return it that. If there isn't, this is the first time
        this cell's been run. So, run it, memoize the calc'd value,
        and return that.
        """
        debug("Getting", self.name)

        # first, determine if this cell needs a recalculation
        if not self.bound :
            debug(self.name, "has not been bound; running.")
            self.run()

        if self.dirty and not self.value_set:
            debug(self.name, "dirty and unset")
            self.run()

        debug(self.name, "is", str(self.value))

        if self.owner._curr:               # if there's a calling cell,
            # notify calling cell that it depends on this cell
            self.owner._curr.calls.add(self)
            # and add the calling cell to the called-by list
            self.called_by.add(self.owner._curr)

        return self.value

    def set(self, value):
        """Special setter for Cell attributes.

        TODO: Describe my behavior
        """
        self.value_set = True
        if self.value != value:
            self.owner._time += 1
            self.time = self.owner._time

            debug("Owner time is:", str(self.owner._time))
            debug("Setting", self.name, "to", str(value))
            debug(self.name, "calls", \
                  str([ cell.name for cell in self.calls]))
            debug(self.name, "called by", \
                  str([ cell.name for cell in self.called_by]))

            oldval = self.value         # save for observers
            oldbound = self.bound       # ditto
            self.bound = True
            self.value = value
            
            self.run_observers(oldval, oldbound)
            self.equalize()

    def run_observers(self, oldval, oldbound):
        debug("Number of observers:", str(len(self.observers)))
        for observer in self.observers:
            debug("Running observer", str(observer))
            observer(self.owner, self.value, oldval, oldbound)

    def run(self):
        """Runs the value-generating function & re-equalizes the subgraph"""
        # update to this time quantum, then run the function
        debug("Owner time is:", str(self.owner._time))

        self.time = self.owner._time        
        oldval = self.value
        oldbound = self.bound
        
        debug(self.name, "time is:", str(self.owner._time))

        # set this cell as the currently-running cell
        if self.owner._curr:
            debug("Currently-running cell was", str(self.owner._curr.name))
        else:
            debug("No currently-running cell")
        oldrunner = self.owner._curr
        self.owner._curr = self
        debug("Currently-running cell is now", str(self.name))

        # note the function is passed the *owner* as the first arg, 
        # mimicking standard Foo.bar dispatch        
        self.value = self.function(self.owner, self.value)
        self.bound = True
        self.dirty = False
        
        # only rerun dependents & observers if the value changed
        if oldval != self.value:
            self.run_observers(oldval, oldbound)
            self.equalize()

        # now that the subgraph is equalized, restore the old running cell
        self.owner._curr = oldrunner
            
        if not self.owner._curr:
            debug("No currently-running cell")
        else:
            debug("Currently-running cell back to",
                  str(self.owner._curr.name))

    def equalize(self):
        """Brings the subgraph of dependents to equlibrium."""
        debug("Equalizing", self.name)
        debug(self.name, "called by",
              str([ cell.name for cell in self.called_by ]))

        # first, mark all to-be-run cells as dirty (to make sure recalcs
        # among dependent dependents get run in the right order)
        for dependent in self.called_by:
            dependent.dirty = True
        
        # then, re-run the cells which call this cell
        for dependent in self.called_by:
            # only run if the dependent hasn't been run in this quantum
            debug("Dependent of", self.name, ":", dependent.name, "at",
                  str(dependent.time))
            if dependent.time < self.time:
                debug("Dependent of", self.name, ":", dependent.name,
                      "re-run")
                # catch EphemeralCellUnboundError exceptions
                try:
                    dependent.run()
                except EphemeralCellUnboundError, e:
                    debug(dependent.name, "hit an unbound ephemeral")
        # the subtree is now at equilibrium.


class RuleCell(Cell):
    """A cell which is determined by a function."""
    def set(self, value):
        raise RuleCellSetError("cannot set a rule cell")

class ValueCell(Cell):
    def run(self):
        raise ValueCellRunError("attempt to run a value cell")
    
class EphemeralCell(Cell):
    def get(self):
        debug("get for", self.name, "(ephemeral)")
        if not self.bound:
            debug("ephemeral", self.name, "unbound")
            if self.owner._curr:               # if there's a calling cell,
                # notify calling cell that it depends on this cell
                self.owner._curr.calls.add(self)
                # and add the calling cell to the called-by list
                self.called_by.add(self.owner._curr)

            raise EphemeralCellUnboundError("attempt to read from unbound cell")
        else:
            return Cell.get(self)
        
    def set(self, value):
        """set, equalize, then unset"""
        debug("ephemeral cell", self.name, "setting")
        Cell.set(self, value)
        debug("ephemeral cell", self.name, "equalized, unbinding")
        self.bound = False

    def run(self):
        """run, equalize, then unset"""
        Cell.run(self)
        self.bound = False