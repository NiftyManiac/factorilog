## Netlist Language Specification

Grammar:
```
line 					::= [output_nets "<="] [input_nets] [passthrough_nets] ":" descriptor
output_nets 			::= nets
input_nets 				::= nets
passthrough_nets		::= nets
nets 					::= net (", " net)*
net 					::= [A-Za-z0-9_]+
descriptor 				::= (entity_name | arithmetic_descriptor | decider_descriptor | constant descriptor)
arithmetic_descriptor	::= signal "=" signal operator (signal | constant)
decider_descriptor		::= out_type signal "?" signal comparator (signal | constant)
constant_descriptor		::= (constant signal)+
signal					::= (<Factorio signal name> | [A-Z] | "each" | "any" | "all")
operator				::= ("+" | "-" | "/" | "*")
constant 				::= int32
out_type				::= ("1" | "@")
comparator				::= (">" | "=" | "<")
```
### Examples:

Behavior:
```
if(A.green > 2)
	B.red = A.green
else
	B.red = 5
end
```

Netlist:
```
cond <= A: 1 black if green>2
case1 <= A: red=green+0
case2 <= 5 red
B <= cond, case1: @ red if black=1
B <= cond, case2: @ all if black=0 
```
