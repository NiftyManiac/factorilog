from enum import Enum 
# pip install git+https://github.com/IlyaSkriblovsky/slpp.git@py3
from slpp import slpp as lua
import abc
from collections import defaultdict
import netlist_parser
import json
from grako.exceptions import SemanticError
from grako.model import ModelBuilderSemantics
from string_ops import signalToString, signalFromString

class Direction(Enum):
    N = 0
    E = 1
    S = 2
    W = 3

class CircuitEnt:
    """ Abstarct entity in the circuit network. May have multiple terminals. """

    __metaclass__ = abc.ABCMeta
    @classmethod
    def fromName(class_, name, bp_ent=None):
        """ Instantiate subclass of CircuitEnt based on name, and, optionally, blueprint """
        names = {"arithmetic-combinator":ArithmeticCombinator, 
                 "decider-combinator":DeciderCombinator, 
                 "constant-combinator":ConstantCombinator,
                 "medium-electric-pole":PowerPole,
                 "small-electric-pole":PowerPole,
                 "big-electric-pole":PowerPole,
                 "substation":PowerPole}
        subclass = names[name]
        if bp_ent:
            return subclass(name, bp_ent)
        else:
            return subclass(name)

    def __init__(self, name, table=None):
        self.terminals = [Terminal(self,type) for type,_ in sorted(self.terminal_types.items(), key=lambda pair: pair[1])]
        self.name = name
        if table:
            self.number = table["entity_number"]
            if "control_behavior" in table:
                self.behavior = table["control_behavior"]
            self.position = table["position"]
            if "direction" in table:
                self.direction = Direction(table["direction"])

    def toNetString(self, meta = False):
        """
        Return human-readable netlist representation.
        If meta==True, add metadata identifier and return (netstr, metastr)
        Otherwise, just return the netstr
        """
        interface = {type_:[] for type_ in TermType}
        for term in self.terminals:
            for hyper in term.hyperwires:
                interface[term.type].append(hyper.name)

        netstr = "{iface}: {desc}".format(
                iface=entInterfacesToString(interface), desc=self.getDescString())
        if meta:
            netstr_meta = "{netstr} \t| {num}".format(
                            netstr = netstr, num = self.number)
            return (netstr_meta, self.getMetaString())
        else:
            return netstr

    @abc.abstractmethod
    def getDescString(self):
        """Return netlist descriptor for this entity"""
        return

    def getMetaString(self):
        """Return metadata string"""
        direction = self.direction.name if hasattr(self, 'direction') else ""
        metastr = "{num} | {x} {y} {dir}".format(
                    num = self.number, x = self.position["x"],
                    y = self.position["y"], dir = direction)
        return metastr

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
    terminal_types = {TermType["in"]: 0, TermType["out"]: 1}

    def getDescString(self):
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
    terminal_types = {TermType["in"]: 0, TermType["out"]: 1}

    def getDescString(self):
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
    terminal_types = {TermType["out"]: 0}

    def getDescString(self):
        filters = self.behavior["filters"]
        accum_filters = defaultdict(int)
        for filt in filters:
            accum_filters[signalToString(filt["signal"])] = filt["count"]

        return ", ".join("{} {}".format(count, name) for name,count in accum_filters.items())

class PowerPole(CircuitEnt):
    terminal_types = {TermType["pass"]: 0}

    def getDescString(self):
        return self.name
    
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

    def getMetaString(self):
        """Get a description including all component wires"""
        subwires = {wire for term in self.terminals for wire in term.wires if wire.color==self.color}
        term_str = lambda term: "{num}{type}".format(num=term.ent.number,
                    type=term.type.name[0] if len(term.ent.terminals)>1 else "")

        wire_strings = ("-".join(map(term_str, wire.terminals)) for wire in subwires)
        return "{name} | {color} {wires}".format(name=self.name, 
                    color=self.color.name, wires=" ".join(wire_strings))


 
class NetlistSemantics(ModelBuilderSemantics):
    def decider_descriptor(self, ast):
        cond = {"comparator": ast.Comparator,
                "copy_count_from_input": ast.OutType=='@',
                "output_signal": signalFromString(ast.OutSig),
                "first_signal": signalFromString(ast.Op1)}
        try:
            cond["constant"] = int(ast.Op2)
        except ValueError:
            cond["second_signal"] = signalFromString(ast.Op2)
            
        return {"name": "decider-combinator", "behavior": {"decider_conditions": cond}}
    
    def arithmetic_descriptor(self, ast):
        cond = {"operation": ast.Operator,
                "output_signal": signalFromString(ast.OutSig),
                "first_signal": signalFromString(ast.Op1)}
        try:
            cond["constant"] = int(ast.Op2)
        except ValueError:
            cond["second_signal"] = signalFromString(ast.Op2)
            
        return {"name": "arithmetic-combinator", "behavior": {"arithmetic_conditions": cond}}
    
    def constant_descriptor(self, ast):
        filters = [{"count": sig.Value,
                     "index": i+1,
                     "signal": signalFromString(sig.Signal)} for i,sig in enumerate(ast)]
        return {"name": "constant-combinator", "behavior": {"filters": filters}}
    
    def entity_descriptor(self, ast):
        return {"name": ast}
    
    def netline(self, ast):
        #TODO fix this
        if ast.InNets and not ast.OutNets: #Passthrough
            ast["nets"] = {"pass": ast.InNets, "out": ast.OutNets}
        else:
            ast["nets"] = {"in": ast.InNets, "out": ast.OutNets}
        del ast["InNets"]
        del ast["OutNets"]
        return ast

