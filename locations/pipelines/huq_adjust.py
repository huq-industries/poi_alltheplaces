import json

import shapely


class HuqAdjustPipeline:
    """Minor tweaks to the "default" AllThePlaces structure to simplify BigQuery import"""

    def process_item(self, item, spider):
        extras = item.get("extras")

        def extras_copy(ks):
            for k in ks:
                if k in extras:
                    item[k] = extras[k]

        # Annoying and expensive to fish these out of the extras array
        extras_copy(["spider", "shop", "amenity"])
        item["extras"] = [{"key": k, "value": v} for k, v in extras.items()]

        geometry = item.get("geometry", None)
        if geometry is not None:
            # Converts from {"type":"POINT"} etc. to "POINT ([lat], [lng])" so BQ can read natively
            item["geometry"] = shapely.to_wkt(shapely.from_geojson(json.dumps(geometry)))

        return item
