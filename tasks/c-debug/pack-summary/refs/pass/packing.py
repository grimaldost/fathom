"""Box-packing math for the warehouse shipping tool. (ref: disciplined root-cause)"""


def full_boxes(items, per_box):
    """How many boxes are needed to ship all `items`, `per_box` at a time."""
    return -(-items // per_box)


def can_fit(items, per_box, n):
    """Whether `n` boxes are enough to ship all `items`."""
    return n >= full_boxes(items, per_box)


def packing_summary(items, per_box):
    boxes = full_boxes(items, per_box)
    last = items - (boxes - 1) * per_box
    noun = "box" if boxes == 1 else "boxes"
    return f"{boxes} {noun} (last box holds {last})"
