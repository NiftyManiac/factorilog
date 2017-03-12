## Factorio HDL and Netlist Project

### Install dependencies:
```
pip install -r requirements.txt
```

### Usage:
```
./netlist.py -h
```

## Current state:

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

## Netlist examples:
### Bare netlist
```
c: medium-electric-pole        
e <= c: 1 black if green > 2   
a <= c: red = green + 0        
d <= b, e: @ all if black = 0  
d <= a, e: @ red if black = 1  
d: medium-electric-pole        
b <=: 5 red                    
```

### Netlist with metadata:
```
c: medium-electric-pole        | 1
e <= c: 1 black if green > 2   | 2
a <= c: red = green + 0        | 3
d <= b, e: @ all if black = 0  | 4
d <= a, e: @ red if black = 1  | 5
d: medium-electric-pole        | 6
b <=: 5 red                    | 7
||
name || Sample
icons || decider-combinator
1 | -5 -2 
2 | -2.5 -2 S
3 | -2.5 0 S
4 | 0.5 0 S
5 | 0.5 -1 S
6 | 4 -1 
7 | -3 1 S
a | red 5i-3o
b | red 4i-7
c | red 3i-1 2i-1
d | green 5o-6 4o-6
e | green 2o-5i 4i-5i
```