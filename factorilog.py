from enum import Enum 
# pip install git+https://github.com/IlyaSkriblovsky/slpp.git@py3
from slpp import slpp as lua
import abc
import re
from collections import defaultdict

class CircuitEnt:
    """ Abstarct entity in the circuit network. May have multiple terminals. """

    __metaclass__ = abc.ABCMeta
    @classmethod
    def fromBlueprint(class_,bp_ent):
        names = {"arithmetic-combinator":ArithmeticCombinator, 
                 "decider-combinator":DeciderCombinator, 
                 "constant-combinator":ConstantCombinator,
                 "medium-electric-pole":PowerPole,
                 "small-electric-pole":PowerPole,
                 "big-electric-pole":PowerPole,
                 "substation":PowerPole}
        subclass = names[bp_ent["name"]]
        return subclass(bp_ent)

    def __init__(self, table):
        self.terminals = [Terminal(self,term_type) for term_type in self.terminal_types]
        self.name = table["name"]
        if "control_behavior" in table:
            self.behavior = table["control_behavior"]

    def toNetString(self):
        """Return human-readable netlist representation"""
        return

TermType = Enum("TerminalType","in out pass")
class Terminal:
    """ A wire connection point. Most entities have one, 
    decider/arithmetic combinators have 2.
    Types:
        in: read from circuits but don't act
        out: output to circuits
        pass: do nothing (i.e. power pole)
    """
    def __init__(self, ent, term_type):
        self.ent = ent
        self.term_type = term_type
        self.wires = set()
        self.hyperwires = set()
        
    def addWire(self, wire):
        if wire not in self.wires:
            self.wires.add(wire)

def signalToString(signal):
    """
    Return string from signal specification 
    {name="", type=""}
    """
    replacements = (("signal-everything","all"),
                    ("signal-anything","any"),
                    ("signal-each","each"),
                    # remove signal prefix from non-numeric virtuals
                    (r"signal-([^0-9].*)",r"\1")) 
    name = signal["name"]
    for pattern, repl in replacements:
        name = re.sub(pattern, repl, name)
    return name

def entInterfacesToString(interfaces):
    elements = []
    for type_ in [TermType["out"], TermType["in"], TermType["pass"]]:
        separated = ", ".join(interfaces[type_])
        if separated:
            elements.append(separated)
            if type_==TermType["out"]:
                elements.append("<=")
    return " ".join(elements)

class DeciderCombinator(CircuitEnt):
    terminal_types = [TermType["in"], TermType["out"]]

    def toNetString(self):
        cond = self.behavior["decider_conditions"]
        output_count = "@" if cond["copy_count_from_input"] else "1"
        out_signal = signalToString(cond["output_signal"])
        comparator = cond["comparator"]
        operand1 = signalToString(cond["first_signal"])
        if "second_signal" in cond:
            operand2 = signalToString(cond["second_signal"])
        else:
            operand2 = cond["constant"]

        return "{out_num} {out_sig} if {op1} {compare} {op2}".format(
            out_num = output_count, out_sig = out_signal, op1 = operand1, 
            op2 = operand2, compare = comparator)

class ArithmeticCombinator(CircuitEnt):
    terminal_types = [TermType["in"], TermType["out"]]

    def toNetString(self):
        cond = self.behavior["arithmetic_conditions"]
        out_signal = signalToString(cond["output_signal"])
        operator = cond["operation"]
        operand1 = signalToString(cond["first_signal"])
        if "second_signal" in cond:
            operand2 = signalToString(cond["second_signal"])
        else:
            operand2 = cond["constant"]

        return "{out_sig} = {op1} {operator} {op2}".format(
            out_sig = out_signal, op1 = operand1, op2 = operand2, operator = operator)

class ConstantCombinator(CircuitEnt):
    terminal_types = [TermType["out"]]

    def toNetString(self):
        filters = self.behavior["filters"]
        accum_filters = defaultdict(int)
        for filt in filters:
            accum_filters[signalToString(filt["signal"])] = filt["count"]

        return ", ".join("{} {}".format(count, name) for name,count in accum_filters.items())

class PowerPole(CircuitEnt):
    terminal_types = [TermType["pass"]]

    def toNetString(self):
        return self.name
    
WireColor = Enum("WireColor","red green")
class Wire:
    """ 
    A connection between terminals.
    In a Layout, a Wire is an edge connecting exactly two terminals and has a color.
    In a Netlist, a Wire is a hyperedge connecting 2+ terminals. Also referred to as a "hyperwire".
    """
    def __init__(self, terminals, color):
        self.terminals = frozenset(terminals)
        self.color = color
        
    def __eq__(self, other):
        return self.terminals==other.terminals and self.color==other.color
    
    def __hash__(self):
        return hash((self.terminals,self.color))
    
class Layout:
    def __init__(self):
        self.ents = set()
        self.hyperwires = set()

    @classmethod
    def fromBlueprint(class_, lua_blueprint):
        self = Layout()
        bp = lua.decode(lua_blueprint)
        ents_by_id = {} # lua form of entities indexed by id
        wires = set()

        for lua_ent in bp:
            ent = CircuitEnt.fromBlueprint(lua_ent)
            self.ents.add(ent)
            ents_by_id[lua_ent["entity_number"]] = ent
        
        for lua_ent in bp:
            for term_i,lua_terminal in lua_ent["connections"].items():
                source_term = ents_by_id[lua_ent["entity_number"]].terminals[int(term_i)-1]
                for color,lua_wires in lua_terminal.items():
                    for lua_wire in lua_wires:
                        if "circuit_id" in lua_wire:
                            terminal_i = lua_wire["circuit_id"]-1
                        else:
                            terminal_i = 0
                            
                        target_ent_id = lua_wire["entity_id"]
                        target_term = ents_by_id[target_ent_id].terminals[terminal_i]
                        wire = Wire({source_term, target_term},WireColor[color])
                        wires.add(wire)
                        source_term.addWire(wire)
                        
        return self

    def exportBlueprint(self):
        pass

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

    def getNetlist(self):
        """Get the set of hyperwires describing all connections"""
        if self.hyperwires:
            return self.hyperwires

        self.hyperwires = set()
        explored = {color:set() for color in WireColor}

        for ent in self.ents:
            for term in ent.terminals:
                for color in WireColor:
                    if term not in explored[color]:
                        terms = self.getConnectedTerminals(term, color)
                        explored[color].update(terms)
                        if len(terms)>1:
                            self.hyperwires.add(Wire(terms, color))

        # assign hyperwire refs to terminals
        for hyperwire in self.hyperwires:
            for term in hyperwire.terminals:
                term.hyperwires.add(hyperwire)

        return self.hyperwires

    def toNetString(self):
        self.getNetlist()

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

        # generate string for each entity
        net_strings = []
        for ent in self.ents:
            interface = {type_:[] for type_ in TermType}
            for term in ent.terminals:
                for hyper in term.hyperwires:
                    interface[term.term_type].append(hyper.name)

            ent_str = "{iface}: {ent}".format(
                        iface=entInterfacesToString(interface), ent=ent.toNetString())
            net_strings.append(ent_str)
        return "\n".join(net_strings)









