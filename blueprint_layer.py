#!/usr/bin/env python
# Blueprint import/export

from slpp import slpp as lua

from factorilog import Layout, Wire, WireColor, CircuitEnt, Direction

from collections import defaultdict

def buildEntFromBlueprint(ent_bp):
  ent = CircuitEnt.fromName(ent_bp["name"])

  ent.name = ent_bp["name"]
  ent.number = ent_bp["entity_number"]
  if "control_behavior" in ent_bp:
    ent.behavior = ent_bp["control_behavior"]
  ent.position = ent_bp["position"]
  if "direction" in ent_bp:
    ent.direction = Direction(ent_bp["direction"])
  return ent


def importBlueprint(lua_blueprint):
  """ 
  Convert lua blueprint to Layout.
  Blueprint is obtained via 
  "/c serpent.line(game.player.cursor_stack.get_blueprint_entities()):
  """
  layout = Layout()
  bp = lua.decode(lua_blueprint)
  ents_by_id = {} # lua form of entities indexed by id
  wires = set()

  for lua_ent in bp:
    ent = buildEntFromBlueprint(lua_ent)

    layout.entities.add(ent)
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
          
  layout.flags["meta_valid"] = True
  return layout

def exportBlueprint(layout):
  """
  Convert Layout to lua blueprint.
  Blueprint can be used via
  "/c game.player.cursor_stack.set_blueprint_entities(blueprint)"
  """
  if not layout.flags["meta_valid"]:
      raise RuntimeError("Cannot produce blueprint without valid meta info")

  blueprint = []
  for ent in layout.entities:
    ent_bp = {}
    ent_bp["connections"] = {}
    for i,term in enumerate(ent.terminals):
      bp_term = str(i+1)
      bp_wires_by_color = defaultdict(list)
      for wire in term.wires:
        other_term = list(wire.terminals - {term})[0]
        other_ent = other_term.ent
        circuit_id = other_ent.terminal_types[other_term.type]+1

        bp_wires_by_color[wire.color.name].append(
          {"circuit_id": circuit_id, "entity_id": other_ent.number})
      
      ent_bp["connections"][bp_term] = bp_wires_by_color
      ent_bp["entity_number"] = ent.number
      ent_bp["name"] = ent.name
      ent_bp["position"] = ent.position
      if hasattr(ent, "direction"):
        ent_bp["direction"] = ent.direction.value
      if hasattr(ent, "behavior"):
        ent_bp["control_behavior"] = ent.behavior
    blueprint.append(ent_bp)
  blueprint.sort(key=lambda ent_bp: ent_bp["entity_number"])
  return lua.encode(blueprint)
