# Traduccion-Dirigida-por-Sintaxis

Parser LL(1) con EDTS en Python que evalúa expresiones aritméticas (`+`, `-`, `*`, `/`, paréntesis).  
Realiza análisis léxico, sintáctico, construye AST, gestiona tabla de símbolos y evalúa en una sola pasada.

---

## Solución en Python

### Código Principal (`edts_core.py`)

```python
# Gramática LL(1)
PRODS = {
    "E":  [["T", "E'"]],
    "E'": [["+", "T", "E'"], ["-", "T", "E'"], ["ε"]],
    "T":  [["F", "T'"]],
    "T'": [["*", "F", "T'"], ["/", "F", "T'"], ["ε"]],
    "F":  [["(", "E", ")"], ["num"], ["id"]],
}

# Lexer: tokeniza números, identificadores, operadores
# Parser: análisis LL(1) con atributos sintetizados/heredados
# AST: árbol decorado con valores
# TablaSimbolos: gestión de variables
```

### Interfaz CLI (`app.py`)

```python
def main():
    expr = input("Expresión: ").strip()
    
    # Calcula FIRST/FOLLOW/PREDICT
    first  = compute_first(PRODS)
    follow = compute_follow(PRODS, START, first)
    predict = compute_predict(PRODS, first, follow)
    
    # Parse y evaluación
    toks = Lexer(expr).tokens()
    ast, value, ts = Parser(toks).parse()
    
    # Genera archivos en ./out
    write_txt("out/grammar.txt", dump_grammar() + dump_sets(...))
    write_txt("out/ast.txt", ast.pretty())
    write_txt("out/symbols.txt", ts.to_text())
    write_txt("out/eval.txt", f"{expr} = {value}")
    
    print(f"Valor = {value}")
```

---

## 1. Gramática LL(1)

```
E  → T E'
E' → + T E' | - T E' | ε
T  → F T'
T' → * F T' | / F T' | ε
F  → ( E ) | num | id
```

- Sin recursión izquierda → parsing descendente
- Precedencia: `*` `/` > `+` `-`
- Asociatividad izquierda

---

## 2. Análisis Léxico (Lexer)

Convierte texto en tokens:

```python
class Lexer:
    def tokens(self) -> List[Token]:
        # Reconoce: operadores (+,-,*,/,(,))
        #           números (42, 3.14)
        #           identificadores (x, var_1)
        #           EOF ($)
```

**Ejemplo:**
```python
Lexer("x + 2 * 3").tokens()
# [Token('id','x'), Token('+'), Token('num','2'), Token('*'), Token('num','3'), Token('

---

## 3. Conjuntos FIRST, FOLLOW y PREDICT

Garantizan que la gramática es LL(1) (sin ambigüedades).

```python
FIRST(E)  = {(, num, id}      # Símbolos que inician E
FIRST(E') = {+, -, ε}         # Símbolos que inician E'

FOLLOW(E)  = {), $}           # Símbolos después de E
FOLLOW(T') = {+, -, ), $}     # Símbolos después de T'

PREDICT(E' → + T E') = {+}    # Token '+' elige esta producción
PREDICT(E' → ε)      = {), $} # Tokens ')' o '

---

## 4. AST y Tabla de Símbolos

**AST (Árbol de Sintaxis Abstracta):** Estructura jerárquica de la expresión.

```python
@dataclass
class AST:
    tag: str                    # 'add', 'mul', 'num', 'id'
    value: Optional[float]      # Valor evaluado
    name: Optional[str]         # Nombre (variables)
    children: List["AST"]       # Hijos del nodo
```

**Ejemplo:** `2 + 3 * 4`
```
add(val=14.0)
  num(val=2.0)
  mul(val=12.0)
    num(val=3.0)
    num(val=4.0)
```

**Tabla de Símbolos:** Gestiona variables.

```python
class TablaSimbolos:
    def tocar(nombre, pos):     # Registra uso
    def set_valor(nombre, val): # Asigna valor
    def obtener(nombre):        # Recupera valor
```

---

## 5. Parser LL(1) con EDTS

Parser con **atributos sintetizados** (↑) y **heredados** (↓).

### E → T E'
```python
def E(self):
    nT, vT = self.T()          # Parse T
    return self.Ep(nT, vT)     # Pasa heredados → E'
```

### E' → + T E' | - T E' | ε
```python
def Ep(self, inh_node, inh_val):
    if self.la().typ == TT_PLUS:
        self.eat(TT_PLUS)
        nT, vT = self.T()
        node = AST("add", children=[inh_node, nT])  # Construye AST
        return self.Ep(node, inh_val + vT)          # Evalúa y recursión
    
    if self.la().typ == TT_MINUS:
        # Similar...
    
    return inh_node, inh_val  # Producción ε
```

### F → ( E ) | num | id
```python
def F(self):
    if self.la().typ == TT_NUM:
        tok = self.eat(TT_NUM)
        return AST("num", value=float(tok.lex)), float(tok.lex)
    
    if self.la().typ == TT_ID:
        tok = self.eat(TT_ID)
        if not self.ts.obtener(tok.lex):
            val = float(input(f"Valor para {tok.lex}: "))  # Input interactivo
            self.ts.set_valor(tok.lex, val)
        return AST("id", name=tok.lex, value=...), ...
```

**Flujo:**
1. `T.val` → `E'.inh_val` (heredado ↓)
2. Construye `add(E'.inh_nodo, T.nodo)`
3. Calcula `E'.inh_val + T.val`
4. Pasa a siguiente `E'` recursivamente

---

## 6. Gramática de Atributos (EDTS)

```
E  → T E'  { E'.inh_val=T.val; E'.inh_nodo=T.nodo; E.val=E'.val; E.nodo=E'.nodo }
E' → + T E'₁ { tmp=E'.inh_val+T.val; n=add(E'.inh_nodo,T.nodo); 
               E'₁.inh_val=tmp; E'₁.inh_nodo=n; E'.val=E'₁.val }
E' → ε     { E'.val=E'.inh_val; E'.nodo=E'.inh_nodo }
T  → F T'  { T'.inh_val=F.val; T'.inh_nodo=F.nodo; T.val=T'.val }
T' → * F T'₁ { tmp=T'.inh_val*F.val; n=mul(T'.inh_nodo,F.nodo); ... }
F  → num   { F.val=float(num.lex); F.nodo=Num(num.lex) }
F  → id    { si tabla[id] None → pedir; F.val=tabla[id] }
```

---

## Cómo ejecutar

```bash
python3 app.py
```

**Ejemplo:**
```
Expresión: x + 2 * 3
Valor para x: 5
Valor = 11.0

AST:
add(val=11.0)
  id(name=x, val=5.0)
  mul(val=6.0)
    num(val=2.0)
    num(val=3.0)

== Tabla de símbolos ==
x    tipo=num valor=5.0 ocurrencias=[(1,1)]

Archivos generados en ./out
```

**Desde stdin:**
```bash
echo "2 + 3 * 4" | python3 app.py  # Resultado: 14.0
echo "(2 + 3) * 4" | python3 app.py  # Resultado: 20.0
```

---

## Archivos Generados (`./out`)

| Archivo | Contenido |
|---------|-----------|
| `grammar.txt` | Gramática + conjuntos FIRST/FOLLOW/PREDICT |
| `attrib_grammar.txt` | Gramática con atributos y acciones |
| `etds.txt` | Esquema de traducción dirigida |
| `ast.txt` | AST decorado con valores |
| `symbols.txt` | Tabla de símbolos (variables) |
| `eval.txt` | Resultado de la evaluación |

---

## Casos de Prueba

```bash
2 + 3           → 5.0
2 + 3 * 4       → 14.0  (precedencia correcta)
(2 + 3) * 4     → 20.0  (paréntesis)
x * (y + 3)     → evalúa con input interactivo
```

---

## Conceptos Implementados

- **EDTS:** Acciones semánticas durante parsing (no después)
- **Atributos sintetizados/heredados:** Flujo bidireccional de información
- **Eliminación recursión izquierda:** `E → E + T` → `E → T E'`
- **Parser LL(1):** 1 símbolo lookahead, decisión determinista, O(n)
- **FIRST/FOLLOW/PREDICT:** Garantizan gramática LL(1)

---

## Manejo de Errores

```python
# Token inesperado
SyntaxError(f"Esperaba '{typ}' llegó '{t.typ}' ({line},{col})")

# División por cero
ZeroDivisionError("División por cero")

# Variable no definida → input interactivo
input(f"Valor para {var}: ")
```

---

**Autor:** [Tu Nombre]  
**Materia:** Teoría de Compiladores  
**Fecha:** 2025)]
```

---

## 3. Conjuntos FIRST, FOLLOW y PREDICT

Estos conjuntos garantizan que la gramática es **LL(1)** (sin ambigüedades).

### FIRST(α) - Primeros símbolos posibles

```python
def compute_first(prods: Dict[str, List[List[str]]]) -> Dict[str,set]:
    first: Dict[str,set] = {A:set() for A in prods}
    # Algoritmo iterativo de punto fijo
    changed = True
    while changed:
        changed = False
        for A, alts in prods.items():
            for rhs in alts:
                # Calcula FIRST para cada producción
                ...
    return first
