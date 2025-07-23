import bw2data as bd
import bw2calc as bc
import bw2io as bi
import bw_functional
import json

class LCIA_allocator():
    def __init__(self):
        with open("data/prices/prices.json", "r") as file:
            self.prices = json.load(file)

    def run_lca(self, database, method, functional_unit_trigger, outputs):
        total_price = sum(self.prices[metal.lower()] * amount for metal, amount in outputs.items())
        impacts = []
        total_impact = 0
        functional_unit = {next((act for act in database if functional_unit_trigger == act["name"].lower())): -1}
        lca = bc.LCA(functional_unit, method)
        lca.lci()
        lca.lcia()

        for metal, amount in outputs.items():
            price_share = (self.prices[metal.lower()] * amount) / total_price
            impacts.append({
                "material": metal.lower(),
                "amount": amount,
                "impacts": lca.score * price_share
            })
            total_impact += lca.score * price_share

        sorted_impacts = sorted(impacts, key=lambda x: x["impacts"], reverse=True)


        return sorted_impacts, total_impact