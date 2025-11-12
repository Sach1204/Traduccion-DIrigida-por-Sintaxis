# -*- coding: utf-8 -*-
# Núcleo EDTS: léxico, AST, TS, gramática, FIRST/FOLLOW/PREDICT y parser LL(1)

import re, os
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional

# ---------------- Gramática LL(1) ----------------
NONTERMS = ["E", "E'", "T", "T'", "F"]
TERMS    = ["+", "-", "*", "/", "(", ")", "num", "id", "$"]
START    = "E"
EPS      = "ε"
TT_EOF   = "$"

PRODS = {
    "E":  [["T", "E'"]],
    "E'": [["+", "T", "E'"], ["-", "T", "E'"], [EPS]],
    "T":  [["F", "T'"]],
    "T'": [["*", "F", "T'"], ["/", "F", "T'"], [EPS]],
    "F":  [["(", "E", ")"], ["num"], ["id"]],
}

def dump_grammar() -> str:
    out = ["== Gramática (LL(1)) ==", f"Inicial: {START}", ""]
    for A in NONTERMS:
        out.append(f"{A} → " + " | ".join(" ".join(beta) for beta in PRODS[A]))
    return "\n".join(out)

# ---------------- Léxico ----------------
TT_PLUS, TT_MINUS, TT_MUL, TT_DIV = "+", "-", "*", "/"
TT_LP, TT_RP = "(", ")"
TT_ID, TT_NUM = "id", "num"

WS  = re.compile(r"[ \t]+")
NUM = re.compile(r"\d+(\.\d+)?")
ID  = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

@dataclass
class Token:
    typ: str
    lex: str
    line: int
    col: int

class Lexer:
    def __init__(self, text: str):
        self.t, self.i, self.n = text, 0, len(text)
        self.line, self.col = 1, 1

    def _adv(self, k=1):
        for _ in range(k):
            if self.i >= self.n: return
            ch = self.t[self.i]; self.i += 1
            if ch == "\n": self.line += 1; self.col = 1
            else: self.col += 1

    def tokens(self) -> List[Token]:
        toks: List[Token] = []
        while True:
            m = WS.match(self.t, self.i)
            if m: self._adv(m.end() - self.i)
            if self.i >= self.n:
                toks.append(Token(TT_EOF, "", self.line, self.col)); break
            ch = self.t[self.i]
            if ch in "+-*/()":
                tok = {"+":TT_PLUS,"-":TT_MINUS,"*":TT_MUL,"/":TT_DIV,"(":TT_LP,")":TT_RP}[ch]
                toks.append(Token(tok, ch, self.line, self.col)); self._adv(); continue
            m = NUM.match(self.t, self.i)
            if m:
                lex = m.group(0); toks.append(Token(TT_NUM, lex, self.line, self.col))
                self._adv(len(lex)); continue
            m = ID.match(self.t, self.i)
            if m:
                lex = m.group(0); toks.append(Token(TT_ID, lex, self.line, self.col))
                self._adv(len(lex)); continue
            raise SyntaxError(f"Carácter inesperado '{ch}' ({self.line},{self.col})")
        return toks

# ---------------- AST y Tabla de símbolos ----------------
@dataclass
class AST:
    tag: str
    value: Optional[float] = None
    name: Optional[str] = None
    children: List["AST"] = field(default_factory=list)
    pos: Optional[Tuple[int,int]] = None
    def pretty(self, indent=0) -> str:
        pad = "  "*indent; meta=[]
        if self.name is not None:  meta.append(f"name={self.name}")
        if self.value is not None: meta.append(f"val={self.value}")
        if self.pos:               meta.append(f"@{self.pos[0]}:{self.pos[1]}")
        head = f"{pad}{self.tag}" + (f"({', '.join(meta)})" if meta else "")
        return head if not self.children else head + "\n" + "\n".join(c.pretty(indent+1) for c in self.children)