```

**Resultado:**
```
FIRST(E)  = {(, num, id}
FIRST(E') = {+, -, ε}
FIRST(T)  = {(, num, id}
FIRST(T') = {*, /, ε}
FIRST(F)  = {(, num, id}
```

### FOLLOW(A) - Símbolos que pueden seguir a A

```python
def compute_follow(prods, start, first) -> Dict[str,set]:
    follow: Dict[str,set] = {A:set() for A in prods}
    follow[start].add(TT_EOF)  # $ sigue al símbolo inicial
    # Algoritmo iterativo
    ...
    return follow
```

**Resultado:**
```
FOLLOW(E)  = {), $}
FOLLOW(E') = {), $}
FOLLOW(T)  = {+, -, ), $}
FOLLOW(T') = {+, -, ), $}
FOLLOW(F)  = {*, /, +, -, ), $}
```

### PREDICT(A → α) - Símbolos que predicen una producción

```python
def compute_predict(prods, first, follow):
    pred = {}
    for A, alts in prods.items():
        for rhs in alts:
            if rhs == [EPS]:
                pred[(A,tuple(rhs))] = follow[A]
            else:
                # Calcula FIRST(α) y añade FOLLOW(A) si α es nullable
                ...
    return pred
```

**Resultado:**
```
PREDICT(E → T E')     = {(, num, id}
PREDICT(E' → + T E')  = {+}
PREDICT(E' → - T E')  = {-}
PREDICT(E' → ε)       = {), $}
PREDICT(T → F T')     = {(, num, id}
PREDICT(T' → * F T')  = {*}
PREDICT(T' → / F T')  = {/}
PREDICT(T' → ε)       = {+, -, ), $}
PREDICT(F → ( E ))    = {(}
PREDICT(F → num)      = {num}
PREDICT(F → id)       = {id}
```

**Propiedad LL(1):** Para cada no terminal `A`, los conjuntos PREDICT de sus producciones son **disjuntos** (no se superponen).

---

## 4. Árbol de Sintaxis Abstracta (AST)

Representa la estructura jerárquica de la expresión.

```python
@dataclass
class AST:
    tag: str                          # Tipo: 'add', 'mul', 'num', 'id'
    value: Optional[float] = None     # Valor numérico (sintetizado)
    name: Optional[str] = None        # Nombre de variable
    children: List["AST"] = field(default_factory=list)
    pos: Optional[Tuple[int,int]] = None  # (línea, columna)
    
    def pretty(self, indent=0) -> str:
        # Impresión indentada del árbol
        ...
```

**Ejemplo:** Para `2 + 3 * 4`:

```
add(val=14.0)
  num(val=2.0, @1:1)
  mul(val=12.0)
    num(val=3.0, @1:5)
    num(val=4.0, @1:9)
```

El AST refleja la **precedencia** correcta: la multiplicación se evalúa primero.

---

## 5. Tabla de Símbolos

Gestiona variables y sus usos.

```python
@dataclass
class Simbolo:
    nombre: str
    tipo: str = "num"
    valor: Optional[float] = None
    ocurrencias: List[Tuple[int,int]] = field(default_factory=list)

class TablaSimbolos:
    def __init__(self): 
        self.tab: Dict[str,Simbolo] = {}
    
    def tocar(self, nombre:str, pos:Tuple[int,int]) -> Simbolo:
        # Registra uso de variable
        if nombre not in self.tab:
            self.tab[nombre] = Simbolo(nombre)
        self.tab[nombre].ocurrencias.append(pos)
        return self.tab[nombre]
    
    def set_valor(self, nombre:str, val:float):
        # Asigna valor a variable
        ...
    
    def obtener(self, nombre:str) -> Optional[float]:
        # Recupera valor de variable
        ...
```

**Salida (symbols.txt):**
```
== Tabla de símbolos ==
x            tipo=num valor=5.0 ocurrencias=[(1,1)]
y            tipo=num valor=10.0 ocurrencias=[(1,5)]
```

---

## 6. Parser LL(1) con EDTS

El parser implementa **traducción dirigida por sintaxis** usando:
- **Atributos sintetizados:** `val`, `nodo` (fluyen hacia arriba)
- **Atributos heredados:** `inh_val`, `inh_nodo` (fluyen hacia abajo)

### Estructura del Parser

```python
class Parser:
    def __init__(self, toks: List[Token]): 
        self.toks = toks
        self.k = 0  # Índice del token actual
        self.ts = TablaSimbolos()
    
    def la(self) -> Token: 
        return self.toks[self.k]  # Lookahead
    
    def eat(self, typ:str) -> Token:
        # Consume token esperado
        t = self.la()
        if t.typ != typ: 
            raise SyntaxError(...)
        self.k += 1
        return t
```

### Métodos de Parsing con Acciones Semánticas

#### E → T E'

```python
def E(self):
    nT, vT = self.T()              # Parse T
    return self.Ep(nT, vT)         # Pasa atributos heredados a E'
```

#### E' → + T E' | - T E' | ε

```python
def Ep(self, inh_node: AST, inh_val: float):
    t = self.la()
    
    if t.typ == TT_PLUS:
        self.eat(TT_PLUS)
        nT, vT = self.T()          # Parse T
        node = AST("add", children=[inh_node, nT])  # Construye nodo
        return self.Ep(node, inh_val + vT)          # Recursión con nuevos heredados
    
    if t.typ == TT_MINUS:
        self.eat(TT_MINUS)
        nT, vT = self.T()
        node = AST("sub", children=[inh_node, nT])
        return self.Ep(node, inh_val - vT)
    
    # Producción ε
    return inh_node, inh_val
```

**Flujo de atributos:**
1. `T.val` → `E'.inh_val` (heredado)
2. `T.nodo` → `E'.inh_nodo` (heredado)
3. Se construye nuevo nodo: `add(E'.inh_nodo, T.nodo)`
4. Se calcula nuevo valor: `E'.inh_val + T.val`
5. Se pasa recursivamente a `E'1`

#### T → F T'

```python
def T(self):
    nF, vF = self.F()
    return self.Tp(nF, vF)
```

#### T' → * F T' | / F T' | ε

```python
def Tp(self, inh_node: AST, inh_val: float):
    t = self.la()
    
    if t.typ == TT_MUL:
        self.eat(TT_MUL)
        nF, vF = self.F()
        node = AST("mul", children=[inh_node, nF])
        return self.Tp(node, inh_val * vF)
    
    if t.typ == TT_DIV:
        self.eat(TT_DIV)
        nF, vF = self.F()
        if vF == 0: 
            raise ZeroDivisionError("División por cero")
        node = AST("div", children=[inh_node, nF])
        return self.Tp(node, inh_val / vF)
    
    return inh_node, inh_val  # ε
```

#### F → ( E ) | num | id

```python
def F(self):
    t = self.la()
    
    if t.typ == TT_LP:
        self.eat(TT_LP)
        nE, vE = self.E()
        self.eat(TT_RP)
        return nE, vE
    
    if t.typ == TT_NUM:
        tok = self.eat(TT_NUM)
        val = float(tok.lex)
        return AST("num", value=val, pos=(tok.line,tok.col)), val
    
    if t.typ == TT_ID:
        tok = self.eat(TT_ID)
        s = self.ts.tocar(tok.lex, (tok.line, tok.col))  # Registra en tabla
        
        if s.valor is None:
            # Solicita valor al usuario
            while True:
                raw = input(f"Valor para {tok.lex}: ").strip()
                try: 
                    v = float(raw)
                    break
                except: 
                    print("Número inválido.")
            self.ts.set_valor(tok.lex, v)
        
        val = float(self.ts.obtener(tok.lex))
        return AST("id", name=tok.lex, value=val, pos=(tok.line,tok.col)), val
```

---

## 7. Gramática de Atributos y EDTS

### Gramática de Atributos (attrib_grammar.txt)

```
== Gramática de atributos ==
Atributos: para X∈{E,E',T,T',F} → X.val (sintetizado), X.nodo (sintetizado).
Para 'id' y 'num': F.val, F.nodo.

E  → T E'        { E'.inh_val=T.val; E'.inh_nodo=T.nodo;  E.val=E'.val; E.nodo=E'.nodo }
E' → + T E'1     { tmp=E'.inh_val+T.val; n=add(E'.inh_nodo,T.nodo);  
                   E'1.inh_val=tmp; E'1.inh_nodo=n;  E'.val=E'1.val; E'.nodo=E'1.nodo }
E' → - T E'1     { tmp=E'.inh_val-T.val; n=sub(E'.inh_nodo,T.nodo);  
                   E'1.inh_val=tmp; E'1.inh_nodo=n;  E'.val=E'1.val; E'.nodo=E'1.nodo }
E' → ε           { E'.val=E'.inh_val; E'.nodo=E'.inh_nodo }
T  → F T'        { T'.inh_val=F.val; T'.inh_nodo=F.nodo;  T.val=T'.val; T.nodo=T'.nodo }
T' → * F T'1     { tmp=T'.inh_val*F.val; n=mul(T'.inh_nodo,F.nodo);  
                   T'1.inh_val=tmp; T'1.inh_nodo=n;  T'.val=T'1.val; T'.nodo=T'1.nodo }
T' → / F T'1     { tmp=T'.inh_val/F.val; n=div(T'.inh_nodo,F.nodo);  
                   T'1.inh_val=tmp; T'1.inh_nodo=n;  T'.val=T'1.val; T'.nodo=T'1.nodo }
T' → ε           { T'.val=T'.inh_val; T'.nodo=T'.inh_nodo }
F  → ( E )       { F.val=E.val; F.nodo=E.nodo }
F  → num         { F.val=float(num.lex); F.nodo=Num(num.lex) }
F  → id          { si tabla[id] es None pedir; F.val=tabla[id]; F.nodo=Id(id,F.val) }
```

### Esquema EDTS (etds.txt)

```
== Esquema EDTS ==
E  → T {E'.inh_val=T.val; E'.inh_nodo=T.nodo} E' {E.val=E'.val; E.nodo=E'.nodo}
E' → + T {tmp=E'.inh_val+T.val; n=add(E'.inh_nodo,T.nodo)} 
         {E'1.inh_val=tmp; E'1.inh_nodo=n} E'1 {E'.val=E'1.val; E'.nodo=E'1.nodo}
E' → - T {tmp=E'.inh_val-T.val; n=sub(E'.inh_nodo,T.nodo)} 
         {E'1.inh_val=tmp; E'1.inh_nodo=n} E'1 {E'.val=E'1.val; E'.nodo=E'1.nodo}
E' → ε  {E'.val=E'.inh_val; E'.nodo=E'.inh_nodo}
T  → F {T'.inh_val=F.val; T'.inh_nodo=F.nodo} T' {T.val=T'.val; T.nodo=T'.nodo}
T' → * F {tmp=T'.inh_val*F.val; n=mul(T'.inh_nodo,F.nodo)} 
         {T'1.inh_val=tmp; T'1.inh_nodo=n} T'1 {T'.val=T'1.val; T'.nodo=T'1.nodo}
T' → / F {tmp=T'.inh_val/F.val; n=div(T'.inh_nodo,F.nodo)} 
         {T'1.inh_val=tmp; T'1.inh_nodo=n} T'1 {T'.val=T'1.val; T'.nodo=T'1.nodo}
T' → ε  {T'.val=T'.inh_val; T'.nodo=T'.inh_nodo}
F  → ( E ) {F.val=E.val; F.nodo=E.nodo}
F  → num   {F.val=float(num.lex); F.nodo=Num(num.lex)}
F  → id    {si tabla[id] None → pedir; F.val=tabla[id]; F.nodo=Id(id,F.val)}
```

---

## Cómo ejecutar

### Modo Interactivo
```bash
python3 app.py
```

**Ejemplo:**
```
Expresión: x + 2 * 3
Valor para x: 5
Valor = 11.0

AST:
add(val=11.0)
  id(name=x, val=5.0, @1:1)
  mul(val=6.0)
    num(val=2.0, @1:5)
    num(val=3.0, @1:9)

== Tabla de símbolos ==
x            tipo=num valor=5.0 ocurrencias=[(1,1)]

Archivos generados en ./out
```

### Desde stdin
```bash
echo "2 + 3 * 4" | python3 app.py
```

### Con expresiones complejas
```bash
python3 app.py
Expresión: (x + 5) * 2 - y / 3
Valor para x: 10
Valor para y: 9
Valor = 27.0
```

---

## Archivos Generados en `./out`

### 1. `grammar.txt` - Gramática y Conjuntos

```
== Gramática (LL(1)) ==
Inicial: E

E → T E'
E' → + T E' | - T E' | ε
T → F T'
T' → * F T' | / F T' | ε
F → ( E ) | num | id

== Conjuntos FIRST ==
FIRST(E) = {(, id, num}
FIRST(E') = {+, -, ε}
FIRST(T) = {(, id, num}
FIRST(T') = {*, /, ε}
FIRST(F) = {(, id, num}

== Conjuntos FOLLOW ==
FOLLOW(E) = {), $}
FOLLOW(E') = {), $}
FOLLOW(T) = {+, -, ), $}
FOLLOW(T') = {+, -, ), $}
FOLLOW(F) = {*, /, +, -, ), $}

== Conjuntos PREDICT ==
PREDICT(E → T E') = {(, id, num}
PREDICT(E' → + T E') = {+}
PREDICT(E' → - T E') = {-}
PREDICT(E' → ε) = {), $}
...
```

### 2. `attrib_grammar.txt` - Gramática de Atributos

(Ver sección 7)

### 3. `etds.txt` - Esquema EDTS

(Ver sección 7)

### 4. `ast.txt` - AST Decorado

```
== AST decorado ==
add(val=11.0)
  id(name=x, val=5.0, @1:1)
  mul(val=6.0)
    num(val=2.0, @1:5)
    num(val=3.0, @1:9)
```

### 5. `symbols.txt` - Tabla de Símbolos

```
== Tabla de símbolos ==
x            tipo=num valor=5.0 ocurrencias=[(1,1)]
```

### 6. `eval.txt` - Resultado de Evaluación

```
== Resultado ==
x + 2 * 3 = 11.0
```

---

## Casos de Prueba

### Expresión Simple
```bash
echo "2 + 3" | python3 app.py
# Resultado: 5.0
```

### Precedencia de Operadores
```bash
echo "2 + 3 * 4" | python3 app.py
# Resultado: 14.0 (no 20.0)
```

### Paréntesis
```bash
echo "(2 + 3) * 4" | python3 app.py
# Resultado: 20.0
```

### Variables
```bash
python3 app.py
Expresión: (a + b) / 2
Valor para a: 10
Valor para b: 20
# Resultado: 15.0
```

### Expresión Compleja
```bash
python3 app.py
Expresión: x * (y + 3) - z / 2
Valor para x: 2
Valor para y: 5
Valor para z: 4
# Resultado: 14.0
```

---

## Respuesta Mostrada en Terminal

**Entrada:** `x + 2 * 3` con `x = 5`

```
Valor = 11.0

AST:
add(val=11.0)
  id(name=x, val=5.0, @1:1)
  mul(val=6.0)
    num(val=2.0, @1:5)
    num(val=3.0, @1:9)

== Tabla de símbolos ==
x            tipo=num valor=5.0 ocurrencias=[(1,1)]

Archivos generados en ./out
```

---

## Conceptos Teóricos Implementados

### 1. Traducción Dirigida por Sintaxis (EDTS)
Las acciones semánticas se ejecutan **durante** el parsing, no después:
- Construcción incremental del AST
- Evaluación en una sola pasada
- Gestión eficiente de memoria

### 2. Atributos Sintetizados vs Heredados
- **Sintetizados** (`val`, `nodo`): Se calculan de hijos → padres
- **Heredados** (`inh_val`, `inh_nodo`): Se pasan de padres → hijos

### 3. Eliminación de Recursión Izquierda
Transformación de:
```
E → E + T | T
```
A:
```
E  → T E'
E' → + T E' | ε
```

Permite parsing descendente recursivo sin backtracking.

### 4. Parser LL(1) Predictivo
- Usa **1 símbolo de lookahead**
- Decisión determinista en cada paso
- Complejidad **O(n)** lineal

### 5. Conjuntos FIRST/FOLLOW/PREDICT
Garantizan que la gramática es:
- **Determinista** (no ambigua)
- **Predictiva** (decisión única)
- **LL(1)** (parsing eficiente)

---

## Manejo de Errores

### Tokens Inesperados
```python
raise SyntaxError(f"Se esperaba '{typ}' y llegó '{t.typ}' ({t.line},{t.col})")
```

### División por Cero
```python
if vF == 0: 
    raise ZeroDivisionError("División por cero")
```

### Variables No Definidas
```python
if s.valor is None:
    raw = input(f"Valor para {tok.lex}: ").strip()
```

### Expresiones Vacías
```python
if not expr:
    print("Expresión vacía.")
    return
```

---

## Referencias

- **Aho, Sethi, Ullman** - "Compilers: Principles, Techniques, and Tools" (Dragon Book)
- **Gramáticas Libres de Contexto** (GLC)
- **Análisis Sintáctico LL(1)**
- **Traducción Dirigida por Sintaxis**
- **Atributos Sintetizados e Heredados**

---

**Autor:** [Tu Nombre]  
**Materia:** Teoría de Compiladores  
**Fecha:** 2025 eligen ε
```

**Propiedad LL(1):** Los conjuntos PREDICT de cada producción son disjuntos.

---

## 4. Árbol de Sintaxis Abstracta (AST)

Representa la estructura jerárquica de la expresión.

```python
@dataclass
class AST:
    tag: str                          # Tipo: 'add', 'mul', 'num', 'id'
    value: Optional[float] = None     # Valor numérico (sintetizado)
    name: Optional[str] = None        # Nombre de variable
    children: List["AST"] = field(default_factory=list)
    pos: Optional[Tuple[int,int]] = None  # (línea, columna)
    
    def pretty(self, indent=0) -> str:
        # Impresión indentada del árbol
        ...
```

**Ejemplo:** Para `2 + 3 * 4`:

```
add(val=14.0)
  num(val=2.0, @1:1)
  mul(val=12.0)
    num(val=3.0, @1:5)
    num(val=4.0, @1:9)
```

El AST refleja la **precedencia** correcta: la multiplicación se evalúa primero.

---

## 5. Tabla de Símbolos

Gestiona variables y sus usos.

```python
@dataclass
class Simbolo:
    nombre: str
    tipo: str = "num"
    valor: Optional[float] = None
    ocurrencias: List[Tuple[int,int]] = field(default_factory=list)

class TablaSimbolos:
    def __init__(self): 
        self.tab: Dict[str,Simbolo] = {}
    
    def tocar(self, nombre:str, pos:Tuple[int,int]) -> Simbolo:
        # Registra uso de variable
        if nombre not in self.tab:
            self.tab[nombre] = Simbolo(nombre)
        self.tab[nombre].ocurrencias.append(pos)
        return self.tab[nombre]
    
    def set_valor(self, nombre:str, val:float):
        # Asigna valor a variable
        ...
    
    def obtener(self, nombre:str) -> Optional[float]:
        # Recupera valor de variable
        ...
```

**Salida (symbols.txt):**
```
== Tabla de símbolos ==
x            tipo=num valor=5.0 ocurrencias=[(1,1)]
y            tipo=num valor=10.0 ocurrencias=[(1,5)]
```

---

## 6. Parser LL(1) con EDTS

El parser implementa **traducción dirigida por sintaxis** usando:
- **Atributos sintetizados:** `val`, `nodo` (fluyen hacia arriba)
- **Atributos heredados:** `inh_val`, `inh_nodo` (fluyen hacia abajo)

### Estructura del Parser

```python
class Parser:
    def __init__(self, toks: List[Token]): 
        self.toks = toks
        self.k = 0  # Índice del token actual
        self.ts = TablaSimbolos()
    
    def la(self) -> Token: 
        return self.toks[self.k]  # Lookahead
    
    def eat(self, typ:str) -> Token:
        # Consume token esperado
        t = self.la()
        if t.typ != typ: 
            raise SyntaxError(...)
        self.k += 1
        return t
```

### Métodos de Parsing con Acciones Semánticas

#### E → T E'

```python
def E(self):
    nT, vT = self.T()              # Parse T
    return self.Ep(nT, vT)         # Pasa atributos heredados a E'
```

#### E' → + T E' | - T E' | ε

```python
def Ep(self, inh_node: AST, inh_val: float):
    t = self.la()
    
    if t.typ == TT_PLUS:
        self.eat(TT_PLUS)
        nT, vT = self.T()          # Parse T
        node = AST("add", children=[inh_node, nT])  # Construye nodo
        return self.Ep(node, inh_val + vT)          # Recursión con nuevos heredados
    
    if t.typ == TT_MINUS:
        self.eat(TT_MINUS)
        nT, vT = self.T()
        node = AST("sub", children=[inh_node, nT])
        return self.Ep(node, inh_val - vT)
    
    # Producción ε
    return inh_node, inh_val
```

**Flujo de atributos:**
1. `T.val` → `E'.inh_val` (heredado)
2. `T.nodo` → `E'.inh_nodo` (heredado)
3. Se construye nuevo nodo: `add(E'.inh_nodo, T.nodo)`
4. Se calcula nuevo valor: `E'.inh_val + T.val`
5. Se pasa recursivamente a `E'1`

#### T → F T'

```python
def T(self):
    nF, vF = self.F()
    return self.Tp(nF, vF)
```

#### T' → * F T' | / F T' | ε

```python
def Tp(self, inh_node: AST, inh_val: float):
    t = self.la()
    
    if t.typ == TT_MUL:
        self.eat(TT_MUL)
        nF, vF = self.F()
        node = AST("mul", children=[inh_node, nF])
        return self.Tp(node, inh_val * vF)
    
    if t.typ == TT_DIV:
        self.eat(TT_DIV)
        nF, vF = self.F()
        if vF == 0: 
            raise ZeroDivisionError("División por cero")
        node = AST("div", children=[inh_node, nF])
        return self.Tp(node, inh_val / vF)
    
    return inh_node, inh_val  # ε
```

#### F → ( E ) | num | id

```python
def F(self):
    t = self.la()
    
    if t.typ == TT_LP:
        self.eat(TT_LP)
        nE, vE = self.E()
        self.eat(TT_RP)
        return nE, vE
    
    if t.typ == TT_NUM:
        tok = self.eat(TT_NUM)
        val = float(tok.lex)
        return AST("num", value=val, pos=(tok.line,tok.col)), val
    
    if t.typ == TT_ID:
        tok = self.eat(TT_ID)
        s = self.ts.tocar(tok.lex, (tok.line, tok.col))  # Registra en tabla
        
        if s.valor is None:
            # Solicita valor al usuario
            while True:
                raw = input(f"Valor para {tok.lex}: ").strip()
                try: 
                    v = float(raw)
                    break
                except: 
                    print("Número inválido.")
            self.ts.set_valor(tok.lex, v)
        
        val = float(self.ts.obtener(tok.lex))
        return AST("id", name=tok.lex, value=val, pos=(tok.line,tok.col)), val
```

---

## 7. Gramática de Atributos y EDTS

### Gramática de Atributos (attrib_grammar.txt)

```
== Gramática de atributos ==
Atributos: para X∈{E,E',T,T',F} → X.val (sintetizado), X.nodo (sintetizado).
Para 'id' y 'num': F.val, F.nodo.

E  → T E'        { E'.inh_val=T.val; E'.inh_nodo=T.nodo;  E.val=E'.val; E.nodo=E'.nodo }
E' → + T E'1     { tmp=E'.inh_val+T.val; n=add(E'.inh_nodo,T.nodo);  
                   E'1.inh_val=tmp; E'1.inh_nodo=n;  E'.val=E'1.val; E'.nodo=E'1.nodo }
E' → - T E'1     { tmp=E'.inh_val-T.val; n=sub(E'.inh_nodo,T.nodo);  
                   E'1.inh_val=tmp; E'1.inh_nodo=n;  E'.val=E'1.val; E'.nodo=E'1.nodo }
E' → ε           { E'.val=E'.inh_val; E'.nodo=E'.inh_nodo }
T  → F T'        { T'.inh_val=F.val; T'.inh_nodo=F.nodo;  T.val=T'.val; T.nodo=T'.nodo }
T' → * F T'1     { tmp=T'.inh_val*F.val; n=mul(T'.inh_nodo,F.nodo);  
                   T'1.inh_val=tmp; T'1.inh_nodo=n;  T'.val=T'1.val; T'.nodo=T'1.nodo }
T' → / F T'1     { tmp=T'.inh_val/F.val; n=div(T'.inh_nodo,F.nodo);  
                   T'1.inh_val=tmp; T'1.inh_nodo=n;  T'.val=T'1.val; T'.nodo=T'1.nodo }
T' → ε           { T'.val=T'.inh_val; T'.nodo=T'.inh_nodo }
F  → ( E )       { F.val=E.val; F.nodo=E.nodo }
F  → num         { F.val=float(num.lex); F.nodo=Num(num.lex) }
F  → id          { si tabla[id] es None pedir; F.val=tabla[id]; F.nodo=Id(id,F.val) }
```

### Esquema EDTS (etds.txt)

```
== Esquema EDTS ==
E  → T {E'.inh_val=T.val; E'.inh_nodo=T.nodo} E' {E.val=E'.val; E.nodo=E'.nodo}
E' → + T {tmp=E'.inh_val+T.val; n=add(E'.inh_nodo,T.nodo)} 
         {E'1.inh_val=tmp; E'1.inh_nodo=n} E'1 {E'.val=E'1.val; E'.nodo=E'1.nodo}
E' → - T {tmp=E'.inh_val-T.val; n=sub(E'.inh_nodo,T.nodo)} 
         {E'1.inh_val=tmp; E'1.inh_nodo=n} E'1 {E'.val=E'1.val; E'.nodo=E'1.nodo}
E' → ε  {E'.val=E'.inh_val; E'.nodo=E'.inh_nodo}
T  → F {T'.inh_val=F.val; T'.inh_nodo=F.nodo} T' {T.val=T'.val; T.nodo=T'.nodo}
T' → * F {tmp=T'.inh_val*F.val; n=mul(T'.inh_nodo,F.nodo)} 
         {T'1.inh_val=tmp; T'1.inh_nodo=n} T'1 {T'.val=T'1.val; T'.nodo=T'1.nodo}
T' → / F {tmp=T'.inh_val/F.val; n=div(T'.inh_nodo,F.nodo)} 
         {T'1.inh_val=tmp; T'1.inh_nodo=n} T'1 {T'.val=T'1.val; T'.nodo=T'1.nodo}
T' → ε  {T'.val=T'.inh_val; T'.nodo=T'.inh_nodo}
F  → ( E ) {F.val=E.val; F.nodo=E.nodo}
F  → num   {F.val=float(num.lex); F.nodo=Num(num.lex)}
F  → id    {si tabla[id] None → pedir; F.val=tabla[id]; F.nodo=Id(id,F.val)}
```

---

## Cómo ejecutar

### Modo Interactivo
```bash
python3 app.py
```

**Ejemplo:**
```
Expresión: x + 2 * 3
Valor para x: 5
Valor = 11.0

AST:
add(val=11.0)
  id(name=x, val=5.0, @1:1)
  mul(val=6.0)
    num(val=2.0, @1:5)
    num(val=3.0, @1:9)

== Tabla de símbolos ==
x            tipo=num valor=5.0 ocurrencias=[(1,1)]

Archivos generados en ./out
```

### Desde stdin
```bash
echo "2 + 3 * 4" | python3 app.py
```

### Con expresiones complejas
```bash
python3 app.py
Expresión: (x + 5) * 2 - y / 3
Valor para x: 10
Valor para y: 9
Valor = 27.0
```

---

## Archivos Generados en `./out`

### 1. `grammar.txt` - Gramática y Conjuntos

```
== Gramática (LL(1)) ==
Inicial: E

E → T E'
E' → + T E' | - T E' | ε
T → F T'
T' → * F T' | / F T' | ε
F → ( E ) | num | id

== Conjuntos FIRST ==
FIRST(E) = {(, id, num}
FIRST(E') = {+, -, ε}
FIRST(T) = {(, id, num}
FIRST(T') = {*, /, ε}
FIRST(F) = {(, id, num}

== Conjuntos FOLLOW ==
FOLLOW(E) = {), $}
FOLLOW(E') = {), $}
FOLLOW(T) = {+, -, ), $}
FOLLOW(T') = {+, -, ), $}
FOLLOW(F) = {*, /, +, -, ), $}

== Conjuntos PREDICT ==
PREDICT(E → T E') = {(, id, num}
PREDICT(E' → + T E') = {+}
PREDICT(E' → - T E') = {-}
PREDICT(E' → ε) = {), $}
...
```

### 2. `attrib_grammar.txt` - Gramática de Atributos

(Ver sección 7)

### 3. `etds.txt` - Esquema EDTS

(Ver sección 7)

### 4. `ast.txt` - AST Decorado

```
== AST decorado ==
add(val=11.0)
  id(name=x, val=5.0, @1:1)
  mul(val=6.0)
    num(val=2.0, @1:5)
    num(val=3.0, @1:9)
```

### 5. `symbols.txt` - Tabla de Símbolos

```
== Tabla de símbolos ==
x            tipo=num valor=5.0 ocurrencias=[(1,1)]
```

### 6. `eval.txt` - Resultado de Evaluación

```
== Resultado ==
x + 2 * 3 = 11.0
```

---

## Casos de Prueba

### Expresión Simple
```bash
echo "2 + 3" | python3 app.py
# Resultado: 5.0
```

### Precedencia de Operadores
```bash
echo "2 + 3 * 4" | python3 app.py
# Resultado: 14.0 (no 20.0)
```

### Paréntesis
```bash
echo "(2 + 3) * 4" | python3 app.py
# Resultado: 20.0
```

### Variables
```bash
python3 app.py
Expresión: (a + b) / 2
Valor para a: 10
Valor para b: 20
# Resultado: 15.0
```

### Expresión Compleja
```bash
python3 app.py
Expresión: x * (y + 3) - z / 2
Valor para x: 2
Valor para y: 5
Valor para z: 4
# Resultado: 14.0
```

---

## Respuesta Mostrada en Terminal

**Entrada:** `x + 2 * 3` con `x = 5`

```
Valor = 11.0

AST:
add(val=11.0)
  id(name=x, val=5.0, @1:1)
  mul(val=6.0)
    num(val=2.0, @1:5)
    num(val=3.0, @1:9)

== Tabla de símbolos ==
x            tipo=num valor=5.0 ocurrencias=[(1,1)]

Archivos generados en ./out
```

---

## Conceptos Teóricos Implementados

### 1. Traducción Dirigida por Sintaxis (EDTS)
Las acciones semánticas se ejecutan **durante** el parsing, no después:
- Construcción incremental del AST
- Evaluación en una sola pasada
- Gestión eficiente de memoria

### 2. Atributos Sintetizados vs Heredados
- **Sintetizados** (`val`, `nodo`): Se calculan de hijos → padres
- **Heredados** (`inh_val`, `inh_nodo`): Se pasan de padres → hijos

### 3. Eliminación de Recursión Izquierda
Transformación de:
```
E → E + T | T
```
A:
```
E  → T E'
E' → + T E' | ε
```

Permite parsing descendente recursivo sin backtracking.

### 4. Parser LL(1) Predictivo
- Usa **1 símbolo de lookahead**
- Decisión determinista en cada paso
- Complejidad **O(n)** lineal

### 5. Conjuntos FIRST/FOLLOW/PREDICT
Garantizan que la gramática es:
- **Determinista** (no ambigua)
- **Predictiva** (decisión única)
- **LL(1)** (parsing eficiente)

---

## Manejo de Errores

### Tokens Inesperados
```python
raise SyntaxError(f"Se esperaba '{typ}' y llegó '{t.typ}' ({t.line},{t.col})")
```

### División por Cero
```python
if vF == 0: 
    raise ZeroDivisionError("División por cero")
```

### Variables No Definidas
```python
if s.valor is None:
    raw = input(f"Valor para {tok.lex}: ").strip()
```

### Expresiones Vacías
```python
if not expr:
    print("Expresión vacía.")
    return
```

---

## Referencias

- **Aho, Sethi, Ullman** - "Compilers: Principles, Techniques, and Tools" (Dragon Book)
- **Gramáticas Libres de Contexto** (GLC)
- **Análisis Sintáctico LL(1)**
- **Traducción Dirigida por Sintaxis**
- **Atributos Sintetizados e Heredados**

---

**Autor:** [Tu Nombre]  
**Materia:** Teoría de Compiladores  
**Fecha:** 2025)]
```

---

## 3. Conjuntos FIRST, FOLLOW y PREDICT

Estos conjuntos garantizan que la gramática es **LL(1)** (sin ambigüedades).

### FIRST(α) - Primeros símbolos posibles

```python
def compute_first(prods: Dict[str, List[List[str]]]) -> Dict[str,set]:
    first: Dict[str,set] = {A:set() for A in prods}
    # Algoritmo iterativo de punto fijo
    changed = True
    while changed:
        changed = False
        for A, alts in prods.items():
            for rhs in alts:
                # Calcula FIRST para cada producción
                ...
    return first
```

**Resultado:**
```
FIRST(E)  = {(, num, id}
FIRST(E') = {+, -, ε}
FIRST(T)  = {(, num, id}
FIRST(T') = {*, /, ε}
FIRST(F)  = {(, num, id}
```

### FOLLOW(A) - Símbolos que pueden seguir a A

```python
def compute_follow(prods, start, first) -> Dict[str,set]:
    follow: Dict[str,set] = {A:set() for A in prods}
    follow[start].add(TT_EOF)  # $ sigue al símbolo inicial
    # Algoritmo iterativo
    ...
    return follow
```

**Resultado:**
```
FOLLOW(E)  = {), $}
FOLLOW(E') = {), $}
FOLLOW(T)  = {+, -, ), $}
FOLLOW(T') = {+, -, ), $}
FOLLOW(F)  = {*, /, +, -, ), $}
```

### PREDICT(A → α) - Símbolos que predicen una producción

```python
def compute_predict(prods, first, follow):
    pred = {}
    for A, alts in prods.items():
        for rhs in alts:
            if rhs == [EPS]:
                pred[(A,tuple(rhs))] = follow[A]
            else:
                # Calcula FIRST(α) y añade FOLLOW(A) si α es nullable
                ...
    return pred
```

**Resultado:**
```
PREDICT(E → T E')     = {(, num, id}
PREDICT(E' → + T E')  = {+}
PREDICT(E' → - T E')  = {-}
PREDICT(E' → ε)       = {), $}
PREDICT(T → F T')     = {(, num, id}
PREDICT(T' → * F T')  = {*}
PREDICT(T' → / F T')  = {/}
PREDICT(T' → ε)       = {+, -, ), $}
PREDICT(F → ( E ))    = {(}
PREDICT(F → num)      = {num}
PREDICT(F → id)       = {id}
```

**Propiedad LL(1):** Para cada no terminal `A`, los conjuntos PREDICT de sus producciones son **disjuntos** (no se superponen).

---

## 4. Árbol de Sintaxis Abstracta (AST)

Representa la estructura jerárquica de la expresión.

```python
@dataclass
class AST:
    tag: str                          # Tipo: 'add', 'mul', 'num', 'id'
    value: Optional[float] = None     # Valor numérico (sintetizado)
    name: Optional[str] = None        # Nombre de variable
    children: List["AST"] = field(default_factory=list)
    pos: Optional[Tuple[int,int]] = None  # (línea, columna)
    
    def pretty(self, indent=0) -> str:
        # Impresión indentada del árbol
        ...
```

**Ejemplo:** Para `2 + 3 * 4`:

```
add(val=14.0)
  num(val=2.0, @1:1)
  mul(val=12.0)
    num(val=3.0, @1:5)
    num(val=4.0, @1:9)
```

El AST refleja la **precedencia** correcta: la multiplicación se evalúa primero.

---

## 5. Tabla de Símbolos

Gestiona variables y sus usos.

```python
@dataclass
class Simbolo:
    nombre: str
    tipo: str = "num"
    valor: Optional[float] = None
    ocurrencias: List[Tuple[int,int]] = field(default_factory=list)

class TablaSimbolos:
    def __init__(self): 
        self.tab: Dict[str,Simbolo] = {}
    
    def tocar(self, nombre:str, pos:Tuple[int,int]) -> Simbolo:
        # Registra uso de variable
        if nombre not in self.tab:
            self.tab[nombre] = Simbolo(nombre)
        self.tab[nombre].ocurrencias.append(pos)
        return self.tab[nombre]
    
    def set_valor(self, nombre:str, val:float):
        # Asigna valor a variable
        ...
    
    def obtener(self, nombre:str) -> Optional[float]:
        # Recupera valor de variable
        ...
```

**Salida (symbols.txt):**
```
== Tabla de símbolos ==
x            tipo=num valor=5.0 ocurrencias=[(1,1)]
y            tipo=num valor=10.0 ocurrencias=[(1,5)]
```

---

## 6. Parser LL(1) con EDTS

El parser implementa **traducción dirigida por sintaxis** usando:
- **Atributos sintetizados:** `val`, `nodo` (fluyen hacia arriba)
- **Atributos heredados:** `inh_val`, `inh_nodo` (fluyen hacia abajo)

### Estructura del Parser

```python
class Parser:
    def __init__(self, toks: List[Token]): 
        self.toks = toks
        self.k = 0  # Índice del token actual
        self.ts = TablaSimbolos()
    
    def la(self) -> Token: 
        return self.toks[self.k]  # Lookahead
    
    def eat(self, typ:str) -> Token:
        # Consume token esperado
        t = self.la()
        if t.typ != typ: 
            raise SyntaxError(...)
        self.k += 1
        return t
```

### Métodos de Parsing con Acciones Semánticas

#### E → T E'

```python
def E(self):
    nT, vT = self.T()              # Parse T
    return self.Ep(nT, vT)         # Pasa atributos heredados a E'
```

#### E' → + T E' | - T E' | ε

```python
def Ep(self, inh_node: AST, inh_val: float):
    t = self.la()
    
    if t.typ == TT_PLUS:
        self.eat(TT_PLUS)
        nT, vT = self.T()          # Parse T
        node = AST("add", children=[inh_node, nT])  # Construye nodo
        return self.Ep(node, inh_val + vT)          # Recursión con nuevos heredados
    
    if t.typ == TT_MINUS:
        self.eat(TT_MINUS)
        nT, vT = self.T()
        node = AST("sub", children=[inh_node, nT])
        return self.Ep(node, inh_val - vT)
    
    # Producción ε
    return inh_node, inh_val
```

**Flujo de atributos:**
1. `T.val` → `E'.inh_val` (heredado)
2. `T.nodo` → `E'.inh_nodo` (heredado)
3. Se construye nuevo nodo: `add(E'.inh_nodo, T.nodo)`
4. Se calcula nuevo valor: `E'.inh_val + T.val`
5. Se pasa recursivamente a `E'1`

#### T → F T'

```python
def T(self):
    nF, vF = self.F()
    return self.Tp(nF, vF)
```

#### T' → * F T' | / F T' | ε

```python
def Tp(self, inh_node: AST, inh_val: float):
    t = self.la()
    
    if t.typ == TT_MUL:
        self.eat(TT_MUL)
        nF, vF = self.F()
        node = AST("mul", children=[inh_node, nF])
        return self.Tp(node, inh_val * vF)
    
    if t.typ == TT_DIV:
        self.eat(TT_DIV)
        nF, vF = self.F()
        if vF == 0: 
            raise ZeroDivisionError("División por cero")
        node = AST("div", children=[inh_node, nF])
        return self.Tp(node, inh_val / vF)
    
    return inh_node, inh_val  # ε
```

#### F → ( E ) | num | id

```python
def F(self):
    t = self.la()
    
    if t.typ == TT_LP:
        self.eat(TT_LP)
        nE, vE = self.E()
        self.eat(TT_RP)
        return nE, vE
    
    if t.typ == TT_NUM:
        tok = self.eat(TT_NUM)
        val = float(tok.lex)
        return AST("num", value=val, pos=(tok.line,tok.col)), val
    
    if t.typ == TT_ID:
        tok = self.eat(TT_ID)
        s = self.ts.tocar(tok.lex, (tok.line, tok.col))  # Registra en tabla
        
        if s.valor is None:
            # Solicita valor al usuario
            while True:
                raw = input(f"Valor para {tok.lex}: ").strip()
                try: 
                    v = float(raw)
                    break
                except: 
                    print("Número inválido.")
            self.ts.set_valor(tok.lex, v)
        
        val = float(self.ts.obtener(tok.lex))
        return AST("id", name=tok.lex, value=val, pos=(tok.line,tok.col)), val
```

---

## 7. Gramática de Atributos y EDTS

### Gramática de Atributos (attrib_grammar.txt)

```
== Gramática de atributos ==
Atributos: para X∈{E,E',T,T',F} → X.val (sintetizado), X.nodo (sintetizado).
Para 'id' y 'num': F.val, F.nodo.

E  → T E'        { E'.inh_val=T.val; E'.inh_nodo=T.nodo;  E.val=E'.val; E.nodo=E'.nodo }
E' → + T E'1     { tmp=E'.inh_val+T.val; n=add(E'.inh_nodo,T.nodo);  
                   E'1.inh_val=tmp; E'1.inh_nodo=n;  E'.val=E'1.val; E'.nodo=E'1.nodo }
E' → - T E'1     { tmp=E'.inh_val-T.val; n=sub(E'.inh_nodo,T.nodo);  
                   E'1.inh_val=tmp; E'1.inh_nodo=n;  E'.val=E'1.val; E'.nodo=E'1.nodo }
E' → ε           { E'.val=E'.inh_val; E'.nodo=E'.inh_nodo }
T  → F T'        { T'.inh_val=F.val; T'.inh_nodo=F.nodo;  T.val=T'.val; T.nodo=T'.nodo }
T' → * F T'1     { tmp=T'.inh_val*F.val; n=mul(T'.inh_nodo,F.nodo);  
                   T'1.inh_val=tmp; T'1.inh_nodo=n;  T'.val=T'1.val; T'.nodo=T'1.nodo }
T' → / F T'1     { tmp=T'.inh_val/F.val; n=div(T'.inh_nodo,F.nodo);  
                   T'1.inh_val=tmp; T'1.inh_nodo=n;  T'.val=T'1.val; T'.nodo=T'1.nodo }
T' → ε           { T'.val=T'.inh_val; T'.nodo=T'.inh_nodo }
F  → ( E )       { F.val=E.val; F.nodo=E.nodo }
F  → num         { F.val=float(num.lex); F.nodo=Num(num.lex) }
F  → id          { si tabla[id] es None pedir; F.val=tabla[id]; F.nodo=Id(id,F.val) }
```

### Esquema EDTS (etds.txt)

```
== Esquema EDTS ==
E  → T {E'.inh_val=T.val; E'.inh_nodo=T.nodo} E' {E.val=E'.val; E.nodo=E'.nodo}
E' → + T {tmp=E'.inh_val+T.val; n=add(E'.inh_nodo,T.nodo)} 
         {E'1.inh_val=tmp; E'1.inh_nodo=n} E'1 {E'.val=E'1.val; E'.nodo=E'1.nodo}
E' → - T {tmp=E'.inh_val-T.val; n=sub(E'.inh_nodo,T.nodo)} 
         {E'1.inh_val=tmp; E'1.inh_nodo=n} E'1 {E'.val=E'1.val; E'.nodo=E'1.nodo}
E' → ε  {E'.val=E'.inh_val; E'.nodo=E'.inh_nodo}
T  → F {T'.inh_val=F.val; T'.inh_nodo=F.nodo} T' {T.val=T'.val; T.nodo=T'.nodo}
T' → * F {tmp=T'.inh_val*F.val; n=mul(T'.inh_nodo,F.nodo)} 
         {T'1.inh_val=tmp; T'1.inh_nodo=n} T'1 {T'.val=T'1.val; T'.nodo=T'1.nodo}
T' → / F {tmp=T'.inh_val/F.val; n=div(T'.inh_nodo,F.nodo)} 
         {T'1.inh_val=tmp; T'1.inh_nodo=n} T'1 {T'.val=T'1.val; T'.nodo=T'1.nodo}
T' → ε  {T'.val=T'.inh_val; T'.nodo=T'.inh_nodo}
F  → ( E ) {F.val=E.val; F.nodo=E.nodo}
F  → num   {F.val=float(num.lex); F.nodo=Num(num.lex)}
F  → id    {si tabla[id] None → pedir; F.val=tabla[id]; F.nodo=Id(id,F.val)}
```

---

## Cómo ejecutar

### Modo Interactivo
```bash
python3 app.py
```

**Ejemplo:**
```
Expresión: x + 2 * 3
Valor para x: 5
Valor = 11.0

AST:
add(val=11.0)
  id(name=x, val=5.0, @1:1)
  mul(val=6.0)
    num(val=2.0, @1:5)
    num(val=3.0, @1:9)

== Tabla de símbolos ==
x            tipo=num valor=5.0 ocurrencias=[(1,1)]

Archivos generados en ./out
```

### Desde stdin
```bash
echo "2 + 3 * 4" | python3 app.py
```

### Con expresiones complejas
```bash
python3 app.py
Expresión: (x + 5) * 2 - y / 3
Valor para x: 10
Valor para y: 9
Valor = 27.0
```

---

## Archivos Generados en `./out`

### 1. `grammar.txt` - Gramática y Conjuntos

```
== Gramática (LL(1)) ==
Inicial: E

E → T E'
E' → + T E' | - T E' | ε
T → F T'
T' → * F T' | / F T' | ε
F → ( E ) | num | id

== Conjuntos FIRST ==
FIRST(E) = {(, id, num}
FIRST(E') = {+, -, ε}
FIRST(T) = {(, id, num}
FIRST(T') = {*, /, ε}
FIRST(F) = {(, id, num}

== Conjuntos FOLLOW ==
FOLLOW(E) = {), $}
FOLLOW(E') = {), $}
FOLLOW(T) = {+, -, ), $}
FOLLOW(T') = {+, -, ), $}
FOLLOW(F) = {*, /, +, -, ), $}

== Conjuntos PREDICT ==
PREDICT(E → T E') = {(, id, num}
PREDICT(E' → + T E') = {+}
PREDICT(E' → - T E') = {-}
PREDICT(E' → ε) = {), $}
...
```

### 2. `attrib_grammar.txt` - Gramática de Atributos

(Ver sección 7)

### 3. `etds.txt` - Esquema EDTS

(Ver sección 7)

### 4. `ast.txt` - AST Decorado

```
== AST decorado ==
add(val=11.0)
  id(name=x, val=5.0, @1:1)
  mul(val=6.0)
    num(val=2.0, @1:5)
    num(val=3.0, @1:9)
```

### 5. `symbols.txt` - Tabla de Símbolos

```
== Tabla de símbolos ==
x            tipo=num valor=5.0 ocurrencias=[(1,1)]
```

### 6. `eval.txt` - Resultado de Evaluación

```
== Resultado ==
x + 2 * 3 = 11.0
```

---

## Casos de Prueba

### Expresión Simple
```bash
echo "2 + 3" | python3 app.py
# Resultado: 5.0
```

### Precedencia de Operadores
```bash
echo "2 + 3 * 4" | python3 app.py
# Resultado: 14.0 (no 20.0)
```

### Paréntesis
```bash
echo "(2 + 3) * 4" | python3 app.py
# Resultado: 20.0
```

### Variables
```bash
python3 app.py
Expresión: (a + b) / 2
Valor para a: 10
Valor para b: 20
# Resultado: 15.0
```

### Expresión Compleja
```bash
python3 app.py
Expresión: x * (y + 3) - z / 2
Valor para x: 2
Valor para y: 5
Valor para z: 4
# Resultado: 14.0
```

---

## Respuesta Mostrada en Terminal

**Entrada:** `x + 2 * 3` con `x = 5`

```
Valor = 11.0

AST:
add(val=11.0)
  id(name=x, val=5.0, @1:1)
  mul(val=6.0)
    num(val=2.0, @1:5)
    num(val=3.0, @1:9)

== Tabla de símbolos ==
x            tipo=num valor=5.0 ocurrencias=[(1,1)]

Archivos generados en ./out
```

---

## Conceptos Teóricos Implementados

### 1. Traducción Dirigida por Sintaxis (EDTS)
Las acciones semánticas se ejecutan **durante** el parsing, no después:
- Construcción incremental del AST
- Evaluación en una sola pasada
- Gestión eficiente de memoria

### 2. Atributos Sintetizados vs Heredados
- **Sintetizados** (`val`, `nodo`): Se calculan de hijos → padres
- **Heredados** (`inh_val`, `inh_nodo`): Se pasan de padres → hijos

### 3. Eliminación de Recursión Izquierda
Transformación de:
```
E → E + T | T
```
A:
```
E  → T E'
E' → + T E' | ε
```

Permite parsing descendente recursivo sin backtracking.

### 4. Parser LL(1) Predictivo
- Usa **1 símbolo de lookahead**
- Decisión determinista en cada paso
- Complejidad **O(n)** lineal

### 5. Conjuntos FIRST/FOLLOW/PREDICT
Garantizan que la gramática es:
- **Determinista** (no ambigua)
- **Predictiva** (decisión única)
- **LL(1)** (parsing eficiente)

---

## Manejo de Errores

### Tokens Inesperados
```python
raise SyntaxError(f"Se esperaba '{typ}' y llegó '{t.typ}' ({t.line},{t.col})")
```

### División por Cero
```python
if vF == 0: 
    raise ZeroDivisionError("División por cero")
```

### Variables No Definidas
```python
if s.valor is None:
    raw = input(f"Valor para {tok.lex}: ").strip()
```

### Expresiones Vacías
```python
if not expr:
    print("Expresión vacía.")
    return
```

---

## Referencias

- **Aho, Sethi, Ullman** - "Compilers: Principles, Techniques, and Tools" (Dragon Book)
- **Gramáticas Libres de Contexto** (GLC)
- **Análisis Sintáctico LL(1)**
- **Traducción Dirigida por Sintaxis**
- **Atributos Sintetizados e Heredados**

---

**Autor:** [Tu Nombre]  
**Materia:** Teoría de Compiladores  
**Fecha:** 2025
