#!/usr/bin/env python
# Blueprint import/export

from slpp import slpp as lua
import re
import base64, gzip

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


def importBlueprint(blueprint, string = True):
  """ 
  Convert lua blueprint to Layout.
  If string==True, expect blueprint string (gzip+base64)
  Otherwise, expect lua table obtained via
  "/c serpent.line(game.player.cursor_stack.get_blueprint_entities()):
  """

  # Decode blueprint string
  if string:
    blueprint = gzip.decompress(base64.b64decode(blueprint)).decode("utf-8")

  # strip any serpent-made lua around the table
  table = re.search(r'\{.*\}', blueprint, re.DOTALL)
  if table:
    bp = lua.decode(table.group(0))
  else:
    raise RuntimeError("Could not parse blueprint")

  layout = Layout()
  ents_by_id = {} # lua form of entities indexed by id
  wires = set()

  if "entities" in bp:
    bp_entities = bp["entities"]
  else:
    bp_entities = bp

  # blueprint entities contain entity_numbers, but blueprint stringifiers remove it
  if "entity_number" not in bp_entities[0]:
    for i, bp_entity in enumerate(bp_entities, 1):
      bp_entity["entity_number"] = i 

  # Create all entities 
  for bp_ent in bp_entities:
    ent = buildEntFromBlueprint(bp_ent)

    layout.entities.add(ent)
    ents_by_id[bp_ent["entity_number"]] = ent
  
  # Create all wires
  for bp_ent in bp_entities:
    for term_i,lua_terminal in bp_ent["connections"].items():
      source_term = ents_by_id[bp_ent["entity_number"]].terminals[int(term_i)-1]
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

def exportBlueprint(layout, string = True):
  """
  Convert Layout to lua blueprint.
  If string==True, outputs a blueprint string (gzip+base64)
  Otherwise, blueprint can be used via
  "/c game.player.cursor_stack.set_blueprint_entities(blueprint)"
  """
  if not layout.flags["meta_valid"]:
      raise RuntimeError("Cannot produce blueprint without valid meta info")

  bp_entities = []
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
    bp_entities.append(ent_bp)
  bp_entities.sort(key=lambda ent_bp: ent_bp["entity_number"])
  blueprint = {"entities": bp_entities}
  lua_blueprint = lua.encode(blueprint)
  lua_blueprint = "do local _="+lua_blueprint+";return _;end"

   # Encode blueprint string
  if string:
    bp_string = base64.b64encode(gzip.compress(lua_blueprint.encode('utf-8'))).decode('utf-8')
    return bp_string
  return lua_blueprint
