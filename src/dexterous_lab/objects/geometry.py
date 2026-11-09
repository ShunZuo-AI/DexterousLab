"""Convert object configuration to physical dimensions in metres."""


def scaled_size(config):
    return tuple(size * scale for size, scale in zip(config.size, config.scale, strict=True))
