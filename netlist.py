#!/usr/bin/env python
import argparse
import blueprint_layer as BlueprintLayer
import netlist_layer as NetlistLayer

parser = argparse.ArgumentParser(description="Translate between blueprints and netlists",
  usage="\n%(prog)s -h\
         \n%(prog)s -n NETLIST [--raw-blueprint] -o OUTFILE\
         \n%(prog)s -b BLUEPRINT [--no-meta] -o OUTFILE")

netlist = parser.add_argument_group("Netlist->Blueprint")
netlist.add_argument('-n','--netlist', help="Filename of input netlist")
netlist.add_argument('--raw-blueprint', action="store_true", help="Output Lua blueprint instead of blueprint string")

blueprint = parser.add_argument_group("Blueprint->Netlist")
blueprint.add_argument('-b','--blueprint', help="Filename of input blueprint string or Lua blueprint spec")
blueprint.add_argument('--no-meta', action="store_true", help="Don't include metadata")

req = parser.add_argument_group("required arguments")
req.add_argument('-o','--outfile', required=True, help="Filename of output file")

args = parser.parse_args()
print(args)

output = None
if args.blueprint and args.netlist:
  parser.print_help()

elif args.blueprint:
  with open(args.blueprint, 'r') as bp_file:
    bp = bp_file.read()

  try:
    layout = BlueprintLayer.importBlueprint(bp, string=True)
  except OSError:
    layout = BlueprintLayer.importBlueprint(bp, string=False)

  output = NetlistLayer.exportNetlist(layout, meta=not args.no_meta)

elif args.netlist:
  with open(args.netlist, 'r') as net_file:
    netlist = net_file.read()

  layout = NetlistLayer.importNetlist(netlist)
  output = BlueprintLayer.exportBlueprint(layout, string=not args.raw_blueprint)

else:
  parser.print_help()

if output:
  with open(args.outfile, 'w') as out_file:
    out_file.write(output)


