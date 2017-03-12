## Factorio HDL Project

### Install dependencies:
```
pip install -r requirements.txt
```

### Usage:
```
./netlist.py -h
```

###Complete:
* Supported entities:
  * Combinators
  * Power poles/substations
* Blueprint string import and export
* Entity table import and export (get/set_blueprint_entities())
* Netlist import and export
* Blueprint->Netlist (abstraction)
* Netlist with metadata->Blueprint

### Todo:

* Bare netlist->Blueprint (auto layout)
* HDL implementation
* HDL compilation
