#!/usr/bin/env python
import argparse
import sys
import blueprint_layer as BlueprintLayer
import netlist_layer as NetlistLayer

def convert(args):
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
    message = "Wrote {name} to file {filename}".format(
      name = "netlist" + (" with metadata" if not args.no_meta else ""),
      filename = args.outfile)

  elif args.netlist:
    with open(args.netlist, 'r') as net_file:
      netlist = net_file.read()

    layout = NetlistLayer.importNetlist(netlist)
    output = BlueprintLayer.exportBlueprint(layout, string=not args.entity_table)
    message = "Wrote {name} to file {filename}".format(
      name = "blueprint string" if not args.entity_table else "entity table",
      filename = args.outfile)

  else:
    parser.print_help()

  if output:
    with open(args.outfile, 'w') as out_file:
      out_file.write(output)
    print(message)

if __name__=="__main__":
  parser = argparse.ArgumentParser(description="Translate between blueprints and netlists",
    usage="\n%(prog)s -h\
           \n%(prog)s -n NETLIST [--entities-only] -o OUTFILE\
           \n%(prog)s -b BLUEPRINT [--no-meta] -o OUTFILE")


  netlist = parser.add_argument_group("Netlist->Blueprint")
  netlist.add_argument('-n','--netlist', help="Filename of input netlist")
  netlist.add_argument('--entity-table', action="store_true", help="Output Lua entity table instead of blueprint string")

  blueprint = parser.add_argument_group("Blueprint->Netlist")
  blueprint.add_argument('-b','--blueprint', help="Filename of input blueprint string or Lua entity table")
  blueprint.add_argument('--no-meta', action="store_true", help="Don't include metadata (positions, wire colors, etc)")

  req = parser.add_argument_group("required arguments")
  req.add_argument('-o','--outfile', required=True, help="Filename of output file")

  if len(sys.argv)==1:
    parser.print_help()
    sys.exit(1)

  args = parser.parse_args()

  convert(args)

