"""Box-packing math for the warehouse shipping tool."""


def full_boxes(items, per_box):
    """How many boxes are needed to ship all `items`, `per_box` at a time."""
    return items // per_box


def can_fit(items, per_box, n):
    """Whether `n` boxes are enough to ship all `items`."""
    return n >= full_boxes(items, per_box)
