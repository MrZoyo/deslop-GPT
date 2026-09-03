def public_label(record):
    return record["name"].strip().casefold()


def legacy_product_label(product_space):
    return product_space["selected"]["display_name"].strip().casefold()