class Layout:
    def __init__(self):
        self.ents = set()
        self.hyperwires = set()
        self.flags = {"hyperwires_named": False,
                       "meta_valid": False}

    @classmethod
    def fromBlueprint(class_, lua_blueprint):
        self = Layout()
        bp = lua.decode(lua_blueprint)
        ents_by_id = {} # lua form of entities indexed by id
        wires = set()

        for lua_ent in bp:
            ent = CircuitEnt.fromName(lua_ent["name"],lua_ent)
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
                        source_term.wires.add(wire)
                        
        self.flags["meta_valid"] = True
        return self

    def exportBlueprint(self):
        pass

    @classmethod
    def fromNetlist(class_, netlist):
        parser = netlist_parser.NetlistParser(parseinfo=False)
        ast = parser.parse(netlist, rule_name='start', semantics=NetlistSemantics())
        print(json.dumps(ast, indent=2))

        # Catalog all metadata and create hyperwires
        hyperwire_meta = {} #by name
        entity_meta = {} #by id
        entities = set()
        if ast.Metadata:
            for meta_ast in ast.Metadata:
                if "Name" in meta_ast: # hyperwire metadata
                    hyperwire_meta[meta_ast.Name] = meta_ast
                else: # entity metadata
                    entity_meta[meta_ast.ID] = meta_ast

        # Create entities and hyperwires from netspec
        metadata_labels = 0
        hyperwires = defaultdict(Wire) #by name
        for entity_ast in ast.Entities:
            # Make new entity
            ent = CircuitEnt.fromName(entity_ast.Descriptor["name"])
            entities.add(ent)

            # Populate connected hyperwires
            for term_name, term_nets in entity_ast.nets.items():
                if term_nets:
                    term = ent.terminals[ent.terminal_types[TermType[term_name]]]
                    for net_name in term_nets:
                        hyperwires[net_name].terminals |= {term}
            # Assign hyperwire names
            for name,hyperwire in hyperwires.items():
                hyperwire.name = name

            # Add info from entity metadata, if any
            ent.number = entity_ast.ID
            if entity_ast.ID:
                # assume we have metadata
                metadata_labels += 1
                try:
                    meta = entity_meta[entity_ast.ID]
                except KeyError:
                    raise SemanticError("Missing metadata for entity {}".format(entity_ast.ID))
                ent.position = {"x": meta.X, "y": meta.Y}
                if meta.Direction:
                    ent.direction = Direction[meta.Direction]
                entity_meta[entity_ast.ID]["ent"] = ent

            if "behavior" in entity_ast.Descriptor:
                ent.behavior = entity_ast.Descriptor["behavior"]

        if metadata_labels != 0 and metadata_labels != len(ast.Entities):
            raise SemanticError("Incomplete metadata provided")

        # Create all wires from metadata
        for name,meta in hyperwire_meta.items():
            hyperwires[name].color = WireColor[meta.Color]
            for wire in meta.Wires:
                terminals = set() 
                for term_ast in wire.Terminals:
                    ent = entity_meta[term_ast.ID].ent
                    if term_ast.Type:
                        terminal_i = ent.terminal_types[terminal_short[term_ast.Type]]
                    else:
                        terminal_i = 0
                    terminals.add(ent.terminals[terminal_i])
                wire = Wire(terminals, WireColor[meta.Color])
                for terminal in terminals:
                    terminal.wires.add(wire)

        self = Layout()
        self.ents = entities
        self.hyperwires = set(hyperwires.values())
        self.assignHyperwiresToTerminals()
        self.flags["meta_valid"] = meta
        self.flags["hyperwires_named"] = meta
        return self

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

    def toNetString(self, meta = False):
        self.getNetlist()

        self.nameHyperwires()

        # generate string for each entity
        strings = []
        for ent in sorted(self.ents, key=lambda e: e.number):
            strings.append(ent.toNetString(meta))

        if meta:
            net_strs, ent_meta_strs = zip(*strings)
            hyper_meta_strs = tuple(hyper.getMetaString() for hyper in self.hyperwires)
            meta_strs = ent_meta_strs + hyper_meta_strs

            max_tab = max(s.find('\t') for s in net_strs)
            return "{nets}\n||\n{metas}".format(
                    nets = "\n".join(net_strs), metas = "\n".join(meta_strs)) \
                    .expandtabs(max_tab+1)
        else:
            return "\n".join(strings)

#TODO: separate hyperwire class with mutable terminals and no hash