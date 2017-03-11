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

Layout:

```
cond <= A: 1 black if green>2		| 1
case1 <= A: red=green+0				| 2
case2 <= 5 red						| 3
B <= cond, case1: @ red if black=1	| 4
B <= cond, case2: @ all if black=0  | 5

||
1 | pos:(x,y), rot=N, wires={"in":}
case1 | color:green, (2i-3o, )
```


line                    ::= [netlist '<='] [netlist] [netlist] ':' descriptor
netlist                 ::= Name {',' Name}
descriptor              ::= Factorio_Name | arithmetic_descriptor | decider_descriptor | constant_descriptor
arithmetic_descriptor   ::= signal '=' signal operator channel
decider_descriptor      ::= out_type signal '?' signal comparator channel
constant_descriptor     ::= constant signal {',' constant signal}
channel                 ::= signal | constant
signal                  ::= factorio_signal | 'each' | 'any' | 'all'
factorio_signal         ::= numeric_signal | alpha_signal | other_signal
numeric_signal          ::= ['signal-'] digit
alpha_signal            ::= ['signal-'] upper_letter
other_signal            ::= Any Other Factorio Signal (e.g., 'copper-ore')
operator                ::= '+' | '-' | '/' | '*'
constant                ::= Int32
out_type                ::= '1' | '@'
comparator              ::= '>' | '=' | '<'
upper_letter            ::= 'A' | 'B' | ... | 'Z'
lower_letter            ::= 'a' | 'b' | ... | 'z'
digit                   ::= '0' | '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9'
 
Name can be any combination of ascii letters a-z (upper and lower case), numbers, and underscore (_)