@dataclass
class Simbolo:
    nombre: str
    tipo: str = "num"
    valor: Optional[float] = None
    ocurrencias: List[Tuple[int,int]] = field(default_factory=list)

class TablaSimbolos:
    def __init__(self): self.tab: Dict[str,Simbolo] = {}
    def tocar(self, nombre:str, pos:Tuple[int,int]) -> Simbolo:
        s = self.tab.get(nombre)
        if not s: s = Simbolo(nombre); self.tab[nombre] = s
        self.tab[nombre].ocurrencias.append(pos)
        return self.tab[nombre]
    def set_valor(self, nombre:str, val:float): self.tocar(nombre, (-1,-1)); self.tab[nombre].valor = val
    def obtener(self, nombre:str) -> Optional[float]: return self.tab.get(nombre).valor if nombre in self.tab else None
    def to_text(self) -> str:
        lines = ["== Tabla de símbolos =="]
        for k in sorted(self.tab):
            s = self.tab[k]
            occ = ", ".join(f"({i},{j})" for i,j in s.ocurrencias if i != -1)
            lines.append(f"{s.nombre:<12} tipo={s.tipo} valor={s.valor} ocurrencias=[{occ}]")
        return "\n".join(lines)

# ---------------- FIRST / FOLLOW / PREDICT ----------------
def compute_first(prods: Dict[str, List[List[str]]]) -> Dict[str,set]:
    first: Dict[str,set] = {A:set() for A in prods}
    for A, alts in prods.items():
        for rhs in alts:
            for X in rhs:
                if X not in prods and X != EPS:
                    first.setdefault(X, set()).add(X)
    changed = True
    while changed:
        changed = False
        for A, alts in prods.items():
            for rhs in alts:
                nullable = True
                for X in rhs:
                    if X == EPS:
                        if EPS not in first[A]: first[A].add(EPS); changed = True
                        nullable = False; break
                    s = set(first[X]) if X in prods else {X}
                    if EPS in s:
                        s.remove(EPS)
                        if not s.issubset(first[A]): first[A] |= s; changed = True
                        nullable = True
                    else:
                        if not s.issubset(first[A]): first[A] |= s; changed = True
                        nullable = False; break
                if nullable and EPS not in first[A]:
                    first[A].add(EPS); changed = True
    return first

def compute_follow(prods: Dict[str, List[List[str]]], start: str, first: Dict[str,set]) -> Dict[str,set]:
    follow: Dict[str,set] = {A:set() for A in prods}
    follow[start].add(TT_EOF)
    changed = True
    while changed:
        changed = False
        for A, alts in prods.items():
            for rhs in alts:
                for i, X in enumerate(rhs):
                    if X in prods:
                        beta = rhs[i+1:]
                        if not beta:
                            if not follow[A].issubset(follow[X]): follow[X] |= follow[A]; changed = True
                        else:
                            FIRSTb, nullable = set(), True
                            for Y in beta:
                                if Y == EPS: FIRSTb.add(EPS); break
                                s = set(first[Y]) if Y in prods else {Y}
                                FIRSTb |= (s - {EPS})
                                if EPS in s: nullable = True
                                else: nullable = False; break
                            if not (FIRSTb - {EPS}).issubset(follow[X]): follow[X] |= (FIRSTb - {EPS}); changed = True
                            if nullable and not follow[A].issubset(follow[X]): follow[X] |= follow[A]; changed = True
    return follow

def compute_predict(prods: Dict[str, List[List[str]]], first: Dict[str,set], follow: Dict[str,set]) -> Dict[Tuple[str,Tuple[str,...]], set]:
    pred: Dict[Tuple[str,Tuple[str,...]], set] = {}
    for A, alts in prods.items():
        for rhs in alts:
            t = tuple(rhs)
            if rhs == [EPS]: pred[(A,t)] = set(follow[A]); continue
            Fa, nullable = set(), True
            for X in rhs:
                if X == EPS: Fa.add(EPS); break
                s = set(first[X]) if X in prods else {X}
                Fa |= (s - {EPS})
                if EPS in s: nullable = True
                else: nullable = False; break
            if nullable: Fa |= follow[A]
            pred[(A,t)] = Fa
    return pred

