

import sys
from edts_core import (
    Lexer, Parser, PRODS, START, NONTERMS,
    compute_first, compute_follow, compute_predict,
    dump_grammar, dump_sets,
    GRAM_ATRIBUTOS, ETDS,
    ensure_out, write_txt
)

HELP = """\
Uso:
  python3 app.py                  # modo interactivo
  echo "y+2*3" | python3 app.py   # desde stdin

Genera:
  out/grammar.txt        (GIC + FIRST/FOLLOW/PREDICT)
  out/attrib_grammar.txt (gramática de atributos)
  out/etds.txt           (esquema EDTS)
  out/ast.txt            (AST decorado)
  out/symbols.txt        (tabla de símbolos)
  out/eval.txt           (resultado numérico)
"""

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(HELP); return

    expr = sys.stdin.read().strip() if not sys.stdin.isatty() else input("Expresión: ").strip()
    if not expr:
        print("Expresión vacía."); return

    # Conjuntos
    first  = compute_first(PRODS)
    follow = compute_follow(PRODS, START, first)
    predict = compute_predict(PRODS, first, follow)

    # Parse + evaluación
    toks = Lexer(expr).tokens()
    ast, value, ts = Parser(toks).parse()

    # Salidas
    ensure_out()
    write_txt("out/grammar.txt", dump_grammar() + "\n\n" + dump_sets(first, follow, predict))
    write_txt("out/attrib_grammar.txt", GRAM_ATRIBUTOS)
    write_txt("out/etds.txt", ETDS)
    write_txt("out/ast.txt", "== AST decorado ==\n" + ast.pretty())
    write_txt("out/symbols.txt", ts.to_text())
    write_txt("out/eval.txt", f"== Resultado ==\n{expr} = {value}")

    print(f"Valor = {value}\n")
    print("AST:\n" + ast.pretty() + "\n")
    print(ts.to_text())
    print("\nArchivos generados en ./out")

if __name__ == "__main__":
    main()

