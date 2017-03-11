import re

signal_replacements = (("signal-everything","all"),
                        ("signal-anything","any"),
                        ("signal-each","each"))

# Extract all signals with lua:
"""
map = {};
    
for _,v in pairs(game.virtual_signal_prototypes) do table.insert(map,{name=v.name,type="virtual"}) end;
for _,f in pairs(game.fluid_prototypes) do table.insert(map,{name=f.name,type="fluid"}) end;
for _,i in pairs(game.item_prototypes)  do if not i.has_flag("hidden") then table.insert(map,{name=i.name,type="item"}) end end;

game.write_file("signals.lua", serpent.line(map,{indent=" ",comment=false}), false)
"""
from slpp import slpp as lua

def readAllSignals():
    with open("signals.lua",'r') as f:
        signal_table = lua.decode(f.read())
    return {sig["name"]: sig["type"] for sig in signal_table}

def signalToString(signal):
    """
    Return string from signal specification 
    {name="", type=""}
    """
    
    name = signal["name"]
    # remove signal prefix from non-numeric virtuals
    replacements = signal_replacements + ((r"signal-([^0-9].*)",r"\1"),)
    for pattern, repl in replacements:
        name = re.sub(pattern, repl, name)
    return name

def signalFromString(signal_str):
    for repl, pattern in signal_replacements:
        signal_str = re.sub(pattern, repl, signal_str)
    if signal_str not in signal_types:
        signal_str = "signal-"+signal_str

    return {"type": signal_types[signal_str], "name": signal_str}

signal_types = readAllSignals()