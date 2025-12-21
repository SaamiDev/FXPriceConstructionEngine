from decimal import Decimal

def extract_all_crls(parsed_scp: dict) -> list[dict]:
    crls = []

    root_crl = parsed_scp.get("crl")
    if not root_crl:
        return crls

    xcalc = root_crl.get("XCalc", {})

    # Component 1
    comp1 = xcalc.get("comp1Calc", {}).get("crl")
    if comp1:
        crls.append(_normalize_crl(comp1))

    # Component 2
    comp2 = xcalc.get("comp2Calc", {}).get("crl")
    if comp2:
        crls.append(_normalize_crl(comp2))

    # Final CRL (always last)
    crls.append(_normalize_crl(root_crl))

    return crls


def _normalize_crl(crl: dict) -> dict:
    rungs = crl.get("rungs", [])
    if isinstance(rungs, dict):
        rungs = [rungs]

    return {
        "id": crl.get("id"),
        "ccyPair": crl.get("ccyPair"),
        "origin": crl.get("origin"),
        "valDt": crl.get("valDt"),
        "rType": crl.get("rType"),
        "rungs": rungs
    }

def explain_triangulation(parsed_scp):
    crl = parsed_scp.get("crl", {})
    xcalc = crl.get("XCalc")

    if not xcalc:
        raise ValueError("CRL is not synthetic / no XCalc found")

    comp1 = xcalc["comp1Calc"]
    comp2 = xcalc["comp2Calc"]

    crl1 = comp1["crl"]
    crl2 = comp2["crl"]

    bid1 = Decimal(comp1["traderAdjBid"])
    bid2 = Decimal(comp2["traderAdjBid"])
    ask1 = Decimal(comp1["traderAdjAsk"])
    ask2 = Decimal(comp2["traderAdjAsk"])

    return {
        "finalPair": crl["ccyPair"],
        "method": "TRIANGULATION",
        "bid": {
            "formula": f'{crl1["ccyPair"]} × {crl2["ccyPair"]}',
            "components": [
                {"pair": crl1["ccyPair"], "bid": bid1},
                {"pair": crl2["ccyPair"], "bid": bid2},
            ],
            "result": Decimal(xcalc["finalTriBid"])
        },
        "ask": {
            "formula": f'{crl1["ccyPair"]} × {crl2["ccyPair"]}',
            "components": [
                {"pair": crl1["ccyPair"], "ask": ask1},
                {"pair": crl2["ccyPair"], "ask": ask2},
            ],
            "result": Decimal(xcalc["finalTriAsk"])
        },
        "sources": [
            {
                "pair": crl1["ccyPair"],
                "origin": crl1["origin"],
                "id": crl1["id"]
            },
            {
                "pair": crl2["ccyPair"],
                "origin": crl2["origin"],
                "id": crl2["id"]
            }
        ]
    }