def dump_sets(first:Dict[str,set], follow:Dict[str,set], predict:Dict[Tuple[str,Tuple[str,...]],set]) -> str:
    f = lambda s: "{" + ", ".join(sorted(s)) + "}"
    out = ["== Conjuntos FIRST =="]
    for A in NONTERMS: out.append(f"FIRST({A}) = {f(first[A])}")
    out.append("\n== Conjuntos FOLLOW ==")
    for A in NONTERMS: out.append(f"FOLLOW({A}) = {f(follow[A])}")
    out.append("\n== Conjuntos PREDICT ==")
    for (A,rhs),S in predict.items(): out.append(f"PREDICT({A} → {' '.join(rhs)}) = {f(S)}")
    return "\n".join(out)

# ---------------- Parser LL(1) con acciones (EDTS) ----------------
class Parser:
    def __init__(self, toks: List[Token]): self.toks=toks; self.k=0; self.ts=TablaSimbolos()
    def la(self) -> Token: return self.toks[self.k]
    def eat(self, typ:str) -> Token:
        t=self.la()
        if t.typ!=typ: raise SyntaxError(f"Se esperaba '{typ}' y llegó '{t.typ}' ({t.line},{t.col})")
        self.k+=1; return t

    def parse(self):
        n,v = self.E(); self.eat(TT_EOF); return n,v,self.ts

    def E(self):
        nT,vT = self.T()
        return self.Ep(nT, vT)

    def Ep(self, inh_node:AST, inh_val:float):
        t = self.la()
        if t.typ == TT_PLUS:
            self.eat(TT_PLUS); nT,vT = self.T()
            node = AST("add", children=[inh_node, nT])
            return self.Ep(node, inh_val + vT)
        if t.typ == TT_MINUS:
            self.eat(TT_MINUS); nT,vT = self.T()
            node = AST("sub", children=[inh_node, nT])
            return self.Ep(node, inh_val - vT)
        return inh_node, inh_val  # ε

    def T(self):
        nF,vF = self.F()
        return self.Tp(nF, vF)

    def Tp(self, inh_node:AST, inh_val:float):
        t = self.la()
        if t.typ == TT_MUL:
            self.eat(TT_MUL); nF,vF = self.F()
            node = AST("mul", children=[inh_node, nF])
            return self.Tp(node, inh_val * vF)
        if t.typ == TT_DIV:
            self.eat(TT_DIV); nF,vF = self.F()
            if vF == 0: raise ZeroDivisionError("División por cero")
            node = AST("div", children=[inh_node, nF])
            return self.Tp(node, inh_val / vF)
        return inh_node, inh_val  # ε

    def F(self):
        t = self.la()
        if t.typ == TT_LP:
            self.eat(TT_LP); nE,vE = self.E(); self.eat(TT_RP); return nE,vE
        if t.typ == TT_NUM:
            tok = self.eat(TT_NUM); val = float(tok.lex)
            return AST("num", value=val, pos=(tok.line,tok.col)), val
        if t.typ == TT_ID:
            tok = self.eat(TT_ID)
            s = self.ts.tocar(tok.lex, (tok.line, tok.col))
            if s.valor is None:
                while True:
                    raw = input(f"Valor para {tok.lex}: ").strip()
                    try: v = float(raw); break
                    except: print("Número inválido.")
                self.ts.set_valor(tok.lex, v)
            val = float(self.ts.obtener(tok.lex))
            return AST("id", name=tok.lex, value=val, pos=(tok.line,tok.col)), val
        raise SyntaxError(f"Token inesperado '{t.typ}' ({t.line},{t.col})")

