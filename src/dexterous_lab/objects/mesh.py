"""Object-frame meshes for grasp synthesis; simulator and policy independent."""

from dexterous_lab.objects.geometry import scaled_size


def get_object_mesh(configuration):
    """Return a metric triangle mesh in object frame O, with scale already applied.

    Curved analytic primitives use a tessellated surface approximation. USD meshes
    use Arena's extraction API and reject unsupported non-mesh geometry.
    """
    import trimesh

    dimensions = scaled_size(configuration)
    if configuration.kind == "cube":
        return trimesh.creation.box(extents=dimensions)
    if configuration.kind == "sphere":
        return trimesh.creation.icosphere(subdivisions=3, radius=dimensions[0] / 2)
    if configuration.kind == "cylinder":
        return trimesh.creation.cylinder(radius=dimensions[0] / 2, height=dimensions[2], sections=64)
    if configuration.kind == "usd":
        from isaaclab_arena.utils.usd.helpers import extract_trimesh_from_usd_path

        return extract_trimesh_from_usd_path(configuration.usd_path, scale=configuration.scale)
    raise ValueError(f"Mesh extraction is not implemented for {configuration.kind}")
