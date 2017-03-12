from enum import Enum 

class Direction(Enum):
  N = 0
  E = 1
  S = 2
  W = 3

class CircuitEnt:
  """ Abstract entity in the circuit network. May have multiple terminals. """

  @classmethod
  def fromName(class_, name, bp_ent=None):
    """ Instantiate subclass of CircuitEnt based on name, and, optionally, blueprint """
    for subclass in class_.__subclasses__():
      if name in subclass.names:
        return subclass(name)
    raise RuntimeError("Entity {} not supported".format(name))

  def __init__(self, name = None):
    if name:
      self.name = name
    self.terminals = [Terminal(self,type) for type,_ in sorted(self.terminal_types.items(), key=lambda pair: pair[1])]

TermType = Enum("TerminalType","in out pass")
terminal_short = {"i": TermType["in"], "o": TermType["out"], "p": TermType["pass"]}
class Terminal:
  """ A wire connection point. Most entities have one, 
  decider/arithmetic combinators have 2.
  Types:
    in: read from circuits but don't act
    out: output to circuits
    pass: do nothing (i.e. power pole)
  """
  def __init__(self, ent, type):
    self.ent = ent
    self.type = type
    self.wires = set()
    self.hyperwires = set()

class DeciderCombinator(CircuitEnt):
  names = {"decider-combinator"}
  terminal_types = {TermType["in"]: 0, TermType["out"]: 1}

class ArithmeticCombinator(CircuitEnt):
  names = {"arithmetic-combinator"}
  terminal_types = {TermType["in"]: 0, TermType["out"]: 1}

class ConstantCombinator(CircuitEnt):
  names = {"constant-combinator"}
  terminal_types = {TermType["out"]: 0}

class PowerPole(CircuitEnt):
  names = {"small electric pole", "medium-electric-pole", "big-electric-pole",
          "substation"}
  terminal_types = {TermType["pass"]: 0}
  
WireColor = Enum("WireColor","red green")
class Wire:
  """ 
  A connection between terminals.
  In a Layout, a Wire is an edge connecting exactly two terminals and has a color.
  In a Netlist, a Wire is a hyperedge connecting 2+ terminals. Also referred to as a "hyperwire".
  """
  def __init__(self, terminals={}, color=None):
    self.terminals = frozenset(terminals)
    self.color = color
    self.name = None
    
  def __eq__(self, other):
    return self.terminals==other.terminals and self.color==other.color
  
  def __hash__(self):
    return hash((self.terminals,self.color))

class Layout:
  def __init__(self):
    self.entities = set()
    self.hyperwires = set()
    self.flags = {"hyperwires_named": False,
             "meta_valid": False}
    self.meta = {}

  def getConnectedTerminals(self, terminal, color):
    """
    Traverse the graph to get all terminals connected by one wire.
    Node expansion order is undefined and doesn't matter.t
    """
    frontier = {terminal}
    explored = set()
    while frontier:
      term = frontier.pop()
      explored.add(term)
      for wire in term.wires:
        if wire.color==color:
          frontier.update(wire.terminals)
      frontier -= explored
    return explored

  def assignHyperwiresToTerminals(self):
    # assign hyperwire refs to terminals
    for hyperwire in self.hyperwires:
      for term in hyperwire.terminals:
        term.hyperwires.add(hyperwire)

  def getHyperwires(self):
    """Get the set of hyperwires describing all connections"""
    if self.hyperwires:
      return self.hyperwires

    self.hyperwires = set()
    explored = {color:set() for color in WireColor}

    for ent in self.entities:
      for term in ent.terminals:
        for color in WireColor:
          if term not in explored[color]:
            terms = self.getConnectedTerminals(term, color)
            explored[color].update(terms)
            if len(terms)>1:
              self.hyperwires.add(Wire(terms, color))

    self.assignHyperwiresToTerminals()

    return self.hyperwires

  def nameHyperwires(self):
    if self.flags["hyperwires_named"]:
      return

    # name the hyperwires
    name = "a"
    # get next lowercase alphabetical string
    def next_str(name):
      def roll_str(name):
        if len(name)==0:
          return "-"
        elif name[-1]!='z':
          return name[:-1] + chr(ord(name[-1])+1)
        else:
          return roll_str(name[:-1])+'a'
      new = roll_str(name)
      return new if new[0]!='-' else new[1:]+'a'

    for hyperwire in self.hyperwires:
      hyperwire.name = name
      name = next_str(name)

    self.flags["hyperwires_named"] = True

#TODO: separate hyperwire class with mutable terminals and no hash