# ---------------- Gramática de atributos y ETDS (texto) ----------------
GRAM_ATRIBUTOS = r"""
== Gramática de atributos ==
Atributos: para X∈{E,E',T,T',F} → X.val (sintetizado), X.nodo (sintetizado).
Para 'id' y 'num': F.val, F.nodo.

E  → T E'        { E'.inh_val=T.val; E'.inh_nodo=T.nodo;  E.val=E'.val; E.nodo=E'.nodo }
E' → + T E'1     { tmp=E'.inh_val+T.val; n=add(E'.inh_nodo,T.nodo);  E'1.inh_val=tmp; E'1.inh_nodo=n;  E'.val=E'1.val; E'.nodo=E'1.nodo }
E' → - T E'1     { tmp=E'.inh_val-T.val; n=sub(E'.inh_nodo,T.nodo);  E'1.inh_val=tmp; E'1.inh_nodo=n;  E'.val=E'1.val; E'.nodo=E'1.nodo }
E' → ε           { E'.val=E'.inh_val; E'.nodo=E'.inh_nodo }
T  → F T'        { T'.inh_val=F.val; T'.inh_nodo=F.nodo;  T.val=T'.val; T.nodo=T'.nodo }
T' → * F T'1     { tmp=T'.inh_val*F.val; n=mul(T'.inh_nodo,F.nodo);  T'1.inh_val=tmp; T'1.inh_nodo=n;  T'.val=T'1.val; T'.nodo=T'1.nodo }
T' → / F T'1     { tmp=T'.inh_val/F.val; n=div(T'.inh_nodo,F.nodo);  T'1.inh_val=tmp; T'1.inh_nodo=n;  T'.val=T'1.val; T'.nodo=T'1.nodo }
T' → ε           { T'.val=T'.inh_val; T'.nodo=T'.inh_nodo }
F  → ( E )       { F.val=E.val; F.nodo=E.nodo }
F  → num         { F.val=float(num.lex); F.nodo=Num(num.lex) }
F  → id          { si tabla[id] es None pedir; F.val=tabla[id]; F.nodo=Id(id,F.val) }
""".strip()

ETDS = r"""
== Esquema EDTS ==
E  → T {E'.inh_val=T.val; E'.inh_nodo=T.nodo} E' {E.val=E'.val; E.nodo=E'.nodo}
E' → + T {tmp=E'.inh_val+T.val; n=add(E'.inh_nodo,T.nodo)} {E'1.inh_val=tmp; E'1.inh_nodo=n} E'1 {E'.val=E'1.val; E'.nodo=E'1.nodo}
E' → - T {tmp=E'.inh_val-T.val; n=sub(E'.inh_nodo,T.nodo)} {E'1.inh_val=tmp; E'1.inh_nodo=n} E'1 {E'.val=E'1.val; E'.nodo=E'1.nodo}
E' → ε  {E'.val=E'.inh_val; E'.nodo=E'.inh_nodo}
T  → F {T'.inh_val=F.val; T'.inh_nodo=F.nodo} T' {T.val=T'.val; T.nodo=T'.nodo}
T' → * F {tmp=T'.inh_val*F.val; n=mul(T'.inh_nodo,F.nodo)} {T'1.inh_val=tmp; T'1.inh_nodo=n} T'1 {T'.val=T'1.val; T'.nodo=T'1.nodo}
T' → / F {tmp=T'.inh_val/F.val; n=div(T'.inh_nodo,F.nodo)} {T'1.inh_val=tmp; T'1.inh_nodo=n} T'1 {T'.val=T'1.val; T'.nodo=T'1.nodo}
T' → ε  {T'.val=T'.inh_val; T'.nodo=T'.inh_nodo}
F  → ( E ) {F.val=E.val; F.nodo=E.nodo}
F  → num   {F.val=float(num.lex); F.nodo=Num(num.lex)}
F  → id    {si tabla[id] None → pedir; F.val=tabla[id]; F.nodo=Id(id,F.val)}
""".strip()

# ---------------- util ----------------
def ensure_out(): os.makedirs("out", exist_ok=True)
def write_txt(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.rstrip() + "\n")

