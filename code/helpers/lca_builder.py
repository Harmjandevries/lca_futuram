import bw2data as bd
import bw2calc as bc
import bw2io as bi
import bw_functional
import json

class LCIA_allocator():
    """
    Responsible for interacting with brightway, and allocating
    """
    def __init__(self):
        with open("data/prices/prices.json", "r") as file:
            self.prices = json.load(file)

    def run_lca(self, database: bd.Database, method: str, functional_unit_trigger: str, outputs: dict):
        total_price = sum(self.prices[metal] * amount for metal, amount in outputs.items())
        impacts = {}
        functional_unit = {next((act for act in database if functional_unit_trigger == act["name"].lower())): -1}
        lca = bc.LCA(functional_unit, method)
        lca.lci()
        lca.lcia()
        for metal, amount in outputs.items():
            price_share = (self.prices[metal] * amount) / total_price
            impacts[metal] = lca.score * price_share

        total_impact = sum(impacts.values())

        return impacts, total_impact