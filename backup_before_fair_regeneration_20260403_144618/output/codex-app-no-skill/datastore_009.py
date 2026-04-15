body = {
        "size": data["size"],
        "query": data["query"],
        "aggs": {
            "dynamic_metric": {
                "scripted_metric": {
                    "init_script": {"id": data["script_id"], "params": data["params"]},
                    "map_script": {"id": data["script_id"], "params": data["params"]},
                    "combine_script": {"id": data["script_id"], "params": data["params"]},
                    "reduce_script": {"id": data["script_id"], "params": data["params"]},
                }
            }
        },
    }