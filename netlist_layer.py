#!/usr/bin/env python
# Netlist import/export

from grako.exceptions import SemanticError
from grako.model import ModelBuilderSemantics
from collections import defaultdict

from factorilog import *
from string_ops import signalToString, signalFromString
from netlist_parser import NetlistParser

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

def importNetlist(netlist):
  """ 
  Parse netlist string to produce a Layout.
  """
  parser = NetlistParser(parseinfo=False)
  ast = parser.parse(netlist, rule_name='start', semantics=NetlistSemantics())

  layout = Layout()

  # Catalog all metadata and create hyperwires
  hyperwire_meta = {} #by name
  entity_meta = {} #by id
  entities = set()
  # TODO cleanup here
  if ast.Metadata:
    for meta_ast in ast.Metadata:
      if "WireName" in meta_ast: # hyperwire metadata
        hyperwire_meta[meta_ast.WireName] = meta_ast
      elif "ID" in meta_ast: # entity metadata
        entity_meta[meta_ast.ID] = meta_ast
      elif "Name" in meta_ast:
        layout.meta["name"] = meta_ast.Name
      elif "Names" in meta_ast:
        layout.meta["icons"] = [signalFromString(name) for name in meta_ast.Names]

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

  layout.entities = entities
  layout.hyperwires = set(hyperwires.values())
  layout.assignHyperwiresToTerminals()
  layout.flags["meta_valid"] = meta
  layout.flags["hyperwires_named"] = meta
  return layout

def getDescString(ent):
  """ Get description string for circuit entity """
  if isinstance(ent, DeciderCombinator):
    cond = ent.behavior["decider_conditions"]
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

  elif isinstance(ent, ArithmeticCombinator):
    cond = ent.behavior["arithmetic_conditions"]
    out_signal = signalToString(cond["output_signal"])
    operator = cond["operation"]
    operand1 = signalToString(cond["first_signal"])
    if "second_signal" in cond:
      operand2 = signalToString(cond["second_signal"])
    else:
      operand2 = cond["constant"]

    return "{out_sig} = {op1} {operator} {op2}".format(
      out_sig = out_signal, op1 = operand1, op2 = operand2, operator = operator)

  elif isinstance(ent, ConstantCombinator):
    filters = ent.behavior["filters"]
    accum_filters = defaultdict(int)
    for filt in filters:
      accum_filters[signalToString(filt["signal"])] = filt["count"]

    return ", ".join("{} {}".format(count, name) for name,count in accum_filters.items())

  else:
    return ent.name


def getEntityMetaString(ent):
  """Return metadata string"""
  direction = ent.direction.name if hasattr(ent, 'direction') else ""
  metastr = "{num} | {x} {y} {dir}".format(
        num = ent.number, x = ent.position["x"],
        y = ent.position["y"], dir = direction)
  return metastr

def getWireMetaString(wire):
  """Get a description including all component wires"""
  # Tracer()()
  subwires = {subwire for term in wire.terminals for subwire in term.wires if subwire.color==wire.color}
  term_str = lambda term: "{num}{type}".format(num=term.ent.number,
        type=term.type.name[0] if len(term.ent.terminals)>1 else "")

  wire_strings = ("-".join(map(term_str, wire.terminals)) for wire in subwires)
  return "{name} | {color} {wires}".format(name=wire.name, 
        color=wire.color.name, wires=" ".join(wire_strings))

def getLayoutMetaString(layout):
  meta_strs = []
  if "name" in layout.meta:
    meta_strs.append("name || "+layout.meta["name"])
  if "icons" in layout.meta:
    meta_strs.append("icons || "+" ".join(
      signalToString(sig) for sig in layout.meta["icons"]))
  return "\n".join(meta_strs)

def entInterfacesToString(interfaces):
  elements = []
  for type_ in [TermType["out"], TermType["in"], TermType["pass"]]:
    separated = ", ".join(interfaces[type_])
    if separated:
      elements.append(separated)
      if type_==TermType["out"]:
        elements.append("<=")
  return " ".join(elements)

def getNetString(ent, meta = False):
  """
  Return primary netlist representation of entity.
  If meta==True, add metadata identifier and return (netstr, metastr)
  Otherwise, just return the netstr
  """
  interface = {type_:[] for type_ in TermType}
  for term in ent.terminals:
    for hyper in term.hyperwires:
      interface[term.type].append(hyper.name)

  netstr = "{iface}: {desc}".format(
      iface=entInterfacesToString(interface), desc=getDescString(ent))
  if meta:
    netstr_meta = "{netstr} \t| {num}".format(
            netstr = netstr, num = ent.number)
    return (netstr_meta, getEntityMetaString(ent))
  else:
    return netstr

def exportNetlist(layout, meta = False):
  layout.getHyperwires()

  layout.nameHyperwires()

  # generate string for each entity
  strings = []
  for ent in sorted(layout.entities, key=lambda e: e.number):
    strings.append(getNetString(ent, meta))

  if meta:
    net_strs, ent_meta_strs = zip(*strings)
    hyper_meta_strs = tuple(getWireMetaString(hyper) for hyper in layout.hyperwires)
    global_meta_str = getLayoutMetaString(layout)
    meta_strs = ent_meta_strs + hyper_meta_strs
    if global_meta_str:
      meta_strs = (global_meta_str,) + meta_strs

    max_tab = max(s.find('\t') for s in net_strs)
    return "{nets}\n||\n{metas}".format(
        nets = "\n".join(net_strs), metas = "\n".join(meta_strs)) \
        .expandtabs(max_tab+1)
  else:
    return "\n".join(strings)