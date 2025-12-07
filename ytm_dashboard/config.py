"""
Fund Configuration
Defines all target-maturity funds to be tracked
"""

FUND_CONFIG = {
    # Carmignac funds (web extraction)
    "carmignac_2027": {
        "provider": "carmignac",
        "fund_name": "Carmignac Crédit 2027",
        "isin_code": "FR00140081Y1",
        "maturity": 2027,
        "url": "https://www.carmignac.com/fr-fr/nos-fonds-notre-gestion/carmignac-credit-2027-FR00140081Y1-a-eur-acc",
        "source_type": "web"
    },
    "carmignac_2029": {
        "provider": "carmignac",
        "fund_name": "Carmignac Crédit 2029",
        "isin_code": "FR001400KAV4",
        "maturity": 2029,
        "url": "https://www.carmignac.com/en/our-funds/carmignac-credit-2029-FR001400KAV4-a-eur-acc/documents",
        "source_type": "web"
    },
    "carmignac_2031": {
        "provider": "carmignac",
        "fund_name": "Carmignac Crédit 2031",
        "isin_code": "FR001400U4S3",
        "maturity": 2031,
        "url": "https://www.carmignac.com/fr-fr/nos-fonds-notre-gestion/carmignac-credit-2031-FR001400U4S3-a-eur-acc",
        "source_type": "web"
    },

    # Sycomore funds (PDF extraction)
    "sycomore_2030": {
        "provider": "sycomore",
        "fund_name": "Sycoyield 2030",
        "isin_code": "FR001400MCQ6",
        "maturity": 2030,
        "url": "https://fr.sycomore-am.com/fonds/53/sycoyield-2030/169",
        "source_type": "pdf"
    },
    "sycomore_2032": {
        "provider": "sycomore",
        "fund_name": "Sycoyield 2032",
        "isin_code": "FR0014010IG3",
        "maturity": 2032,
        "url": "https://fr.sycomore-am.com/fonds/58/sycoyield-2032/187",
        "source_type": "pdf"
    },

    # Rothschild funds (PDF extraction)
    "rothschild_2028": {
        "provider": "rothschild",
        "fund_name": "R-co Target 2028 IG",
        "isin_code": "FR001400BU49",
        "maturity": 2028,
        "url": "https://am.eu.rothschildandco.com/fr/nos-fonds/r-co-target-2028-ig/",
        "source_type": "pdf"
    },
    "rothschild_2029": {
        "provider": "rothschild",
        "fund_name": "R-co Target 2029 IG",
        "isin_code": "FR001400KAL5",
        "maturity": 2029,
        "url": "https://am.eu.rothschildandco.com/en/our-funds/r-co-target-2029-ig/",
        "source_type": "pdf"
    }
}
