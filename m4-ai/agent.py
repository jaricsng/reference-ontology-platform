"""NL -> SPARQL -> answer agent, grounded in the hospital ontology (Module 4).

LangChain chain over a local Ollama model:
  question -> LLM generates SPARQL (one-shot, schema-grounded)
           -> execute within the user's security scope (security.py)
           -> LLM summarises the result rows in plain language.

The value here is not a chatbot — it is a grounded interface to the operational
model. Answers come from SPARQL over governed data, not the model's memory.
"""
from __future__ import annotations

import os
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

from security import decide, run_scoped

MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")

# Schema + one-shot example. The example is what makes generation reliable —
# zero-shot, the model hallucinates URIs like :ICU and invalid syntax.
SCHEMA = """PREFIX : <http://example.org/hospital#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

Classes & properties:
  :Patient :occupiesBed :Bed .   # a patient currently occupying a bed
  :Bed     :inWard      :Ward .
  Wards and beds have rdfs:label (wards: "ICU","Ward A","Ward B","Ward C"; beds: "ICU-1", "A5", ...).
  A bed is FREE when no patient occupies it:  FILTER NOT EXISTS { ?p :occupiesBed ?bed }"""

GEN_PROMPT = PromptTemplate.from_template(
    """You translate a question into ONE SPARQL query for Apache Jena Fuseki.
{schema}

Rules:
- Output ONLY the query (PREFIX lines + query). No prose, no ``` fences.
- Match wards/beds by their rdfs:label string. NEVER invent a URI like :ICU.
{hint}
Example
Question: List the free beds in Ward A.
SPARQL:
PREFIX : <http://example.org/hospital#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?bedLabel WHERE {{
  ?w rdfs:label "Ward A" .
  ?bed a :Bed ; :inWard ?w ; rdfs:label ?bedLabel .
  FILTER NOT EXISTS {{ ?p :occupiesBed ?bed }}
}} ORDER BY ?bedLabel

Question: {question}
SPARQL:
""")

SUMMARISE_PROMPT = PromptTemplate.from_template(
    """Answer the user's question in one or two plain-language sentences, using ONLY
the query results below. Do not invent numbers.

Question: {question}
Result columns: {cols}
Result rows: {rows}

Answer:""")

_llm = OllamaLLM(model=MODEL, temperature=0)
_gen_chain = GEN_PROMPT | _llm | StrOutputParser()
_sum_chain = SUMMARISE_PROMPT | _llm | StrOutputParser()


def _clean_sparql(text: str) -> str:
    text = re.sub(r"```(?:sparql)?", "", text, flags=re.I).strip().strip("`").strip()
    # keep from the first PREFIX/SELECT onward (drop any stray preamble)
    m = re.search(r"(?is)\b(PREFIX|SELECT|CONSTRUCT|ASK)\b", text)
    return text[m.start():].strip() if m else text


def generate_sparql(question: str, hint: str = "") -> str:
    raw = _gen_chain.invoke({"schema": SCHEMA, "question": question, "hint": hint})
    return _clean_sparql(raw)


def ask(question: str, user: str, verbose: bool = False) -> dict:
    """Run the full grounded + secured chain for one question."""
    decision = decide(user)
    if not decision.get("allow"):
        return {"user": user, "allowed": False,
                "answer": f"Access denied for user '{user}'."}

    scope = decision.get("ward_filter") or "ALL"
    sparql = generate_sparql(question)

    # One retry on execution error — the documented mitigation for bad SPARQL.
    error = None
    for attempt in range(2):
        try:
            cols, rows = run_scoped(sparql, decision)
            break
        except Exception as e:  # noqa: BLE001  (surface any SPARQL/exec error to a retry)
            error = str(e)
            if attempt == 0:
                sparql = generate_sparql(
                    question, hint=f"- Your previous query failed: {error[:160]}. Fix it.\n")
            else:
                return {"user": user, "allowed": True, "scope": scope, "sparql": sparql,
                        "error": error, "answer": "I could not build a valid query for that."}

    answer = _sum_chain.invoke({
        "question": question, "cols": cols,
        "rows": rows[:50] if rows else "(no rows)"}).strip()

    result = {"user": user, "allowed": True, "scope": scope, "sparql": sparql,
              "columns": cols, "row_count": len(rows), "rows": rows, "answer": answer}
    if verbose:
        print(f"[user={user} scope={scope}]\n--- SPARQL ---\n{sparql}\n--- rows={len(rows)} ---")
    return result
