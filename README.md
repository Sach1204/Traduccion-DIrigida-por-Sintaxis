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

## Manejo de Errores

```python
# Token inesperado
SyntaxError(f"Esperaba '{typ}' llegó '{t.typ}' ({line},{col})")

# División por cero
ZeroDivisionError("División por cero")

# Variable no definida → input interactivo
input(f"Valor para {var}: ")
```
